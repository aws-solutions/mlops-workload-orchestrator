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
import json
import boto3
from shared.wrappers import code_pipeline_exception_handler
from shared.logger import get_logger
from shared.helper import get_client

logger = get_logger(__name__)

lm_client = get_client("lambda")
cp_client = get_client("codepipeline")


@code_pipeline_exception_handler
def handler(event, context):
    # todo: change the way to mock boto3 clients for unit tests without passing clients in input

    # Extract the Job ID
    job_id = event["CodePipeline.job"]["id"]

    # Extract the Job Data
    job_data = event["CodePipeline.job"]["data"]
    user_parameters = job_data["actionConfiguration"]["configuration"]["UserParameters"]

    logger.debug("user parameters: %s", user_parameters)
    # Get the user parameter that was sent from the last action (create sagemaker endpoint)
    # Codepipeline formats output variables from previous stages into {"0": {"variableName": "value"}}
    endpoint_name = json.loads(user_parameters)["0"]["endpointName"]
    logger.debug("Sagemaker endpoint name: %s", endpoint_name)
    inference_lambda_arn = os.environ["inference_lambda_arn"]
    logger.debug("Inference Lambda ARN: %s", inference_lambda_arn)

    # Sending request to update environment variables for the inference lambda
    # so that it knows which inference endpoint to refer to when it gets inference
    # request from api gateway
    logger.info("Updating inference lambda configuration")
    response = lm_client.update_function_configuration(
        FunctionName=inference_lambda_arn,
        Environment={"Variables": {"ENDPOINT_NAME": endpoint_name, "LOG_LEVEL": "INFO"}},
    )
    logger.info("finished updating inference lambda")
    logger.debug(response)
    # Send response back to codepipeline success or fail.
    if(response['ResponseMetadata']['HTTPStatusCode'] == 200):
        cp_client.put_job_success_result(jobId=job_id)
    else:
        cp_client.put_job_failure_result(jobId=job_id, failureDetails={'message': "Job failed. Check the logs for more info.", 'type': 'JobFailed'})


