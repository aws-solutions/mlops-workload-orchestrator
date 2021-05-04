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
import boto3
import pytest
from unittest.mock import patch
from moto import mock_lambda
from index import invoke_lambda, no_op, handler


@pytest.fixture()
def invoke_event():
    return {
        "RequestType": "Create",
        "ResourceProperties": {
            "Resource": "InvokeLambda",
            "function_name": "myfunction",
            "message": "Start batch transform job",
        },
    }


@pytest.fixture()
def invoke_bad_event():
    return {
        "RequestType": "Create",
        "ResourceProperties": {
            "Resource": "NotSupported",
        },
    }


@patch("boto3.client")
def test_invoke_lambda(mocked_client, invoke_event, invoke_bad_event):
    response = invoke_lambda(invoke_event, None, mocked_client)
    assert response is not None
    # unsupported
    with pytest.raises(Exception) as error:
        invoke_lambda(invoke_bad_event, None, mocked_client)
    assert str(error.value) == (
        f"The Resource {invoke_bad_event['ResourceProperties']['Resource']} "
        f"is unsupported by the Invoke Lambda custom resource."
    )


@mock_lambda
def test_invoke_lambda_error(invoke_event):
    mocked_client = boto3.client("lambda")
    with pytest.raises(Exception):
        invoke_lambda(invoke_event, None, mocked_client)


@patch("index.invoke_lambda")
def test_no_op(mocked_invoke, invoke_event):
    response = no_op(invoke_event, {})
    assert response is None
    mocked_invoke.assert_not_called()


@patch("index.helper")
def test_handler(mocked_helper, invoke_event):
    handler(invoke_event, {})
    mocked_helper.assert_called_with(invoke_event, {})
