##################################################################################################################
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
from datetime import datetime
import boto3
import pytest
from botocore.stub import ANY
from shared.helper import get_built_in_model_monitor_container_uri


@pytest.fixture(autouse=True)
def mock_env_variables():
    new_env = {
        "BASELINE_JOB_NAME": "test-baseline-job",
        "ASSETS_BUCKET": "testbucket",
        "TRAINING_DATA_LOCATION": "training_data.csv",
        "BASELINE_JOB_OUTPUT_LOCATION": "baseline_output",
        "INSTANCE_TYPE": "ml.m5.4xlarge",
        "INSTANCE_VOLUME_SIZE": "20",
        "ROLE_ARN": "arn:aws:iam::account:role/myrole",
        "STACK_NAME": "test-stack",
        "MAX_RUNTIME_SECONDS": "2600",
    }
    os.environ = {**os.environ, **new_env}


@pytest.fixture
def sm_describe_processing_job_params():
    return {"ProcessingJobName": os.environ["BASELINE_JOB_NAME"]}


@pytest.fixture
def sm_create_baseline_expected_params():
    return {
        "ProcessingJobName": os.environ["BASELINE_JOB_NAME"],
        "ProcessingInputs": [
            {
                "InputName": "baseline_dataset_input",
                "S3Input": {
                    "S3Uri": "s3://" + os.environ["ASSETS_BUCKET"] + "/" + os.environ["TRAINING_DATA_LOCATION"],
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
                        "S3Uri": "s3://"
                        + os.environ["ASSETS_BUCKET"]
                        + "/"
                        + os.environ["BASELINE_JOB_OUTPUT_LOCATION"]
                        + "/"
                        + os.environ["BASELINE_JOB_NAME"],
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                },
            ],
        },
        "ProcessingResources": {
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": os.environ["INSTANCE_TYPE"],
                "VolumeSizeInGB": int(os.environ["INSTANCE_VOLUME_SIZE"]),
            }
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": int(os.environ["MAX_RUNTIME_SECONDS"])},
        "AppSpecification": {
            "ImageUri": get_built_in_model_monitor_container_uri(boto3.session.Session().region_name),
        },
        "Environment": {
            "dataset_format": '{"csv": {"header": true, "output_columns_position": "START"}}',
            "dataset_source": "/opt/ml/processing/input/baseline_dataset_input",
            "output_path": "/opt/ml/processing/output",
            "publish_cloudwatch_metrics": "Disabled",
        },
        "RoleArn": os.environ["ROLE_ARN"],
        "Tags": [
            {"Key": "stack_name", "Value": os.environ["STACK_NAME"]},
        ],
    }


@pytest.fixture
def sm_create_job_response_200():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "ProcessingJobArn": "arn:aws:sagemaker:region:account:processing-job/name",
    }


@pytest.fixture
def sm_describe_job_response():
    return {
        "ProcessingInputs": [
            {
                "InputName": "baseline_dataset_input",
                "S3Input": {
                    "S3Uri": "s3://" + os.environ["ASSETS_BUCKET"] + "/" + os.environ["TRAINING_DATA_LOCATION"],
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
                        "S3Uri": "s3://"
                        + os.environ["ASSETS_BUCKET"]
                        + "/"
                        + os.environ["BASELINE_JOB_OUTPUT_LOCATION"]
                        + "/"
                        + os.environ["BASELINE_JOB_NAME"],
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                        "S3UploadMode": "EndOfJob",
                    },
                }
            ]
        },
        "ProcessingJobName": os.environ["BASELINE_JOB_NAME"],
        "ProcessingResources": {
            "ClusterConfig": {"InstanceCount": 1, "InstanceType": "ml.m5.xlarge", "VolumeSizeInGB": 20}
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": 3600},
        "AppSpecification": {"ImageUri": get_built_in_model_monitor_container_uri(boto3.session.Session().region_name)},
        "Environment": {
            "dataset_format": '{"csv": {"header": true, "output_columns_position": "START"}}',
            "dataset_source": "/opt/ml/processing/input/baseline_dataset_input",
            "output_path": "/opt/ml/processing/output",
            "publish_cloudwatch_metrics": "Disabled",
        },
        "RoleArn": os.environ["ROLE_ARN"],
        "ProcessingJobArn": "arn:processing-job/my-baseline-jobe",
        "ProcessingJobStatus": "Completed",
        "ExitMessage": "Completed: Job completed successfully with no violations.",
        "ProcessingEndTime": datetime(2020, 12, 16),
        "ProcessingStartTime": datetime(2020, 12, 16),
        "LastModifiedTime": datetime(2020, 12, 16),
        "CreationTime": datetime(2020, 12, 16),
        "ResponseMetadata": {
            "RequestId": "3a485433-aea7-428c-8dc1-e70e9e4994d6",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "3a485433-aea7-428c-8dc1-e70e9e4994d6",
                "content-type": "application/x-amz-json-1.1",
                "content-length": "1637",
                "date": "Mon, 21 Dec 2020 16:58:35 GMT",
            },
            "RetryAttempts": 0,
        },
    }


@pytest.fixture
def cp_expected_params_success():
    return {"jobId": "test_job_id"}


@pytest.fixture
def cp_expected_params_failure():
    return {"jobId": "test_job_id", "failureDetails": {"message": ANY, "type": "JobFailed"}}


@pytest.fixture()
def event():
    return {
        "CodePipeline.job": {"id": "test_job_id"},
    }
