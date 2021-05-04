#######################################################################################################################
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
        "batch_job_output_location": "output-location",
        "kms_key_arn": "mykey",
    }
    os.environ = {**os.environ, **new_env}


@pytest.fixture
def sm_expected_params():
    return {
        "TransformJobName": ANY,
        "ModelName": "test",
        "TransformOutput": {"S3OutputPath": ANY, "Accept": "text/csv", "AssembleWith": "Line", "KmsKeyId": "mykey"},
        "TransformInput": {
            "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": ANY}},
            "ContentType": "text/csv",
            "SplitType": "Line",
            "CompressionType": "None",
        },
        "TransformResources": {"InstanceType": ANY, "InstanceCount": 1, "VolumeKmsKeyId": "mykey"},
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


@pytest.fixture()
def event():
    return {
        "CodePipeline.job": {"id": "test_job_id"},
    }


@mock_sts
def test_handler_success(sm_expected_params, sm_response_200, event):
    sm_client = get_client("sagemaker")
    sm_stubber = Stubber(sm_client)

    # success path
    sm_stubber.add_response("create_transform_job", sm_response_200, sm_expected_params)

    with sm_stubber:
        handler(event, {})
        reset_client()


@mock_sts
def test_handler_fail(sm_expected_params, sm_response_500, event):
    sm_client = get_client("sagemaker")
    sm_stubber = Stubber(sm_client)

    # fail path
    sm_stubber.add_response("create_transform_job", sm_response_500, sm_expected_params)

    with pytest.raises(Exception):
        handler(event, {})

    reset_client()
