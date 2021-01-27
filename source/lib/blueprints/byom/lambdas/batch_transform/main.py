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
from time import gmtime, strftime
import boto3
import uuid
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
    job_id = event["CodePipeline.job"]["id"]
    prefix = "batch_transform"
    model_name = os.environ.get("model_name")
    assets_bucket = os.environ.get("assets_bucket")
    batch_data = os.environ.get("batch_inference_data")
    inference_instance = os.environ.get("inference_instance")

    batch_job_name = f"{model_name}-batch-transform-{str(uuid.uuid4())[:8]}"
    output_location = f"s3://{assets_bucket}/{prefix}/output/{batch_job_name}"

    request = {
        "TransformJobName": batch_job_name,
        "ModelName": model_name,
        "TransformOutput": {
            "S3OutputPath": output_location,
            "Accept": "text/csv",
            "AssembleWith": "Line",
        },
        "TransformInput": {
            "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": f"s3://{assets_bucket}/{batch_data}"}},
            "ContentType": "text/csv",
            "SplitType": "Line",
            "CompressionType": "None",
        },
        "TransformResources": {"InstanceType": inference_instance, "InstanceCount": 1},
    }

    response = sm_client.create_transform_job(**request)
    logger.info(f"Response from create transform job request. response: {response}")
    logger.info(f"Created Transform job with name: {batch_job_name}")

    if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
        cp_client.put_job_success_result(jobId=job_id)
        logger.info(f"Sent success message back to codepipeline with job_id: {job_id}")
    else:
        cp_client.put_job_failure_result(
            jobId=job_id, failureDetails={"message": "Job failed. Check the logs for more info.", "type": "JobFailed"}
        )
