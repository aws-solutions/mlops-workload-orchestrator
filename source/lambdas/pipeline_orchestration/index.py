# #####################################################################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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
    if 'httpMethod' in event and event['httpMethod'] == 'POST': # Lambda is being invoked from API Gateway
        if event['path'] == '/provisionpipeline':
            return provision_pipeline(json.loads(event['body']))
        elif event['path'] == '/pipelinestatus':
            return pipeline_status(json.loads(event['body']))
        else:
            raise BadRequest("Unacceptable event path. Path must be /provisionpipeline or /pipelinestatus")
    elif (
        "pipeline_type" in event
    ):  # Lambda is being invoked from codepipeline/codebuild
        return provision_pipeline(event)
    else:
        raise BadRequest("Bad request format. Expected httpMethod or pipeline_type, recevied none. Check documentation for API & config formats.")


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
    new_event = validate(event)
    pipeline_type = new_event["pipeline_type"]
    custom_container = new_event["custom_model_container"]
    model_framework = new_event["model_framework"]
    model_framework_version = new_event["model_framework_version"]
    model_name = new_event["model_name"]
    model_artifact_location = new_event["model_artifact_location"]
    training_data = new_event["training_data"]
    inference_instance = new_event["inference_instance"]
    inference_type = new_event["inference_type"]
    batch_inference_data = new_event["batch_inference_data"]


    pipeline_template_url = template_url(
        inference_type, custom_container, pipeline_type
    )

    template_parameters = []
    if pipeline_type == "byom":
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
                "ParameterKey": "ACCESSBUCKET",
                "ParameterValue": os.environ["ACCESS_BUCKET"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "CUSTOMCONTAINER",
                "ParameterValue": custom_container,
                "UsePreviousValue": True,
            },
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
                "ParameterKey": "TRAININGDATA",
                "ParameterValue": training_data,
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "INFERENCEINSTANCE",
                "ParameterValue": inference_instance,
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "INFERENCETYPE",
                "ParameterValue": inference_type,
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "BATCHINFERENCEDATA",
                "ParameterValue": batch_inference_data,
                "UsePreviousValue": True,
            },
        ]
    # add elif (else if) here to add more pipeline types to the solution
    else:
        raise BadRequest("Bad request format. Pipeline type not supported. Check documentation for API & config formats.")

    # create a pipeline stack using user parameters and specified blueprint
    stack_response = client.create_stack(
        StackName="{}-{}".format(os.environ["PIPELINE_STACK_NAME"], model_name),
        TemplateURL=pipeline_template_url,
        Parameters=template_parameters,
        Capabilities=["CAPABILITY_IAM"],
        OnFailure="DO_NOTHING",
        RoleARN=os.environ["CFN_ROLE_ARN"],
        Tags=[
            {"Key": "purpose", "Value": "test"},
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
    stack_id = body['pipeline_id']
    stack_resources = cfn_client.list_stack_resources(StackName=stack_id)
    pipeline_id = ''
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
        pipeline_status = cp_client.get_pipeline_state(
            name=pipeline_id
        )
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
    :custom_container: whether a custom container build is needed in the pipeline or no. Possible values: 'True' or 'False'

    :return: returns a link to the appropriate coudformation template files which can be one of these values:
    byom_realtime_build_container.yaml
    byom_realtime_builtin_container.yaml
    byom_batch_build_container.yaml
    byom_batch_builtin_container.yaml
    """
    url = (
        "https://"
        + os.environ["BLUEPRINT_BUCKET_URL"]
        + "/blueprints/"
        + pipeline_type
        + "/"
        + pipeline_type
    )
    if inference_type.lower() == "realtime":
        url = url + "_realtime"
    elif inference_type.lower() == "batch":
        url = url + "_batch"
    else:
        raise BadRequest("Bad request format. Inference type must be 'realtime' or 'batch'")

    if len(custom_container) > 0 and custom_container.endswith('.zip'):
        url = url + "_build_container.yaml"
    elif len(custom_container) == 0:
        url = url + "_builtin_container.yaml"
    else:
        raise BadRequest('Bad request. Custom container should point to apath to .zip file containing custom model assets.')
    return url


def validate(event):
    """
    validate is a helper function that checks if all required input parameters are present in the handler's event object

    :event: Lambda function's event object

    :return: returns the event back if it passes the validation othewise it raises a bad request exception
    :raises: BadRequest Exception
    """
    required_keys = [
        'pipeline_type',
        'custom_model_container',
        'model_framework',
        'model_framework_version',
        'model_name',
        'model_artifact_location',
        'training_data',
        'inference_instance',
        'inference_type',
        'batch_inference_data'
    ]
    for key in required_keys:
        if key not in event:
            logger.error(f"Request event did not have parameter: {key}")
            raise BadRequest(f'Bad request. API body does not have the necessary parameter: {key}')

    return event