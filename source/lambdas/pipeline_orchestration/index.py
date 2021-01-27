# #####################################################################################################################
#  Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                       #
#                                                                                                                     #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance     #
#  with the License. A copy of the License is located at                                                              #
#                                                                                                                     #
#  http://www.apache.org/licenses/LICENSE-2.0                                                                         #
#                                                                                                                     #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES  #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions     #
#  and limitations under the License.                                                                                 #
# #####################################################################################################################
import json
import uuid
from json import JSONEncoder
import os
import datetime
import boto3
from shared.wrappers import BadRequest, api_exception_handler
from shared.logger import get_logger

cloudformation_client = boto3.client("cloudformation")
codepipeline_client = boto3.client("codepipeline")

logger = get_logger(__name__)


# subclass JSONEncoder to be able to convert pipeline status to json
class DateTimeEncoder(JSONEncoder):
    # Override the default method
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()


@api_exception_handler
def handler(event, context):
    if "httpMethod" in event and event["httpMethod"] == "POST":  # Lambda is being invoked from API Gateway
        if event["path"] == "/provisionpipeline":
            return provision_pipeline(json.loads(event["body"]))
        elif event["path"] == "/pipelinestatus":
            return pipeline_status(json.loads(event["body"]))
        else:
            raise BadRequest("Unacceptable event path. Path must be /provisionpipeline or /pipelinestatus")
    elif "pipeline_type" in event:  # Lambda is being invoked from codepipeline/codebuild
        return provision_pipeline(event)
    else:
        raise BadRequest(
            "Bad request format. Expected httpMethod or pipeline_type, recevied none. Check documentation "
            + "for API & config formats."
        )


def provision_pipeline(event, client=cloudformation_client):
    """
    provision_pipeline takes the lambda event object and creates a cloudformation stack

    :event: event object from lambda function. It must containe: pipeline_type, custom_model_container,
    model_framework, model_framework_version, model_name, model_artifact_location, training_data,
    inference_instance, inference_type, batch_inference_data
    :client: boto3 cloudformation client. Not needed, it is only added for unit testing purpose
    :return: an object that has statusCode, body, isBase64Encoded, and headers. The body contains
    the arn of the stack this function has created
    """
    response = {}
    # validate required attributes based on the pipeline's type
    validated_event = validate(event)
    # extract byom attributes
    pipeline_type = validated_event.get("pipeline_type", "")
    custom_container = validated_event.get("custom_model_container", "")
    inference_type = validated_event.get("inference_type", "")
    pipeline_template_url = template_url(inference_type, custom_container, pipeline_type)
    # construct common temaplate paramaters
    provisioned_pipeline_stack_name, template_parameters = get_template_parameters(validated_event)
    # create a pipeline stack using user parameters and specified blueprint
    stack_response = client.create_stack(
        StackName=provisioned_pipeline_stack_name,
        TemplateURL=pipeline_template_url,
        Parameters=template_parameters,
        Capabilities=["CAPABILITY_IAM"],
        OnFailure="DO_NOTHING",
        RoleARN=os.environ["CFN_ROLE_ARN"],
        Tags=[
            {"Key": "stack_name", "Value": provisioned_pipeline_stack_name},
        ],
    )
    logger.info("New pipelin stack created")
    logger.debug(stack_response)
    response = {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": json.dumps(
            {
                "message": "success: stack creation started",
                "pipeline_id": stack_response["StackId"],
            }
        ),
        "headers": {"Content-Type": "plain/text"},
    }
    return response


def pipeline_status(event, cfn_client=cloudformation_client, cp_client=codepipeline_client):
    """
    pipeline_status takes the lambda event object and returns the status of codepipeline project that's
    running the pipeline

    :event: event object from lambda function. It must containe: pipeline_id,
    :return: an object that has statusCode, body, isBase64Encoded, and headers. The body contains
    the status of codepipeline project that's
    running the pipeline
    """
    logger.info(event)
    body = event
    stack_id = body["pipeline_id"]
    stack_resources = cfn_client.list_stack_resources(StackName=stack_id)
    pipeline_id = ""
    # Find the CodePipeline physical id in Cloudformation resources.
    # This is to send back the pipeline id to the user so that they can use to get pipeline status.
    for resource in stack_resources["StackResourceSummaries"]:
        if resource["ResourceType"] == "AWS::CodePipeline::Pipeline":
            pipeline_id = resource["PhysicalResourceId"]

    if pipeline_id == "":
        return {
            "statusCode": 200,
            "isBase64Encoded": False,
            "body": "pipeline cloudformation stack has not provisioned the pipeline yet.",
            "headers": {"Content-Type": "plain/text"},
        }
    else:
        # object from codepipeline
        pipeline_status = cp_client.get_pipeline_state(name=pipeline_id)
        logger.info(pipeline_status)
        return {
            "statusCode": 200,
            "isBase64Encoded": False,
            "body": json.dumps(pipeline_status, indent=4, cls=DateTimeEncoder),
            "headers": {"Content-Type": "plain/text"},
        }


def template_url(inference_type, custom_container, pipeline_type):
    """
    template_url is a helper function that determines the cloudformation stack's file name based on
    inputs

    :inference_type: type of inference from lambda event input. Possible values: 'batch' or 'realtime'
    :custom_container: whether a custom container build is needed in the pipeline or no.
    Possible values: 'True' or 'False'

    :return: returns a link to the appropriate coudformation template files which can be one of these values:
    byom_realtime_build_container.yaml
    byom_realtime_builtin_container.yaml
    byom_batch_build_container.yaml
    byom_batch_builtin_container.yaml
    """
    if pipeline_type == "model_monitor":
        url = "https://" + os.environ["BLUEPRINT_BUCKET_URL"] + "/blueprints/byom/model_monitor.yaml"
        return url
    else:
        url = "https://" + os.environ["BLUEPRINT_BUCKET_URL"] + "/blueprints/" + pipeline_type + "/" + pipeline_type
        if inference_type.lower() == "realtime":
            url = url + "_realtime"
        elif inference_type.lower() == "batch":
            url = url + "_batch"
        else:
            raise BadRequest("Bad request format. Inference type must be 'realtime' or 'batch'")

        if len(custom_container) > 0 and custom_container.endswith(".zip"):
            url = url + "_build_container.yaml"
        elif len(custom_container) == 0:
            url = url + "_builtin_container.yaml"
        else:
            raise BadRequest(
                "Bad request. Custom container should point to a path to .zip file containing custom model assets."
            )
        return url


def get_template_parameters(event):
    pipeline_type = event.get("pipeline_type", "")
    model_framework = event.get("model_framework", "")
    model_framework_version = event.get("model_framework_version", "")
    model_name = event.get("model_name", "").lower().strip()
    model_artifact_location = event.get("model_artifact_location", "")
    inference_instance = event.get("inference_instance", "")
    custom_container = event.get("custom_model_container", "")
    batch_inference_data = event.get("batch_inference_data", "")
    pipeline_stack_name = os.environ["PIPELINE_STACK_NAME"]
    endpoint_name = event.get("endpoint_name", "")
    template_parameters = [
        {
            "ParameterKey": "NOTIFICATIONEMAIL",
            "ParameterValue": os.environ["NOTIFICATION_EMAIL"],
            "UsePreviousValue": True,
        },
        {
            "ParameterKey": "BLUEPRINTBUCKET",
            "ParameterValue": os.environ["BLUEPRINT_BUCKET"],
            "UsePreviousValue": True,
        },
        {
            "ParameterKey": "ASSETSBUCKET",
            "ParameterValue": os.environ["ASSETS_BUCKET"],
            "UsePreviousValue": True,
        },
    ]
    if pipeline_type == "byom":
        provisioned_pipeline_stack_name = f"{pipeline_stack_name}-{model_name}"
        # construct common parameters across byom builtin/custom and realtime/batch
        template_parameters.extend(
            [
                {
                    "ParameterKey": "MODELNAME",
                    "ParameterValue": model_name,
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "MODELARTIFACTLOCATION",
                    "ParameterValue": model_artifact_location,
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "INFERENCEINSTANCE",
                    "ParameterValue": inference_instance,
                    "UsePreviousValue": True,
                },
            ]
        )
        if (
            event.get("inference_type", "").lower().strip() == "realtime"
            and event.get("model_framework", "").strip() != ""
        ):
            # update stack name
            provisioned_pipeline_stack_name = f"{provisioned_pipeline_stack_name}-BYOMPipelineReatimeBuiltIn"
            # add builtin/realtime parameters
            template_parameters.extend(
                [
                    {
                        "ParameterKey": "MODELFRAMEWORK",
                        "ParameterValue": model_framework,
                        "UsePreviousValue": True,
                    },
                    {
                        "ParameterKey": "MODELFRAMEWORKVERSION",
                        "ParameterValue": model_framework_version,
                        "UsePreviousValue": True,
                    },
                ]
            )
        elif (
            event.get("inference_type", "").lower().strip() == "batch"
            and event.get("model_framework", "").strip() != ""
        ):
            # update stack name
            provisioned_pipeline_stack_name = f"{provisioned_pipeline_stack_name}-BYOMPipelineBatchBuiltIn"
            # add builtin/batch parameters
            template_parameters.extend(
                [
                    {
                        "ParameterKey": "MODELFRAMEWORK",
                        "ParameterValue": model_framework,
                        "UsePreviousValue": True,
                    },
                    {
                        "ParameterKey": "MODELFRAMEWORKVERSION",
                        "ParameterValue": model_framework_version,
                        "UsePreviousValue": True,
                    },
                    {
                        "ParameterKey": "BATCHINFERENCEDATA",
                        "ParameterValue": batch_inference_data,
                        "UsePreviousValue": True,
                    },
                ]
            )
        elif (
            event.get("inference_type", "").lower().strip() == "realtime"
            and event.get("model_framework", "").strip() == ""
        ):
            # update stack name
            provisioned_pipeline_stack_name = f"{provisioned_pipeline_stack_name}-BYOMPipelineRealtimeBuild"
            # add custom/realtime parameters
            template_parameters.extend(
                [
                    {
                        "ParameterKey": "CUSTOMCONTAINER",
                        "ParameterValue": custom_container,
                        "UsePreviousValue": True,
                    },
                ]
            )
        elif (
            event.get("inference_type", "").lower().strip() == "batch"
            and event.get("model_framework", "").strip() == ""
        ):
            # update stack name
            provisioned_pipeline_stack_name = f"{provisioned_pipeline_stack_name}-BYOMPipelineBatchBuild"
            # add custom/batch parameters
            template_parameters.extend(
                [
                    {
                        "ParameterKey": "CUSTOMCONTAINER",
                        "ParameterValue": custom_container,
                        "UsePreviousValue": True,
                    },
                    {
                        "ParameterKey": "BATCHINFERENCEDATA",
                        "ParameterValue": batch_inference_data,
                        "UsePreviousValue": True,
                    },
                ]
            )
        else:
            raise BadRequest(
                "Bad request format. Pipeline type not supported. Check documentation for API & config formats."
            )

    elif pipeline_type == "model_monitor":
        provisioned_pipeline_stack_name = f"{pipeline_stack_name}-{endpoint_name}-model-monitor"
        # get the optional monitoring type
        monitoring_type = event.get("monitoring_type", "dataquality").lower().strip()
        # create uniques names for data baseline and monitoring schedule. The names need to be unique because
        # Old jobs are not deleted, and there is a high possibility that the client create a job with the same name
        # which will throw an error.
        baseline_job_name = f"{endpoint_name}-baseline-job-{str(uuid.uuid4())[:8]}"
        monitoring_schedule_name = f"{endpoint_name}-monitor-{monitoring_type}-{str(uuid.uuid4())[:8]}"
        # add model monitor parameters
        template_parameters.extend(
            [
                {
                    "ParameterKey": "BASELINEJOBOUTPUTLOCATION",
                    "ParameterValue": event.get("baseline_job_output_location"),
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "ENDPOINTNAME",
                    "ParameterValue": endpoint_name,
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "BASELINEJOBNAME",
                    "ParameterValue": baseline_job_name,
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "MONITORINGSCHEDULENAME",
                    "ParameterValue": monitoring_schedule_name,
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "MONITORINGOUTPUTLOCATION",
                    "ParameterValue": event.get("monitoring_output_location"),
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "SCHEDULEEXPRESSION",
                    "ParameterValue": event.get("schedule_expression"),
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "TRAININGDATA",
                    "ParameterValue": event.get("training_data"),
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "INSTANCETYPE",
                    "ParameterValue": event.get("instance_type"),
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "INSTANCEVOLUMESIZE",
                    "ParameterValue": event.get("instance_volume_size"),
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "MONITORINGTYPE",
                    "ParameterValue": event.get("monitoring_type", "dataquality"),
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "MAXRUNTIMESIZE",
                    "ParameterValue": event.get("max_runtime_seconds", "-1"),
                    "UsePreviousValue": True,
                },
            ]
        )
    else:
        raise BadRequest(
            "Bad request format. Pipeline type not supported. Check documentation for API & config formats."
        )

    return (provisioned_pipeline_stack_name, template_parameters)


def get_required_keys(event):
    required_keys = []
    if event.get("pipeline_type", "").lower() == "byom":
        # common keys
        common_keys = [
            "pipeline_type",
            "model_name",
            "model_artifact_location",
            "inference_instance",
            "inference_type",
        ]

        if (
            event.get("inference_type", "").lower().strip() == "realtime"
            and event.get("model_framework", "").strip() != ""
        ):
            required_keys = common_keys + [
                "model_framework",
                "model_framework_version",
            ]
        elif (
            event.get("inference_type", "").lower().strip() == "batch"
            and event.get("model_framework", "").strip() != ""
        ):
            required_keys = common_keys + [
                "model_framework",
                "model_framework_version",
                "batch_inference_data",
            ]
        elif (
            event.get("inference_type", "").lower().strip() == "realtime"
            and event.get("model_framework", "").strip() == ""
        ):
            required_keys = common_keys + [
                "custom_model_container",
            ]
        elif (
            event.get("inference_type", "").lower().strip() == "batch"
            and event.get("model_framework", "").strip() == ""
        ):
            required_keys = common_keys + [
                "custom_model_container",
                "batch_inference_data",
            ]
        else:
            raise BadRequest("Bad request. missing keys for byom")
    elif event.get("pipeline_type", "").lower().strip() == "model_monitor":
        required_keys = [
            "pipeline_type",
            "endpoint_name",
            "baseline_job_output_location",
            "monitoring_output_location",
            "schedule_expression",
            "training_data",
            "instance_type",
            "instance_volume_size",
        ]

        if event.get("monitoring_type", "").lower().strip() in ["modelquality", "modelbias", "modelexplainability"]:
            required_keys = required_keys + [
                "features_attribute",
                "inference_attribute",
                "probability_attribute",
                "probability_threshold_attribute",
            ]
        # monitoring_type is optional, but if the client provided a value not in the allowed values, raise an exception
        elif event.get("monitoring_type", "").lower().strip() not in [
            "",
            "dataquality",
            "modelquality",
            "modelbias",
            "modelexplainability",
        ]:
            raise BadRequest(
                "Bad request. MonitoringType supported are 'DataQuality'|'ModelQuality'|'ModelBias'|'ModelExplainability'"
            )
    else:
        raise BadRequest(
            "Bad request format. Pipeline type not supported. Check documentation for API & config formats"
        )

    return required_keys


def validate(event):
    """
    validate is a helper function that checks if all required input parameters are present in the handler's event object

    :event: Lambda function's event object

    :return: returns the event back if it passes the validation othewise it raises a bad request exception
    :raises: BadRequest Exception
    """
    # get the required keys to validate the event
    required_keys = get_required_keys(event)
    for key in required_keys:
        if key not in event:
            logger.error(f"Request event did not have parameter: {key}")
            raise BadRequest(f"Bad request. API body does not have the necessary parameter: {key}")

    return event
