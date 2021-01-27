# #####################################################################################################################
#  Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                       #
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
import pytest
from unittest.mock import patch
from unittest import TestCase
import botocore.session
from botocore.stub import Stubber
from pipeline_orchestration.index import (
    handler,
    provision_pipeline,
    pipeline_status,
    DateTimeEncoder,
    get_template_parameters,
    get_required_keys,
    template_url,
    validate,
)
from shared.wrappers import BadRequest
from tests.fixtures.orchestrator_fixtures import (
    mock_env_variables,
    api_byom_event,
    required_api_byom_realtime_builtin,
    required_api_byom_batch_builtin,
    required_api_byom_realtime_custom,
    required_api_byom_batch_custom,
    api_model_monitor_event,
    required_api_keys_model_monitor,
    template_parameters_common,
    template_parameters_realtime_builtin,
    template_parameters_batch_builtin,
    template_parameters_realtime_custom,
    template_parameters_batch_custom,
    generate_names,
    template_parameters_model_monitor,
    get_parameters_keys,
    cf_client_params,
)


def test_handler():
    with patch("pipeline_orchestration.index.provision_pipeline") as mock_provision_pipeline:
        event = {
            "httpMethod": "POST",
            "path": "/provisionpipeline",
            "body": json.dumps({"test": "test"}),
        }
        handler(event, {})
        mock_provision_pipeline.assert_called_with(json.loads(event["body"]))

        event = {
            "pipeline_type": "test",
        }
        handler(event, {})
        mock_provision_pipeline.assert_called_with(event)

        event = {"should_return": "bad_request"}
        response = handler(event, {})
        assert response == {
            "statusCode": 400,
            "isBase64Encoded": False,
            "body": json.dumps(
                {
                    "message": "Bad request format. Expected httpMethod or pipeline_type, recevied none. "
                    + "Check documentation for API & config formats."
                }
            ),
            "headers": {"Content-Type": "plain/text"},
        }

    with patch("pipeline_orchestration.index.pipeline_status") as mock_pipeline_status:
        event = {
            "httpMethod": "POST",
            "path": "/pipelinestatus",
            "body": json.dumps({"test": "test"}),
        }
        handler(event, {})
        mock_pipeline_status.assert_called_with(json.loads(event["body"]))


def test_provision_pipeline(cf_client_params, api_byom_event):

    client = botocore.session.get_session().create_client("cloudformation")
    cp_client = botocore.session.get_session().create_client("codepipeline")

    stubber = Stubber(client)
    cp_stubber = Stubber(cp_client)
    cfn_response = {"StackId": "1234"}
    expected_params = cf_client_params
    expected_response = {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": json.dumps({"message": "success: stack creation started", "pipeline_id": "1234"}),
        "headers": {"Content-Type": "plain/text"},
    }
    event = api_byom_event("realtime", "xgboost")
    cfn_response = {"StackId": "1234"}
    stubber.add_response("create_stack", cfn_response, expected_params)
    with stubber:
        with cp_stubber:
            response = provision_pipeline(event, client)
            assert response == expected_response


def test_pipeline_status():

    cfn_client = botocore.session.get_session().create_client("cloudformation")
    cp_client = botocore.session.get_session().create_client("codepipeline")

    cfn_stubber = Stubber(cfn_client)
    cp_stubber = Stubber(cp_client)

    event = {
        "pipeline_id": "arn:aws:role:region:account:action",
    }
    cfn_expected_params = {"StackName": "arn:aws:role:region:account:action"}
    cp_expected_params = {"name": "testId"}

    cfn_response = {
        "StackResourceSummaries": [
            {
                "ResourceType": "AWS::CodePipeline::Pipeline",
                "PhysicalResourceId": "testId",
                "LogicalResourceId": "test",
                "ResourceStatus": "test",
                "LastUpdatedTimestamp": datetime.datetime(2000, 1, 1, 1, 1),
            }
        ]
    }

    cp_response = {
        "pipelineName": "string",
        "pipelineVersion": 123,
        "stageStates": [
            {
                "stageName": "string",
                "inboundTransitionState": {
                    "enabled": True,
                    "lastChangedBy": "string",
                    "lastChangedAt": datetime.datetime(2015, 1, 1),
                    "disabledReason": "string",
                },
                "actionStates": [
                    {
                        "actionName": "string",
                        "currentRevision": {
                            "revisionId": "string",
                            "revisionChangeId": "string",
                            "created": datetime.datetime(2015, 1, 1),
                        },
                        "latestExecution": {
                            "status": "InProgress",
                            "summary": "string",
                            "lastStatusChange": datetime.datetime(2015, 1, 1),
                            "token": "string",
                            "lastUpdatedBy": "string",
                            "externalExecutionId": "string",
                            "externalExecutionUrl": "string",
                            "percentComplete": 123,
                            "errorDetails": {"code": "string", "message": "string"},
                        },
                        "entityUrl": "string",
                        "revisionUrl": "string",
                    },
                ],
                "latestExecution": {
                    "pipelineExecutionId": "string",
                    "status": "InProgress",
                },
            },
        ],
        "created": datetime.datetime(2015, 1, 1),
        "updated": datetime.datetime(2015, 1, 1),
    }

    expected_response = {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": json.dumps(cp_response, indent=4, cls=DateTimeEncoder),
        "headers": {"Content-Type": "plain/text"},
    }
    cfn_stubber.add_response("list_stack_resources", cfn_response, cfn_expected_params)
    cp_stubber.add_response("get_pipeline_state", cp_response, cp_expected_params)

    with cfn_stubber:
        with cp_stubber:
            response = pipeline_status(event, cfn_client=cfn_client, cp_client=cp_client)
            assert response == expected_response


def test_get_required_keys(
    api_byom_event,
    api_model_monitor_event,
    required_api_byom_realtime_builtin,
    required_api_byom_batch_builtin,
    required_api_byom_realtime_custom,
    required_api_byom_batch_custom,
    required_api_keys_model_monitor,
):
    # Required keys in byom, realtime, builtin
    returned_keys = get_required_keys(api_byom_event("realtime", "xgboost"))
    expected_keys = required_api_byom_realtime_builtin
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in byom, batch, builtin
    returned_keys = get_required_keys(api_byom_event("batch", "xgboost"))
    expected_keys = required_api_byom_batch_builtin
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in byom, realtime, custom
    returned_keys = get_required_keys(api_byom_event("realtime", ""))
    expected_keys = required_api_byom_realtime_custom
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in byom, batch, custom
    returned_keys = get_required_keys(api_byom_event("batch", ""))
    expected_keys = required_api_byom_batch_custom
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in model_monitor, default (no monitoring_type provided)
    returned_keys = get_required_keys(api_model_monitor_event())
    expected_keys = required_api_keys_model_monitor()
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in model_monitor, with monitoring_type provided
    returned_keys = get_required_keys(api_model_monitor_event("modelquality"))
    expected_keys = required_api_keys_model_monitor(False)
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # assert for exceptions
    with pytest.raises(BadRequest) as exceinfo:
        get_required_keys({"pipeline_type": "not_supported"})
    assert (
        str(exceinfo.value)
        == "Bad request format. Pipeline type not supported. Check documentation for API & config formats"
    )
    with pytest.raises(BadRequest) as exceinfo:
        get_required_keys({"pipeline_type": "model_monitor", "monitoring_type": "not_supported"})
    assert (
        str(exceinfo.value)
        == "Bad request. MonitoringType supported are 'DataQuality'|'ModelQuality'|'ModelBias'|'ModelExplainability'"
    )
    with pytest.raises(BadRequest) as exceinfo:
        get_required_keys({"pipeline_type": "byom"})
    assert str(exceinfo.value) == "Bad request. missing keys for byom"


def test_template_url():
    # model monitor CF template
    assert (
        template_url("", "", "model_monitor")
        == "https://" + os.environ["BLUEPRINT_BUCKET_URL"] + "/blueprints/byom/model_monitor.yaml"
    )
    # realtime/builtin CF template
    assert (
        template_url("realtime", "", "byom")
        == "https://" + os.environ["BLUEPRINT_BUCKET_URL"] + "/blueprints/byom/byom_realtime_builtin_container.yaml"
    )
    # batch/builtin CF template
    assert (
        template_url("batch", "", "byom")
        == "https://" + os.environ["BLUEPRINT_BUCKET_URL"] + "/blueprints/byom/byom_batch_builtin_container.yaml"
    )
    # realtime/custom CF template
    assert (
        template_url("realtime", "my_custom_image.zip", "byom")
        == "https://" + os.environ["BLUEPRINT_BUCKET_URL"] + "/blueprints/byom/byom_realtime_build_container.yaml"
    )
    # batch/custom CF template
    assert (
        template_url("batch", "my_custom_image.zip", "byom")
        == "https://" + os.environ["BLUEPRINT_BUCKET_URL"] + "/blueprints/byom/byom_batch_build_container.yaml"
    )
    # assert for exceptions
    with pytest.raises(BadRequest) as exceinfo:
        template_url("notsupported", "my_custom_image.zip", "byom")
    assert str(exceinfo.value) == "Bad request format. Inference type must be 'realtime' or 'batch'"


def test_get_template_parameters(
    template_parameters_realtime_builtin,
    template_parameters_batch_builtin,
    template_parameters_realtime_custom,
    template_parameters_batch_custom,
    template_parameters_model_monitor,
    api_byom_event,
    api_model_monitor_event,
    get_parameters_keys,
):
    # assert template parameters: realtime/builtin
    _, returned_parameters = get_template_parameters(api_byom_event("realtime", "xgboost"))
    expected_parameters = template_parameters_realtime_builtin(api_byom_event("realtime", "xgboost"))
    TestCase().assertCountEqual(get_parameters_keys(expected_parameters), get_parameters_keys(returned_parameters))
    # assert template parameters: batch/builtin
    _, returned_parameters = get_template_parameters(api_byom_event("batch", "xgboost"))
    expected_parameters = template_parameters_batch_builtin(api_byom_event("batch", "xgboost"))
    TestCase().assertCountEqual(get_parameters_keys(expected_parameters), get_parameters_keys(returned_parameters))
    # assert template parameters: realtime/custom
    _, returned_parameters = get_template_parameters(api_byom_event("realtime", ""))
    expected_parameters = template_parameters_realtime_custom(api_byom_event("realtime", ""))
    TestCase().assertCountEqual(get_parameters_keys(expected_parameters), get_parameters_keys(returned_parameters))
    # assert template parameters: batch/custom
    _, returned_parameters = get_template_parameters(api_byom_event("batch", ""))
    expected_parameters = template_parameters_batch_custom(api_byom_event("batch", ""))
    TestCase().assertCountEqual(get_parameters_keys(expected_parameters), get_parameters_keys(returned_parameters))
    # assert template parameters: model monitor
    _, returned_parameters = get_template_parameters(api_model_monitor_event())
    expected_parameters = template_parameters_model_monitor(api_model_monitor_event())
    TestCase().assertCountEqual(get_parameters_keys(expected_parameters), get_parameters_keys(returned_parameters))


def test_validate(api_byom_event):
    # event with required keys
    valid_event = api_byom_event("batch", "xgboost")
    TestCase().assertDictEqual(validate(valid_event), valid_event)
    # event with missing required keys
    bad_event = api_byom_event("batch", "xgboost")
    # remove required key
    del bad_event["model_artifact_location"]
    with pytest.raises(BadRequest) as execinfo:
        validate(bad_event)
    assert str(execinfo.value) == "Bad request. API body does not have the necessary parameter: model_artifact_location"