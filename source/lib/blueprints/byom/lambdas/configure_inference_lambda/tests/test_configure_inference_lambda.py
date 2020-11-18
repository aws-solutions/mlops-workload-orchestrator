##################################################################################################################
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
import datetime
import unittest
from unittest.mock import MagicMock, patch
import pytest
import boto3
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
        "inference_lambda_arn": "testname"
    }
    os.environ = {**os.environ, **new_env}

@pytest.fixture
def lm_expected_params():
    return {
        "FunctionName": ANY,
        "Environment": {"Variables": {"ENDPOINT_NAME": "test", "LOG_LEVEL": "INFO"}},
    }


@pytest.fixture
def cp_expected_params_success():
    return {"jobId": "test_job_id"}


@pytest.fixture
def cp_expected_params_failure():
    return {
        "jobId": "test_job_id",
        "failureDetails": {
           'message': ANY,
           'type': 'JobFailed'
        }
    }


@pytest.fixture
def lm_response_200():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "FunctionName": "string",
        "FunctionArn": "string",
        "Runtime": "nodejs",
        "Role": "string",
        "Handler": "string",
        "CodeSize": 123,
        "Description": "string",
        "Timeout": 1,
        "MemorySize": 129,
        "LastModified": "string",
        "CodeSha256": "string",
        "Version": "string",
        "State": "Active",
        "StateReason": "string",
        "StateReasonCode": "Idle",
        "LastUpdateStatus": "Successful",
        "LastUpdateStatusReason": "string",
        "LastUpdateStatusReasonCode": "EniLimitExceeded",
        "FileSystemConfigs": [
            {"Arn": "string", "LocalMountPath": "string"},
        ],
    }

@pytest.fixture
def lm_response_500():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 500},
        "FunctionName": "string",
        "FunctionArn": "string",
        "Runtime": "nodejs",
        "Role": "string",
        "Handler": "string",
        "CodeSize": 123,
        "Description": "string",
        "Timeout": 1,
        "MemorySize": 129,
        "LastModified": "string",
        "CodeSha256": "string",
        "Version": "string",
        "State": "Active",
        "StateReason": "string",
        "StateReasonCode": "Idle",
        "LastUpdateStatus": "Successful",
        "LastUpdateStatusReason": "string",
        "LastUpdateStatusReasonCode": "EniLimitExceeded",
        "FileSystemConfigs": [
            {"Arn": "string", "LocalMountPath": "string"},
        ],
    }


@pytest.fixture
def event():
    return {
        "CodePipeline.job": {
            "id": "test_job_id",
            "data": {
                "actionConfiguration": {
                    "configuration": {
                        "UserParameters": json.dumps({"0": {"endpointName": "test"}})
                    }
                }
            },
        },
    }

@mock_sts
def test_handler_success(lm_expected_params, lm_response_200, cp_expected_params_success, event):
    lm_client = get_client("lambda")
    lm_stubber = Stubber(lm_client)
    cp_client = get_client("codepipeline")
    cp_stubber = Stubber(cp_client)

    cp_response = {}

    lm_stubber.add_response("update_function_configuration", lm_response_200, lm_expected_params)
    cp_stubber.add_response("put_job_success_result", cp_response, cp_expected_params_success)

    with lm_stubber:
        with cp_stubber:
            handler(event, {})
            cp_stubber.assert_no_pending_responses()
            reset_client()


def test_handler_failure(lm_expected_params, lm_response_500, cp_expected_params_failure, event):
    lm_client = get_client("lambda")
    lm_stubber = Stubber(lm_client)
    cp_client = get_client("codepipeline")
    cp_stubber = Stubber(cp_client)

    cp_response = {}

    lm_stubber.add_response("update_function_configuration", lm_response_500, lm_expected_params)
    cp_stubber.add_response("put_job_failure_result", cp_response, cp_expected_params_failure)

    with lm_stubber:
        with cp_stubber:
            handler(event, {})
            cp_stubber.assert_no_pending_responses()
            reset_client()


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
