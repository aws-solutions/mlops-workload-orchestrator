# #####################################################################################################################
#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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
from shared.helper import get_client, get_built_in_model_monitor_container_uri

logger = get_logger(__name__)

sm_client = get_client("sagemaker")
cp_client = get_client("codepipeline")


@code_pipeline_exception_handler
def handler(event, context):
    # Extract the Job ID
    job_id = event["CodePipeline.job"]["id"]

    baseline_job_name = os.environ["BASELINE_JOB_NAME"]
    assets_bucket = os.environ["ASSETS_BUCKET"]
    training_data_location = os.environ["TRAINING_DATA_LOCATION"]
    baseline_job_output_location = os.environ["BASELINE_JOB_OUTPUT_LOCATION"]
    instance_type = os.environ["INSTANCE_TYPE"]
    instance_volume_size = int(os.environ["INSTANCE_VOLUME_SIZE"])
    role_arn = os.environ["ROLE_ARN"]
    stack_name = os.environ["STACK_NAME"]
    # optional value, if the client did not provide a value, the orchestraion lambda sets it to -1
    max_runtime_seconds = int(os.environ["MAX_RUNTIME_SECONDS"])
    if max_runtime_seconds == -1:
        max_runtime_seconds = None

    logger.info(f"Checking if model monitor's data baseline processing job {baseline_job_name} exists...")
    try:
        existing_baseline_job = sm_client.describe_processing_job(ProcessingJobName=baseline_job_name)
        # Checking if data baseline processing job with the same name exists
        if existing_baseline_job["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logger.info(f"Baseline processing job {baseline_job_name} already exists, skipping job creation")
            check_baseline_job_status(job_id, existing_baseline_job)

    except botocore.exceptions.ClientError as error:
        logger.info(str(error))
        logger.info(f"Data baseline processing job {baseline_job_name} doesn't exist. Creating a new one.")
        # Sending request to create data baseline processing job
        response = sm_client.create_processing_job(
            ProcessingJobName=baseline_job_name,
            ProcessingInputs=[
                {
                    "InputName": "baseline_dataset_input",
                    "S3Input": {
                        "S3Uri": f"s3://{assets_bucket}/{training_data_location}",
                        "LocalPath": "/opt/ml/processing/input/baseline_dataset_input",
                        "S3DataType": "S3Prefix",
                        "S3InputMode": "File",
                        "S3DataDistributionType": "FullyReplicated",
                        "S3CompressionType": "None",
                    },
                }
            ],
            ProcessingOutputConfig={
                "Outputs": [
                    {
                        "OutputName": "baseline_dataset_output",
                        "S3Output": {
                            "S3Uri": f"s3://{assets_bucket}/{baseline_job_output_location}/{baseline_job_name}",
                            "LocalPath": "/opt/ml/processing/output",
                            "S3UploadMode": "EndOfJob",
                        },
                    },
                ],
            },
            ProcessingResources={
                "ClusterConfig": {
                    "InstanceCount": 1,
                    "InstanceType": instance_type,
                    "VolumeSizeInGB": instance_volume_size,
                }
            },
            StoppingCondition={"MaxRuntimeInSeconds": max_runtime_seconds},
            AppSpecification={
                "ImageUri": get_built_in_model_monitor_container_uri(boto3.session.Session().region_name),
            },
            Environment={
                "dataset_format": '{"csv": {"header": true, "output_columns_position": "START"}}',
                "dataset_source": "/opt/ml/processing/input/baseline_dataset_input",
                "output_path": "/opt/ml/processing/output",
                "publish_cloudwatch_metrics": "Disabled",
            },
            RoleArn=role_arn,
            Tags=[
                {"Key": "stack_name", "Value": stack_name},
            ],
        )

        logger.info(f"Finished creating data baseline processing job. respons: {response}")
        logger.info("Data Baseline Processing JobArn: " + response["ProcessingJobArn"])
        logger.debug(response)
        resp = sm_client.describe_processing_job(ProcessingJobName=baseline_job_name)
        check_baseline_job_status(job_id, resp)


def check_baseline_job_status(job_id, baseline_job_response):
    job_status = baseline_job_response["ProcessingJobStatus"]
    logger.info("ProcessingJob Status: " + job_status)
    if job_status == "InProgress":
        continuation_token = json.dumps({"previous_job_id": job_id})
        logger.info("Putting job continuation")
        cp_client.put_job_success_result(jobId=job_id, continuationToken=continuation_token)
    elif job_status == "Completed":
        cp_client.put_job_success_result(
            jobId=job_id,
        )
    else:
        cp_client.put_job_failure_result(
            jobId=job_id,
            failureDetails={
                "message": f"Failed to create Data Baseline Processing Job.  status: {job_status}",
                "type": "JobFailed",
            },
        )
