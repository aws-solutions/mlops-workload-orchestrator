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
from unittest.mock import patch
from moto import mock_sts
from botocore.stub import Stubber
from main import handler
from shared.helper import get_client, reset_client, get_built_in_model_monitor_container_uri
from tests.fixtures.baseline_fixtures import (
    mock_env_variables,
    sm_create_baseline_expected_params,
    sm_create_job_response_200,
    event,
)


@mock_sts
def test_handler_success(
    sm_create_baseline_expected_params,
    sm_create_job_response_200,
    event,
):

    sm_client = get_client("sagemaker")
    sm_stubber = Stubber(sm_client)

    # success path
    sm_stubber.add_response("create_processing_job", sm_create_job_response_200, sm_create_baseline_expected_params)

    with sm_stubber:
        handler(event, {})
        reset_client()


def test_handler_exception(event):
    with patch("boto3.client"):
        handler(event, context={})
        reset_client()
