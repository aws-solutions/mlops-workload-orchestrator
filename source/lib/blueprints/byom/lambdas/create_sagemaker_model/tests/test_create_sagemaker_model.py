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
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from moto import mock_sts
from botocore.stub import Stubber, ANY
from shared.helper import get_client, reset_client
from main import handler


@pytest.fixture(autouse=True)
def mock_env_variables():
    new_env = {
        "model_name": "test",
        "assets_bucket": "testbucket",
        "batch_inference_data": "test",
        "inference_instance": "test",
        "container_uri": "test",
        "model_artifact_location": "test",
        "create_model_role_arn": "arn:aws:sagemaker:region:account:model/name",
    }
    os.environ = {**os.environ, **new_env}


@pytest.fixture
def sm_describe_model_expected_params():
    return {"ModelName": "test"}


@pytest.fixture
def sm_describe_model_response():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "ModelName": "string",
        "PrimaryContainer": {
            "ContainerHostname": "string",
            "Image": "string",
            "ImageConfig": {"RepositoryAccessMode": "Platform"},
            "Mode": "SingleModel",
            "ModelDataUrl": "string",
            "Environment": {"string": "string"},
            "ModelPackageName": "string",
        },
        "Containers": [
            {
                "ContainerHostname": "string",
                "Image": "string",
                "ImageConfig": {"RepositoryAccessMode": "Platform"},
                "Mode": "SingleModel",
                "ModelDataUrl": "string",
                "Environment": {"string": "string"},
                "ModelPackageName": "string",
            },
        ],
        "ExecutionRoleArn": "arn:aws:sagemaker:region:account:model/name",
        "VpcConfig": {
            "SecurityGroupIds": [
                "string",
            ],
            "Subnets": [
                "string",
            ],
        },
        "CreationTime": datetime(2015, 1, 1),
        "ModelArn": "arn:aws:sagemaker:region:account:model/name",
        "EnableNetworkIsolation": True,
    }


@pytest.fixture
def sm_delete_model_expected_params():
    return {"ModelName": "test"}


@pytest.fixture
def sm_create_model_expected_params():
    return {
        "ModelName": "test",
        "PrimaryContainer": {
            "Image": "test",
            "ImageConfig": {"RepositoryAccessMode": "Platform"},
            "ModelDataUrl": "test",
            "Mode": "SingleModel",
        },
        "ExecutionRoleArn": ANY,
        "EnableNetworkIsolation": False,
    }


@pytest.fixture
def sm_create_model_response():
    return {
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "ModelArn": "arn:aws:sagemaker:region:account:model/name",
    }


@pytest.fixture
def cp_expected_params():
    return {"jobId": "test_job_id"}


@pytest.fixture
def event():
    return {
        "CodePipeline.job": {"id": "test_job_id"},
    }


@mock_sts
def test_handler_success(
    sm_describe_model_expected_params,
    sm_describe_model_response,
    sm_delete_model_expected_params,
    sm_create_model_expected_params,
    sm_create_model_response,
    cp_expected_params,
    event,
):

    sm_client = get_client("sagemaker")
    cp_client = get_client("codepipeline")

    sm_stubber = Stubber(sm_client)
    cp_stubber = Stubber(cp_client)

    # describe model

    sm_stubber.add_response("describe_model", sm_describe_model_response, sm_describe_model_expected_params)

    # delete model
    sm_delete_model_response = {}
    sm_stubber.add_response("delete_model", sm_delete_model_response, sm_delete_model_expected_params)

    # create model
    sm_stubber.add_response("create_model", sm_create_model_response, sm_create_model_expected_params)

    # codepipeline
    cp_response = {}
    cp_stubber.add_response("put_job_success_result", cp_response, cp_expected_params)

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
