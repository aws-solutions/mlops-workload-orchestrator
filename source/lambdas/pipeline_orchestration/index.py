# #####################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                 #
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
import os
from botocore.client import BaseClient
from sagemaker.session import Session
from typing import Dict, Any, List, Union
from shared.wrappers import BadRequest, api_exception_handler
from shared.logger import get_logger
from shared.helper import get_client, DateTimeEncoder
from lambda_helpers import (
    validate,
    template_url,
    get_stack_name,
    get_codepipeline_params,
    get_image_builder_params,
    format_template_parameters,
    create_template_zip_file,
)
from solution_model_card import SolutionModelCardAPIs

cloudformation_client = get_client("cloudformation")
codepipeline_client = get_client("codepipeline")
s3_client = get_client("s3")

sm_client = get_client("sagemaker")
sagemaker_session = Session(sagemaker_client=sm_client)

logger = get_logger(__name__)

content_type = "plain/text"

model_card_operations = [
    "create_model_card",
    "update_model_card",
    "describe_model_card",
    "delete_model_card",
    "export_model_card",
    "list_model_cards",
]


@api_exception_handler
def handler(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:

    if "httpMethod" in event and event["httpMethod"] == "POST":  # Lambda is being invoked from API Gateway
        event_body = json.loads(event["body"])
        if event["path"] == "/provisionpipeline" and event_body.get("pipeline_type") in model_card_operations:
            return provision_model_card(event_body, sagemaker_session)
        elif event["path"] == "/provisionpipeline":
            return provision_pipeline(event_body)
        elif event["path"] == "/pipelinestatus":
            return pipeline_status(event_body)
        else:
            raise BadRequest("Unacceptable event path. Path must be /provisionpipeline or /pipelinestatus")
    elif "pipeline_type" in event:  # Lambda is being invoked from codepipeline/codebuild
        return provision_pipeline(event)
    else:
        raise BadRequest(
            "Bad request format. Expected httpMethod or pipeline_type, received none. Check documentation "
            + "for API & config formats."
        )


def provision_model_card(event: Dict[str, Any], sagemaker_session: Session) -> Dict[str, Any]:
    pipeline_type = event.get("pipeline_type")
    if pipeline_type == "create_model_card":
        return SolutionModelCardAPIs(event, sagemaker_session).create()
    elif pipeline_type == "update_model_card":
        return SolutionModelCardAPIs(event, sagemaker_session).update()
    elif pipeline_type == "describe_model_card":
        return SolutionModelCardAPIs(event, sagemaker_session).describe()
    elif pipeline_type == "delete_model_card":
        return SolutionModelCardAPIs(event, sagemaker_session).delete()
    elif pipeline_type == "export_model_card":
        return SolutionModelCardAPIs(event, sagemaker_session).export_to_pdf(
            s3_output_path=f"s3://{os.environ['ASSETS_BUCKET']}/model_card_exports"
        )
    elif pipeline_type == "list_model_cards":
        return SolutionModelCardAPIs(event, sagemaker_session).list_model_cards()
    else:
        raise BadRequest(
            "pipeline_type must be on of create_model_card|update_model_card|describe_model_card|delete_model_card|export_model_card"
        )


def provision_pipeline(
    event: Dict[str, Any],
    client: BaseClient = cloudformation_client,
    s3_client: BaseClient = s3_client,
) -> Dict[str, Any]:
    """
    provision_pipeline takes the lambda event object and creates a cloudformation stack

    :event: event object from lambda function. It must contain: pipeline_type, custom_model_container,
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
    pipeline_type = validated_event.get("pipeline_type", "").strip().lower()
    is_multi_account = os.environ["IS_MULTI_ACCOUNT"]
    provisioned_pipeline_template_url = template_url(pipeline_type)

    # construct stack name to provision
    provisioned_pipeline_stack_name = get_stack_name(validated_event)

    # if the pipeline to provision is byom_image_builder
    if pipeline_type == "byom_image_builder":
        image_builder_params = get_image_builder_params(validated_event)
        # format the params (the format is the same for multi-account parameters)
        formatted_image_builder_params = format_template_parameters(image_builder_params, "True")
        # create the codepipeline
        stack_response = create_codepipeline_stack(
            provisioned_pipeline_stack_name, template_url("byom_image_builder"), formatted_image_builder_params, client
        )

    else:
        # create a pipeline stack using user parameters and specified blueprint
        codepipeline_stack_name = f"{provisioned_pipeline_stack_name}-codepipeline"
        pipeline_template_url = (
            template_url("multi_account_codepipeline")
            if is_multi_account == "True"
            # training pipelines are deployed in the account where the main template is deployed
            and pipeline_type not in ["model_training_builtin", "model_tuner_builtin", "model_autopilot_training"]
            else template_url("single_account_codepipeline")
        )

        template_zip_name = f"mlops_provisioned_pipelines/{provisioned_pipeline_stack_name}/template.zip"
        template_file_name = provisioned_pipeline_template_url.split("/")[-1]
        # get the codepipeline parameters
        codepipeline_params = get_codepipeline_params(
            is_multi_account, pipeline_type, provisioned_pipeline_stack_name, template_zip_name, template_file_name
        )
        # format the params (the format is the same for multi-account parameters)
        formatted_codepipeline_params = format_template_parameters(codepipeline_params, "True")
        # create the codepipeline
        stack_response = create_codepipeline_stack(
            codepipeline_stack_name, pipeline_template_url, formatted_codepipeline_params, client
        )

        # upload template.zip (contains pipeline template and parameters files)
        create_template_zip_file(
            validated_event,
            os.environ["BLUEPRINT_BUCKET"],
            os.environ["ASSETS_BUCKET"],
            provisioned_pipeline_template_url,
            template_zip_name,
            is_multi_account,
            s3_client,
        )

    logger.info("New pipeline stack created")
    logger.info(stack_response)
    response = {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": json.dumps(
            {
                "message": stack_response["message"],
                "pipeline_id": stack_response["StackId"],
            }
        ),
        "headers": {"Content-Type": content_type},
    }
    return response


def update_stack(
    codepipeline_stack_name: str,
    pipeline_template_url: str,
    template_parameters: List[Dict[str, str]],
    client: BaseClient,
    stack_id: str,
) -> Dict[str, str]:
    try:
        update_response = client.update_stack(
            StackName=codepipeline_stack_name,
            TemplateURL=pipeline_template_url,
            Parameters=template_parameters,
            Capabilities=["CAPABILITY_IAM"],
            RoleARN=os.environ["CFN_ROLE_ARN"],
            Tags=[
                {"Key": "stack_name", "Value": codepipeline_stack_name},
            ],
        )

        logger.info(update_response)

        return {"StackId": stack_id, "message": f"Pipeline {codepipeline_stack_name} is being updated."}

    except Exception as e:
        logger.info(f"Error during stack update {codepipeline_stack_name}: {str(e)}")
        if "No updates are to be performed" in str(e):
            return {
                "StackId": stack_id,
                "message": f"Pipeline {codepipeline_stack_name} is already provisioned. No updates are to be performed.",
            }
        else:
            raise e


def create_codepipeline_stack(
    codepipeline_stack_name: str,
    pipeline_template_url: str,
    template_parameters: List[Dict[str, str]],
    client: BaseClient = cloudformation_client,
) -> Dict[str, str]:
    try:
        stack_response = client.create_stack(
            StackName=codepipeline_stack_name,
            TemplateURL=pipeline_template_url,
            Parameters=template_parameters,
            Capabilities=["CAPABILITY_IAM"],
            OnFailure="DO_NOTHING",
            RoleARN=os.environ["CFN_ROLE_ARN"],
            Tags=[
                {"Key": "stack_name", "Value": codepipeline_stack_name},
            ],
        )

        logger.info(stack_response)
        return {"StackId": stack_response["StackId"], "message": "success: stack creation started"}

    except Exception as e:
        logger.error(f"Error in create_codepipeline_stack: {str(e)}")
        if "already exists" in str(e):
            logger.info(f"AWS Codepipeline {codepipeline_stack_name} already exists. Skipping codepipeline create")
            # get the stack id using stack-name
            stack_id = client.describe_stacks(StackName=codepipeline_stack_name)["Stacks"][0]["StackId"]
            # if the pipeline to update is BYOMPipelineImageBuilder
            if codepipeline_stack_name.endswith("byompipelineimagebuilder"):
                return update_stack(
                    codepipeline_stack_name, pipeline_template_url, template_parameters, client, stack_id
                )

            return {
                "StackId": stack_id,
                "message": f"Pipeline {codepipeline_stack_name} is already provisioned. Updating template parameters.",
            }
        else:
            raise e


def pipeline_status(
    event: Dict[str, Any], cfn_client: BaseClient = cloudformation_client, cp_client: BaseClient = codepipeline_client
) -> Dict[str, Any]:
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
            "headers": {"Content-Type": content_type},
        }
    else:
        # object from codepipeline
        pipeline_status = cp_client.get_pipeline_state(name=pipeline_id)
        logger.info(pipeline_status)
        return {
            "statusCode": 200,
            "isBase64Encoded": False,
            "body": json.dumps(pipeline_status, indent=4, cls=DateTimeEncoder),
            "headers": {"Content-Type": content_type},
        }
