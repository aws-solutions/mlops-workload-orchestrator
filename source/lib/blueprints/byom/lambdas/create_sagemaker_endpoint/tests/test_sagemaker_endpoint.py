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
import json
from datetime import datetime
import unittest
from unittest.mock import MagicMock, patch
import pytest
from moto import mock_sts
from botocore.stub import Stubber, ANY
from shared.logger import get_logger
from shared.helper import get_client, reset_client
from main import handler


@pytest.fixture(autouse=True)
def mock_env_variables():
    new_env = {
        "model_name": "test",
        "assets_bucket": "testbucket",
        "batch_inference_data": "test",
        "inference_instance": "test",
    }
    os.environ = {**os.environ, **new_env}


@pytest.fixture
def sm_describe_endpoint_config_params():
    return {"EndpointConfigName": "test-endpoint-config"}


@pytest.fixture
def sm_describe_endpoint_config_response():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "EndpointConfigName": "string",
        "EndpointConfigArn": "arn:aws:sagemaker:region:account:transform-job/name",
        "ProductionVariants": [
            {
                "VariantName": "string",
                "ModelName": "string",
                "InitialInstanceCount": 123,
                "InstanceType": "ml.t2.medium",
                "InitialVariantWeight": 1.0,
                "AcceleratorType": "ml.eia1.medium",
            },
        ],
        "DataCaptureConfig": {
            "EnableCapture": True,
            "InitialSamplingPercentage": 123,
            "DestinationS3Uri": "string",
            "KmsKeyId": "string",
            "CaptureOptions": [
                {"CaptureMode": "Input"},
            ],
            "CaptureContentTypeHeader": {
                "CsvContentTypes": [
                    "string",
                ],
            },
        },
        "KmsKeyId": "string",
        "CreationTime": datetime(2015, 1, 1),
    }


@pytest.fixture
def sm_create_endpoint_config_params():
    return {
        "EndpointConfigName": "test-endpoint-config",
        "ProductionVariants": [
            {
                "VariantName": "test-variant",
                "ModelName": "test",
                "InitialInstanceCount": 1,
                "InstanceType": "test",
            },
        ],
        "DataCaptureConfig": {
            "EnableCapture": True,
            "InitialSamplingPercentage": 100,
            "DestinationS3Uri": f"s3://testbucket/datacapture",
            "CaptureOptions": [{"CaptureMode": "Output"}, {"CaptureMode": "Input"}],
            "CaptureContentTypeHeader": {
                "CsvContentTypes": ["text/csv"],
            },
        },
    }


@pytest.fixture
def sm_create_endpoint_config_response():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "EndpointConfigArn": "arn:aws:sagemaker:region:account:transform-job/name",
    }


@pytest.fixture
def sm_create_endpoint_config_response_500():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "EndpointConfigArn": "arn:aws:sagemaker:region:account:transform-job/name",
    }


@pytest.fixture
def sm_describe_endpoint_params():
    return {"EndpointName": "test-endpoint"}


@pytest.fixture
def sm_create_endpoint_params():
    return {
        "EndpointName": "test-endpoint",
        "EndpointConfigName": "test-endpoint-config",
    }


@pytest.fixture
def sm_create_endpoint_response():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "EndpointArn": "arn:aws:sagemaker:region:account:endpoint/name",
    }


@pytest.fixture
def sm_describe_endpoint_response_2():
    return {
        "EndpointName": "string",
        "EndpointArn": "arn:aws:sagemaker:region:account:endpoint/name",
        "EndpointConfigName": "string",
        "ProductionVariants": [
            {
                "VariantName": "string",
                "DeployedImages": [
                    {
                        "SpecifiedImage": "string",
                        "ResolvedImage": "string",
                        "ResolutionTime": datetime(2015, 1, 1),
                    },
                ],
                "CurrentWeight": 1.0,
                "DesiredWeight": 1.0,
                "CurrentInstanceCount": 123,
                "DesiredInstanceCount": 123,
            },
        ],
        "DataCaptureConfig": {
            "EnableCapture": True,
            "CaptureStatus": "Started",
            "CurrentSamplingPercentage": 123,
            "DestinationS3Uri": "string",
            "KmsKeyId": "string",
        },
        "EndpointStatus": "InService",
        "FailureReason": "string",
        "CreationTime": datetime(2015, 1, 1),
        "LastModifiedTime": datetime(2015, 1, 1),
    }


@pytest.fixture
def cp_expected_params():
    return {
        "jobId": "test_job_id",
        "outputVariables": {
            "endpointName": "test-endpoint",
        },
    }


@pytest.fixture
def cp_expected_params_failure():
    return {
        "jobId": "test_job_id",
        "failureDetails": {"message": "Job failed. Check the logs for more info.", "type": "JobFailed"},
    }


@pytest.fixture
def event():
    return {
        "CodePipeline.job": {"id": "test_job_id"},
    }


@mock_sts
def test_handler_success(
    sm_describe_endpoint_config_params,
    sm_create_endpoint_config_params,
    sm_create_endpoint_config_response,
    cp_expected_params,
    sm_describe_endpoint_params,
    sm_create_endpoint_params,
    sm_create_endpoint_response,
    sm_describe_endpoint_response_2,
    event,
):

    sm_client = get_client("sagemaker")
    cp_client = get_client("codepipeline")

    sm_stubber = Stubber(sm_client)
    cp_stubber = Stubber(cp_client)

    # endpoint config creation
    sm_describe_endpoint_config_response = {}

    cp_response = {}

    sm_stubber.add_client_error(
        "describe_endpoint_config",
        service_error_code="EndpointConfigExists",
        service_message="Could not find endpoint configuration",
        http_status_code=400,
        expected_params=sm_describe_endpoint_config_params,
    )
    sm_stubber.add_response(
        "create_endpoint_config",
        sm_create_endpoint_config_response,
        sm_create_endpoint_config_params,
    )

    # endpoint creation
    sm_stubber.add_client_error(
        "describe_endpoint",
        service_error_code="EndpointExists",
        service_message="Could not find endpoint",
        http_status_code=400,
        expected_params=sm_describe_endpoint_params,
    )

    sm_stubber.add_response("create_endpoint", sm_create_endpoint_response, sm_create_endpoint_params)

    sm_stubber.add_response(
        "describe_endpoint",
        sm_describe_endpoint_response_2,
        sm_describe_endpoint_params,
    )

    cp_stubber.add_response("put_job_success_result", cp_response, cp_expected_params)

    expected_log_message = "Sent success message back to codepipeline with job_id: test_job_id"
    with sm_stubber:
        with cp_stubber:
            handler(event, {})
            cp_stubber.assert_no_pending_responses()
            reset_client()


# wrapper exception
def test_handler_exception():
    with patch("boto3.client") as mock_client:
        event = {
            "CodePipeline.job": {"id": "test_job_id"},
        }
        failure_message = {
            "message": "Job failed. Check the logs for more info.",
            "type": "JobFailed",
        }
        handler(event, context={})
        mock_client().put_job_failure_result.assert_called()