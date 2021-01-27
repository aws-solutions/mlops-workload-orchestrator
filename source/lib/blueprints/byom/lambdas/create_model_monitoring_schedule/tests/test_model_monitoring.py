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
from unittest.mock import MagicMock, patch
import pytest
import boto3
from datetime import datetime
from moto import mock_sts
import botocore.session
from botocore.stub import Stubber, ANY
from main import handler
from shared.helper import get_client, reset_client, get_built_in_model_monitor_container_uri
from tests.fixtures.monitoring_fixtures import (
    mock_env_variables,
    sm_describe_monitoring_scheduale_params,
    sm_create_monitoring_expected_params,
    sm_create_monitoring_response_200,
    sm_describe_monitoring_schedule_response,
    cp_expected_params_success,
    cp_expected_params_failure,
    event,
)


@mock_sts
def test_handler_success(
    sm_create_monitoring_expected_params,
    sm_create_monitoring_response_200,
    sm_describe_monitoring_schedule_response,
    cp_expected_params_success,
    sm_describe_monitoring_scheduale_params,
    event,
):

    sm_client = get_client("sagemaker")
    cp_client = get_client("codepipeline")

    sm_stubber = Stubber(sm_client)
    cp_stubber = Stubber(cp_client)

    cp_response = {}

    # job creation
    sm_stubber.add_client_error(
        "describe_monitoring_schedule",
        service_error_code="MonitorJobExists",
        service_message="Could not find requested job with name",
        http_status_code=400,
        expected_params=sm_describe_monitoring_scheduale_params,
    )

    # success path
    sm_stubber.add_response(
        "create_monitoring_schedule", sm_create_monitoring_response_200, sm_create_monitoring_expected_params
    )

    sm_stubber.add_response(
        "describe_monitoring_schedule",
        sm_describe_monitoring_schedule_response,
        sm_describe_monitoring_scheduale_params,
    )

    cp_stubber.add_response("put_job_success_result", cp_response, cp_expected_params_success)

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
