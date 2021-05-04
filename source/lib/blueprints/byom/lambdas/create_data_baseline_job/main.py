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
import os
import botocore
import boto3
from shared.logger import get_logger
from shared.helper import get_client, get_built_in_model_monitor_container_uri

logger = get_logger(__name__)
sm_client = get_client("sagemaker")


def handler(event, context):
    baseline_job_name = os.environ["BASELINE_JOB_NAME"]
    assets_bucket = os.environ["ASSETS_BUCKET"]
    training_data_location = os.environ["TRAINING_DATA_LOCATION"]
    baseline_job_output_location = os.environ["BASELINE_JOB_OUTPUT_LOCATION"]
    instance_type = os.environ["INSTANCE_TYPE"]
    instance_volume_size = int(os.environ["INSTANCE_VOLUME_SIZE"])
    role_arn = os.environ["ROLE_ARN"]
    kms_key_arn = os.environ.get("KMS_KEY_ARN")
    stack_name = os.environ["STACK_NAME"]
    max_runtime_seconds = int(os.environ["MAX_RUNTIME_SECONDS"])

    try:
        logger.info(f"Creating data baseline processing job {baseline_job_name} ...")
        request = {
            "ProcessingJobName": baseline_job_name,
            "ProcessingInputs": [
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
            "ProcessingOutputConfig": {
                "Outputs": [
                    {
                        "OutputName": "baseline_dataset_output",
                        "S3Output": {
                            "S3Uri": f"s3://{baseline_job_output_location}/{baseline_job_name}",
                            "LocalPath": "/opt/ml/processing/output",
                            "S3UploadMode": "EndOfJob",
                        },
                    },
                ],
            },
            "ProcessingResources": {
                "ClusterConfig": {
                    "InstanceCount": 1,
                    "InstanceType": instance_type,
                    "VolumeSizeInGB": instance_volume_size,
                }
            },
            "AppSpecification": {
                "ImageUri": get_built_in_model_monitor_container_uri(boto3.session.Session().region_name),
            },
            "Environment": {
                "dataset_format": '{"csv": {"header": true, "output_columns_position": "START"}}',
                "dataset_source": "/opt/ml/processing/input/baseline_dataset_input",
                "output_path": "/opt/ml/processing/output",
                "publish_cloudwatch_metrics": "Disabled",
            },
            "RoleArn": role_arn,
            "Tags": [
                {"Key": "stack_name", "Value": stack_name},
            ],
        }

        # optional value, if the client did not provide a value, the orchestraion lambda sets it to -1
        if max_runtime_seconds != -1:
            request.update({"StoppingCondition": {"MaxRuntimeInSeconds": max_runtime_seconds}})
        # add kms key if provided
        if kms_key_arn:
            request["ProcessingOutputConfig"].update({"KmsKeyId": kms_key_arn})
            request["ProcessingResources"]["ClusterConfig"].update({"VolumeKmsKeyId": kms_key_arn})

        # Sending request to create data baseline processing job
        response = sm_client.create_processing_job(**request)

        logger.info(f"Finished creating data baseline processing job. respons: {response}")
        logger.info("Data Baseline Processing JobArn: " + response["ProcessingJobArn"])

    except botocore.exceptions.ClientError as error:
        logger.info(str(error))
        logger.info(f"Creation of baseline processing job: {baseline_job_name} faild.")
