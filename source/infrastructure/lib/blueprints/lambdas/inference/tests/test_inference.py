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
from datetime import datetime
import unittest
from unittest.mock import MagicMock, patch
import pytest
import botocore.session
from botocore.stub import Stubber, ANY
import boto3
from shared.logger import get_logger
from main import handler, invoke

mock_env_variables = {"ENDPOINT_URI": "test/test", "SAGEMAKER_ENDPOINT_NAME": "test-endpoint"}


@pytest.fixture
def event():
    return {"body": '{"payload": "test", "content_type": "text/csv"}'}


@pytest.fixture
def expected_response():
    return {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": [1, 0, 1, 0],
        "headers": {"Content-Type": "plain/text"},
    }


@patch.dict(os.environ, mock_env_variables)
def test_invoke(event):
    with patch("boto3.client") as mock_client:
        invoke(json.loads(event["body"]), "test", sm_client=mock_client)
        mock_client.invoke_endpoint.assert_called_with(EndpointName="test", Body="test", ContentType="text/csv")


@patch("main.invoke")
@patch("boto3.client")
@patch.dict(os.environ, mock_env_variables)
def test_handler(mocked_client, mocked_invoke, event, expected_response):
    mocked_invoke.return_value = expected_response
    response = handler(event, {})
    assert response == expected_response
