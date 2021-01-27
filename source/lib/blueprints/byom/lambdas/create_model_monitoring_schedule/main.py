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
    baseline_job_output_location = os.environ["BASELINE_JOB_OUTPUT_LOCATION"]
    monitoring_schedule_name = os.environ["MONITORING_SCHEDULE_NAME"]
    assets_bucket = os.environ["ASSETS_BUCKET"]
    endpoint_name = os.environ["SAGEMAKER_ENDPOINT_NAME"]
    monitoring_output_location = os.environ["MONITORING_OUTPUT_LOCATION"]
    schedule_expression = os.environ["SCHEDULE_EXPRESSION"]
    instance_type = os.environ["INSTANCE_TYPE"]
    instance_volume_size = int(os.environ["INSTANCE_VOLUME_SIZE"])
    role_arn = os.environ["ROLE_ARN"]
    monitoring_type = os.environ["MONITORING_TYPE"]
    stack_name = os.environ["STACK_NAME"]
    # optional value, if the client did not provide a value, the orchestraion lambda sets it to -1
    max_runtime_seconds = int(os.environ["MAX_RUNTIME_SECONDS"])
    if max_runtime_seconds == -1:
        max_runtime_seconds = None

    allowed_monitoring_types = {
        "dataquality": "DataQuality",
        "modelquality": "ModelQuality",
        "modelbias": "ModelBias",
        "modelexplainability": "ModelExplainability",
    }

    monitoring_type = allowed_monitoring_types[monitoring_type]
    logger.info(f"Checking if monitoring schedule {monitoring_schedule_name} exists...")
    try:
        existing_monitoring_schedule = sm_client.describe_monitoring_schedule(
            MonitoringScheduleName=monitoring_schedule_name
        )
        # Checking if data baseline processing job with the same name exists
        if existing_monitoring_schedule["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logger.info(f"Monitoring schedule {monitoring_schedule_name} already exists, skipping job creation")
            check_monitoring_schedule_status(job_id, existing_monitoring_schedule)

    except botocore.exceptions.ClientError as error:
        logger.info(str(error))
        logger.info(f"Monitoring schedule {monitoring_schedule_name} doesn't exist. Creating a new one.")
        # Sending request to create Monitoring schedule
        response = sm_client.create_monitoring_schedule(
            MonitoringScheduleName=monitoring_schedule_name,
            MonitoringScheduleConfig={
                "ScheduleConfig": {"ScheduleExpression": schedule_expression},
                "MonitoringJobDefinition": {
                    "BaselineConfig": {
                        "ConstraintsResource": {
                            "S3Uri": f"s3://{assets_bucket}/{baseline_job_output_location}/{baseline_job_name}/constraints.json"
                        },
                        "StatisticsResource": {
                            "S3Uri": f"s3://{assets_bucket}/{baseline_job_output_location}/{baseline_job_name}/statistics.json"
                        },
                    },
                    "MonitoringInputs": [
                        {
                            "EndpointInput": {
                                "EndpointName": endpoint_name,
                                "LocalPath": "/opt/ml/processing/input/monitoring_dataset_input",
                                "S3InputMode": "File",
                                "S3DataDistributionType": "FullyReplicated",
                            }
                        },
                    ],
                    "MonitoringOutputConfig": {
                        "MonitoringOutputs": [
                            {
                                "S3Output": {
                                    "S3Uri": f"s3://{assets_bucket}/{monitoring_output_location}",
                                    "LocalPath": "/opt/ml/processing/output",
                                    "S3UploadMode": "EndOfJob",
                                }
                            },
                        ],
                    },
                    "MonitoringResources": {
                        "ClusterConfig": {
                            "InstanceCount": 1,
                            "InstanceType": instance_type,
                            "VolumeSizeInGB": instance_volume_size,
                        }
                    },
                    "MonitoringAppSpecification": {
                        "ImageUri": get_built_in_model_monitor_container_uri(boto3.session.Session().region_name),
                    },
                    "StoppingCondition": {"MaxRuntimeInSeconds": max_runtime_seconds},
                    "RoleArn": role_arn,
                },
            },
            Tags=[
                {"Key": "stack_name", "Value": stack_name},
            ],
        )
        logger.info(f"Finished monitoring Schedule. respons: {response}")
        logger.info("Monitoring Schedule Arn: " + response["MonitoringScheduleArn"])
        logger.debug(response)
        resp = sm_client.describe_monitoring_schedule(MonitoringScheduleName=monitoring_schedule_name)
        check_monitoring_schedule_status(job_id, resp)


def check_monitoring_schedule_status(job_id, monitoring_schedule_response):
    job_status = monitoring_schedule_response["MonitoringScheduleStatus"]
    logger.info("MonitoringScheduleStatus Status: " + job_status)
    if job_status == "Pending":
        continuation_token = json.dumps({"previous_job_id": job_id})
        logger.info("Putting job continuation")
        cp_client.put_job_success_result(jobId=job_id, continuationToken=continuation_token)
    elif job_status == "Scheduled":
        cp_client.put_job_success_result(jobId=job_id)
    else:
        cp_client.put_job_failure_result(
            jobId=job_id,
            failureDetails={
                "message": f"Failed to create Monitoring Schedule.  status: {job_status}",
                "type": "JobFailed",
            },
        )
