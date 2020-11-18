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
from unittest.mock import MagicMock, patch
import pytest
from moto import mock_sts
import botocore.session
from botocore.stub import Stubber, ANY
from main import handler
from shared.helper import get_client, reset_client


@pytest.fixture(autouse=True)
def mock_env_variables():
    new_env = {
        "model_name": "test",
        "assets_bucket": "testbucket",
        "batch_inference_data": "test",
        "inference_instance": "ml.m5.4xlarge",
    }
    os.environ = {**os.environ, **new_env}

@pytest.fixture
def sm_expected_params():
    return {
        "TransformJobName": ANY,
        "ModelName": "test",
        "TransformOutput": {
            "S3OutputPath": ANY,
            "Accept": "text/csv",
            "AssembleWith": "Line",
        },
        "TransformInput": {
            "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": ANY}},
            "ContentType": "text/csv",
            "SplitType": "Line",
            "CompressionType": "None",
        },
        "TransformResources": {"InstanceType": ANY, "InstanceCount": 1},
    }


@pytest.fixture
def sm_response_200():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "TransformJobArn": "arn:aws:sagemaker:region:account:transform-job/name",
    }


@pytest.fixture
def sm_response_500():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 500},
        "TransformJobArn": "arn:aws:sagemaker:region:account:transform-job/name",
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

@pytest.fixture()
def event():
    return {
        "CodePipeline.job": {"id": "test_job_id"},
    }

@mock_sts
def test_handler_success(sm_expected_params, sm_response_200, cp_expected_params_success, event):

    sm_client = get_client("sagemaker")
    cp_client = get_client("codepipeline")

    sm_stubber = Stubber(sm_client)
    cp_stubber = Stubber(cp_client)

    cp_response = {}

    # success path
    sm_stubber.add_response("create_transform_job", sm_response_200, sm_expected_params)
    cp_stubber.add_response("put_job_success_result", cp_response, cp_expected_params_success)

    with sm_stubber:
        with cp_stubber:
            handler(event, {})
            cp_stubber.assert_no_pending_responses()
            reset_client()



@mock_sts
def test_handler_fail(sm_expected_params, sm_response_500, cp_expected_params_failure, event):
    sm_client = get_client("sagemaker")
    cp_client = get_client("codepipeline")

    sm_stubber = Stubber(sm_client)
    cp_stubber = Stubber(cp_client)

    cp_response = {}
    # fail path
    sm_stubber.add_response("create_transform_job", sm_response_500, sm_expected_params)
    cp_stubber.add_response("put_job_failure_result", cp_response, cp_expected_params_failure)

    with sm_stubber:
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
