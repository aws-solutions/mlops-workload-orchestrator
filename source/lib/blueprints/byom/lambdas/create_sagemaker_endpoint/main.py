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
import time
import botocore
import boto3
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

    endpointconfig_name = os.environ['model_name'] + "-endpoint-config"
    logger.info(f"Checking if sagemaker endpoint config {endpointconfig_name} exists...")
    try:
        endpointconfig_old = sm_client.describe_endpoint_config(EndpointConfigName=endpointconfig_name)
        # Checking if endpoint config with the same name exists
        if endpointconfig_old['ResponseMetadata']['HTTPStatusCode'] == 200:
            logger.info(f"Endpoint config {endpointconfig_name} already exists, skipping endpoint creation")
    except botocore.exceptions.ClientError as error:
        logger.info(str(error))
        logger.info(f"Endpoint config {endpointconfig_name} doesn't exist. Creating a new one.")
        # Sending request to create sagemeker endpoint config
        response = sm_client.create_endpoint_config(
            EndpointConfigName=os.environ['model_name'] + "-endpoint-config",
            ProductionVariants=[
                {
                'VariantName': os.environ['model_name']+'-variant',
                'ModelName': os.environ['model_name'],
                'InitialInstanceCount': 1,
                'InstanceType': os.environ['inference_instance'],
                },
            ],
            DataCaptureConfig={
            "EnableCapture": True,
            "InitialSamplingPercentage": 100,
            "DestinationS3Uri": f's3://{os.environ["assets_bucket"]}/datacapture',
            "CaptureOptions": [
                { "CaptureMode": "Output" },
                { "CaptureMode": "Input" }
            ],
            "CaptureContentTypeHeader": {
                "CsvContentTypes": ["text/csv"],
                "JsonContentTypes": ["application/json"]
            }
            }
        )
        logger.info(f"Finished creating sagemaker endpoint config. respons: {response}")

    # Sending request to create sagemeker endpoint
    endpoint_name = os.environ['model_name'] + "-endpoint"
    try:
        logger.info(f"Checking if endpoint {endpoint_name} exists...")
        endpoint_old = sm_client.describe_endpoint(EndpointName=endpoint_name)
        # Checking if endpoint with the same name exists
        if endpoint_old["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logger.info(f"Endpoint {endpoint_name} already exists, skipping endpoint creation")
            check_endpoint_status(job_id, endpoint_old, endpoint_name)

    except botocore.exceptions.ClientError as error:
        logger.info(str(error))
        logger.info(f"Endpoint {endpoint_name} doesn't exist. Creating a new one")
        response = sm_client.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpointconfig_name,
        )
        resp = sm_client.describe_endpoint(EndpointName=endpoint_name)
        logger.info("Finished sending request to create sagemaker endpoint")
        logger.info("Endpoint Arn: " + resp['EndpointArn'])
        logger.debug(response)

        check_endpoint_status(job_id, resp, endpoint_name)



def check_endpoint_status(job_id, endpoint_response, endpoint_name):
    endpoint_status = endpoint_response['EndpointStatus']
    logger.info("Endpoint Status: " + endpoint_status)
    if endpoint_status == 'Creating':
        continuation_token = json.dumps({'previous_job_id': job_id})
        logger.info('Putting job continuation')
        cp_client.put_job_success_result(jobId=job_id, continuationToken=continuation_token)
    elif endpoint_status == 'InService':
        cp_client.put_job_success_result(
            jobId=job_id,
            outputVariables={
                "endpointName": endpoint_name,
            },
        )
    else:
        cp_client.put_job_failure_result(jobId=job_id, failureDetails={'message': f"Failed to create endpoint. Endpoint status: {endpoint_status}", 'type': 'JobFailed'})
