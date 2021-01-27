#######################################################################################################################
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
        "MONITORING_SCHEDULE_NAME": "test-monitoring-schedule",
        "ASSETS_BUCKET": "testbucket",
        "SAGEMAKER_ENDPOINT_NAME": "test-model-endpoint",
        "MONITORING_OUTPUT_LOCATION": "monitor_output",
        "BASELINE_JOB_OUTPUT_LOCATION": "baseline_output",
        "SCHEDULE_EXPRESSION": "cron(0 * ? * * *)",
        "INSTANCE_TYPE": "ml.m5.4xlarge",
        "INSTANCE_VOLUME_SIZE": "20",
        "ROLE_ARN": "arn:aws:iam::account:role/myrole",
        "MONITORING_TYPE": "dataquality",
        "STACK_NAME": "test-stack",
        "MAX_RUNTIME_SECONDS": "2600",
    }
    os.environ = {**os.environ, **new_env}


@pytest.fixture
def sm_describe_monitoring_scheduale_params():
    return {"MonitoringScheduleName": os.environ["MONITORING_SCHEDULE_NAME"]}


@pytest.fixture
def sm_create_monitoring_expected_params():
    baseline_job_name = os.environ["BASELINE_JOB_NAME"]
    baseline_job_output_location = os.environ["BASELINE_JOB_OUTPUT_LOCATION"]
    assets_bucket = os.environ["ASSETS_BUCKET"]
    monitoring_output_location = os.environ["MONITORING_OUTPUT_LOCATION"]
    return {
        "MonitoringScheduleName": os.environ["MONITORING_SCHEDULE_NAME"],
        "MonitoringScheduleConfig": {
            "ScheduleConfig": {"ScheduleExpression": os.environ["SCHEDULE_EXPRESSION"]},
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
                            "EndpointName": os.environ["SAGEMAKER_ENDPOINT_NAME"],
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
                        "InstanceType": os.environ["INSTANCE_TYPE"],
                        "VolumeSizeInGB": int(os.environ["INSTANCE_VOLUME_SIZE"]),
                    }
                },
                "MonitoringAppSpecification": {
                    "ImageUri": get_built_in_model_monitor_container_uri(boto3.session.Session().region_name),
                },
                "StoppingCondition": {"MaxRuntimeInSeconds": int(os.environ["MAX_RUNTIME_SECONDS"])},
                "RoleArn": os.environ["ROLE_ARN"],
            },
        },
        "Tags": [
            {"Key": "stack_name", "Value": os.environ["STACK_NAME"]},
        ],
    }


@pytest.fixture
def sm_create_monitoring_response_200():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "MonitoringScheduleArn": "arn:aws:sagemaker:region:account:monitoring-schedule/name",
    }


@pytest.fixture
def sm_describe_monitoring_schedule_response():
    baseline_job_name = os.environ["BASELINE_JOB_NAME"]
    baseline_job_output_location = os.environ["BASELINE_JOB_OUTPUT_LOCATION"]
    assets_bucket = os.environ["ASSETS_BUCKET"]
    monitoring_output_location = os.environ["MONITORING_OUTPUT_LOCATION"]
    return {
        "MonitoringScheduleArn": "arn:aws:sagemaker:us-east-1:account:monitoring-schedule/monitoring-schedule",
        "MonitoringScheduleName": os.environ["MONITORING_SCHEDULE_NAME"],
        "MonitoringScheduleStatus": "Scheduled",
        "CreationTime": datetime(2021, 1, 15),
        "LastModifiedTime": datetime(2021, 1, 15),
        "MonitoringScheduleConfig": {
            "ScheduleConfig": {"ScheduleExpression": "cron(0 * ? * * *)"},
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
                            "EndpointName": os.environ["SAGEMAKER_ENDPOINT_NAME"],
                            "LocalPath": "/opt/ml/processing/input/monitoring_dataset_input",
                            "S3InputMode": "File",
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    }
                ],
                "MonitoringOutputConfig": {
                    "MonitoringOutputs": [
                        {
                            "S3Output": {
                                "S3Uri": f"s3://{assets_bucket}/{monitoring_output_location}",
                                "LocalPath": "/opt/ml/processing/output",
                                "S3UploadMode": "EndOfJob",
                            }
                        }
                    ]
                },
                "MonitoringResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": os.environ["INSTANCE_TYPE"],
                        "VolumeSizeInGB": int(os.environ["INSTANCE_VOLUME_SIZE"]),
                    }
                },
                "MonitoringAppSpecification": {
                    "ImageUri": get_built_in_model_monitor_container_uri(boto3.session.Session().region_name)
                },
                "StoppingCondition": {"MaxRuntimeInSeconds": int(os.environ["MAX_RUNTIME_SECONDS"])},
                "RoleArn": os.environ["ROLE_ARN"],
            },
        },
        "EndpointName": os.environ["SAGEMAKER_ENDPOINT_NAME"],
        "LastMonitoringExecutionSummary": {
            "MonitoringScheduleName": os.environ["MONITORING_SCHEDULE_NAME"],
            "ScheduledTime": datetime(2021, 1, 15),
            "CreationTime": datetime(2021, 1, 15),
            "LastModifiedTime": datetime(2021, 1, 15),
            "MonitoringExecutionStatus": "CompletedWithViolations",
            "EndpointName": os.environ["SAGEMAKER_ENDPOINT_NAME"],
        },
        "ResponseMetadata": {
            "RequestId": "958ef6e6-f062-44b8-8a9c-c13f25f60050",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "958ef6e6-f062-44b8-8a9c-c13f25f60050",
                "content-type": "application/x-amz-json-1.1",
                "content-length": "2442",
                "date": "Fri, 15 Jan 2021 07:33:21 GMT",
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
