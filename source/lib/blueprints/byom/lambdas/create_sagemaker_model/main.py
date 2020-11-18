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
import os
import botocore
import boto3
import sagemaker
from shared.wrappers import code_pipeline_exception_handler
from shared.logger import get_logger
from shared.helper import get_client

logger = get_logger(__name__)

sm_client = get_client("sagemaker")
cp_client = get_client("codepipeline")


@code_pipeline_exception_handler
def handler(event, context):
  # todo: change the way to mock boto3 clients for unit tests without passing clients in input

  # Extract the Job ID
  job_id = event['CodePipeline.job']['id']

  logger.info("Creating sagemaker model...")
  model_name = os.environ['model_name']
  try:
    logger.info(f"Checking if model {model_name} exists")
    model_old = sm_client.describe_model(ModelName=model_name)
    # Checking if endpoint config with the same name exists
    if model_old['ResponseMetadata']['HTTPStatusCode'] == 200:
      logger.info(f"Model {model_name} exists. Deleting the model before creating a new one.")
      delete_response = sm_client.delete_model(ModelName=model_name)
      logger.info(f"Delete model response: {delete_response}")
      logger.info(f"Model {model_name} deleted. Creating the new model.")
      create_sm_model(job_id)
  except botocore.exceptions.ClientError as error:
    logger.info(str(error))
    logger.info(f"Model {model_name} does not exist. Creating the new model.")
    create_sm_model(job_id)


def create_sm_model(job_id):
    # Get Container image uri
    container_image_uri = ""
    container_params = {}
    if os.environ["container_uri"] == "": # using built in model

        container_image_uri = sagemaker.image_uris.retrieve(
            framework=os.environ["model_framework"],
            region=boto3.session.Session().region_name,
            version=os.environ["model_framework_version"],
        )
        container_params = {
            "Image": container_image_uri,
            "ImageConfig": {"RepositoryAccessMode": "Platform"},
            "Mode": "SingleModel",
            "ModelDataUrl": os.environ["model_artifact_location"],
        }
    else: # using custom model
        container_image_uri = os.environ["container_uri"]
        container_params = {
            "Image": container_image_uri,
            "ImageConfig": {"RepositoryAccessMode": "Platform"},
            "Mode": "SingleModel",
            "ModelDataUrl": os.environ["model_artifact_location"],
        }

    logger.debug(f"Got Container image uri: {container_image_uri}")

    # Sending request to create sagemaker model
    response = sm_client.create_model(
        ModelName=os.environ["model_name"],
        PrimaryContainer=container_params,
        ExecutionRoleArn=os.environ["create_model_role_arn"],
        EnableNetworkIsolation=False,
    )
    logger.info("Sent request to create sagemaker model")
    logger.debug(response)

    # Send response back to codepipeline success or fail.
    if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
        cp_client.put_job_success_result(jobId=job_id)
    else:
        cp_client.put_job_failure_result(
            jobId=job_id,
            failureDetails={
                "message": "Job failed. Check the logs for more info.",
                "type": "JobFailed",
            },
        )
