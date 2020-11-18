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

mock_env_variables = {
    "ENDPOINT_URI": "test/test",
}


@patch.dict(os.environ, mock_env_variables)
def test_invoke():

    sm_invoke_endpoint_expected_params = {
        "EndpointName": "test",
        "Body": "test",
        "ContentType": "text/csv",
    }

    event_body = {"payload": "test", "ContentType": "text/csv"}

    with patch('boto3.client') as mock_client:
        invoke(event_body, "test", sm_client=mock_client)
        mock_client.invoke_endpoint.assert_called_with(
            EndpointName="test",
            Body="test",
            ContentType="text/csv"
        )
