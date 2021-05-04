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
import os
import json
import datetime
import boto3
import tempfile
import pytest
from unittest.mock import patch
from unittest import TestCase
import botocore.session
from botocore.stub import Stubber
from moto import mock_s3
from pipeline_orchestration.lambda_helpers import (
    clean_param,
    get_stack_name,
    get_common_realtime_batch_params,
    get_bacth_specific_params,
    get_model_monitor_params,
    get_image_builder_params,
    format_template_parameters,
    get_codepipeline_params,
    upload_file_to_s3,
    download_file_from_s3,
    get_image_uri,
    template_url,
    get_stage_param,
    create_template_zip_file,
    get_realtime_specific_params,
    get_template_parameters,
    get_required_keys,
    validate,
)
from pipeline_orchestration.index import (
    handler,
    provision_pipeline,
    create_codepipeline_stack,
    update_stack,
    pipeline_status,
    DateTimeEncoder,
)
from shared.wrappers import BadRequest
from tests.fixtures.orchestrator_fixtures import (
    mock_env_variables,
    api_byom_event,
    expected_params_realtime_custom,
    expected_common_realtime_batch_params,
    expected_realtime_specific_params,
    expected_batch_specific_params,
    stack_name,
    api_monitor_event,
    expcted_update_response,
    expected_model_monitor_params,
    required_api_image_builder,
    expected_batch_params,
    api_image_builder_event,
    expected_image_builder_params,
    expect_single_account_params_format,
    expected_multi_account_params_format,
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
    template_parameters_model_monitor,
    get_parameters_keys,
    cf_client_params,
)


content_type = "plain/text"


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
            "headers": {"Content-Type": content_type},
        }

        event = {
            "httpMethod": "POST",
            "path": "/doesnotexist",
            "body": json.dumps({"test": "test"}),
        }
        response = handler(event, {})
        assert response == {
            "statusCode": 400,
            "isBase64Encoded": False,
            "body": json.dumps(
                {"message": "Unacceptable event path. Path must be /provisionpipeline or /pipelinestatus"}
            ),
            "headers": {"Content-Type": content_type},
        }

    with patch("pipeline_orchestration.index.pipeline_status") as mock_pipeline_status:
        event = {
            "httpMethod": "POST",
            "path": "/pipelinestatus",
            "body": json.dumps({"test": "test"}),
        }
        handler(event, {})
        mock_pipeline_status.assert_called_with(json.loads(event["body"]))


def test_clean_param():
    test_path = "path/to/prefix"
    TestCase().assertEqual(clean_param(f"{test_path}/"), test_path)
    TestCase().assertEqual(clean_param(test_path), test_path)


def test_template_url():
    url = "https://" + os.environ["BLUEPRINT_BUCKET_URL"] + "/blueprints/byom"
    TestCase().assertEqual(template_url("byom_batch_custom"), "blueprints/byom/byom_batch_pipeline.yaml")
    TestCase().assertEqual(template_url("single_account_codepipeline"), f"{url}/single_account_codepipeline.yaml")
    with pytest.raises(Exception):
        template_url("byom_not_supported")


def test_provision_pipeline(api_image_builder_event, api_byom_event):
    client = botocore.session.get_session().create_client("cloudformation")
    stubber = Stubber(client)
    expected_response = {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": json.dumps({"message": "success: stack creation started", "pipeline_id": "1234"}),
        "headers": {"Content-Type": content_type},
    }
    # The stubber will be called twice
    stubber.add_response("create_stack", {"StackId": "1234"})
    stubber.add_response("create_stack", {"StackId": "1234"})
    with stubber:
        with mock_s3():
            event = api_image_builder_event
            response = provision_pipeline(event, client)
            assert response == expected_response
            event = api_byom_event("byom_realtime_builtin")
            s3_client = boto3.client("s3", region_name="us-east-1")
            testfile = tempfile.NamedTemporaryFile()
            s3_client.create_bucket(Bucket="testbucket")
            upload_file_to_s3(
                testfile.name, "testbucket", "blueprints/byom/byom_realtime_inference_pipeline.yaml", s3_client
            )
            s3_client.create_bucket(Bucket="testassetsbucket")
            response = provision_pipeline(event, client, s3_client)
            assert response == expected_response


@mock_s3
def test_upload_file_to_s3():
    s3_clinet = boto3.client("s3", region_name="us-east-1")
    testfile = tempfile.NamedTemporaryFile()
    s3_clinet.create_bucket(Bucket="assetsbucket")
    upload_file_to_s3(testfile.name, "assetsbucket", os.environ["TESTFILE"], s3_clinet)


@mock_s3
def test_download_file_from_s3():
    s3_clinet = boto3.client("s3", region_name="us-east-1")
    testfile = tempfile.NamedTemporaryFile()
    s3_clinet.create_bucket(Bucket="assetsbucket")
    upload_file_to_s3(testfile.name, "assetsbucket", os.environ["TESTFILE"], s3_clinet)
    download_file_from_s3("assetsbucket", os.environ["TESTFILE"], testfile.name, s3_clinet)


def test_create_codepipeline_stack(cf_client_params, stack_name, expcted_update_response):
    cf_client = botocore.session.get_session().create_client("cloudformation")
    not_image_satck = "teststack-testmodel-BYOMPipelineReatimeBuiltIn"
    stubber = Stubber(cf_client)
    expected_params = cf_client_params
    cfn_response = {"StackId": "1234"}

    stubber.add_response("create_stack", cfn_response, expected_params)
    with stubber:
        response = create_codepipeline_stack(
            not_image_satck,
            expected_params["TemplateURL"],
            expected_params["Parameters"],
            cf_client,
        )
        assert response["StackId"] == cfn_response["StackId"]

    stubber.add_client_error("create_stack", expected_params=expected_params)

    with stubber:
        with pytest.raises(Exception):
            create_codepipeline_stack(
                not_image_satck,
                expected_params["TemplateURL"],
                expected_params["Parameters"],
                cf_client,
            )
    stubber.add_client_error("create_stack", service_message="already exists")
    expected_response = {"StackId": f"Pipeline {not_image_satck} is already provisioned. Updating template parameters."}
    with stubber:
        response = create_codepipeline_stack(
            not_image_satck,
            expected_params["TemplateURL"],
            expected_params["Parameters"],
            cf_client,
        )

        assert response == expected_response

    # Test if the stack is image builder
    stubber.add_client_error("create_stack", service_message="already exists")
    stubber.add_client_error("update_stack", service_message="No updates are to be performed")
    expected_response = expcted_update_response
    with stubber:
        response = create_codepipeline_stack(
            stack_name,
            expected_params["TemplateURL"],
            expected_params["Parameters"],
            cf_client,
        )

        assert response == expected_response


def test_update_stack(cf_client_params, stack_name, expcted_update_response):
    cf_client = botocore.session.get_session().create_client("cloudformation")

    expected_params = cf_client_params
    stubber = Stubber(cf_client)
    expected_params["StackName"] = stack_name
    expected_params["Tags"] = [{"Key": "stack_name", "Value": stack_name}]
    del expected_params["OnFailure"]
    cfn_response = {"StackId": f"Pipeline {stack_name} is being updated."}

    stubber.add_response("update_stack", cfn_response, expected_params)

    with stubber:
        response = update_stack(
            stack_name,
            expected_params["TemplateURL"],
            expected_params["Parameters"],
            cf_client,
        )
        assert response == cfn_response

    # Test for no update error
    stubber.add_client_error("update_stack", service_message="No updates are to be performed")
    expected_response = expcted_update_response
    with stubber:
        response = update_stack(
            stack_name,
            expected_params["TemplateURL"],
            expected_params["Parameters"],
            cf_client,
        )
        assert response == expected_response

    # Test for other exceptions
    stubber.add_client_error("update_stack", service_message="Some Exception")
    with stubber:
        with pytest.raises(Exception):
            update_stack(
                stack_name,
                expected_params["TemplateURL"],
                expected_params["Parameters"],
                cf_client,
            )


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
        "headers": {"Content-Type": content_type},
    }

    cfn_stubber.add_response("list_stack_resources", cfn_response, cfn_expected_params)
    cp_stubber.add_response("get_pipeline_state", cp_response, cp_expected_params)

    with cfn_stubber:
        with cp_stubber:
            response = pipeline_status(event, cfn_client=cfn_client, cp_client=cp_client)
            assert response == expected_response

    # test codepipeline has not been created yet
    no_cp_cfn_response = {
        "StackResourceSummaries": [
            {
                "ResourceType": "AWS::CodeBuild::Project",
                "PhysicalResourceId": "testId",
                "LogicalResourceId": "test",
                "ResourceStatus": "test",
                "LastUpdatedTimestamp": datetime.datetime(2000, 1, 1, 1, 1),
            }
        ]
    }

    expected_response_no_cp = {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": "pipeline cloudformation stack has not provisioned the pipeline yet.",
        "headers": {"Content-Type": content_type},
    }
    cfn_stubber.add_response("list_stack_resources", no_cp_cfn_response, cfn_expected_params)

    with cfn_stubber:
        with cp_stubber:
            response = pipeline_status(event, cfn_client=cfn_client, cp_client=cp_client)
            assert response == expected_response_no_cp


def test_get_stack_name(api_byom_event, api_monitor_event, api_image_builder_event):
    # realtime builtin pipeline
    realtime_builtin = api_byom_event("byom_realtime_builtin")
    assert (
        get_stack_name(realtime_builtin)
        == f"mlops-pipeline-{realtime_builtin['model_name']}-byompipelinerealtimebuiltin"
    )
    # batch builtin pipeline
    batch_builtin = api_byom_event("byom_batch_builtin")
    assert get_stack_name(batch_builtin) == f"mlops-pipeline-{batch_builtin['model_name']}-byompipelinebatchbuiltin"

    # model monitor pipeline
    assert get_stack_name(api_monitor_event) == f"mlops-pipeline-{api_monitor_event['model_name']}-byommodelmonitor"

    # image builder pipeline
    assert (
        get_stack_name(api_image_builder_event)
        == f"mlops-pipeline-{api_image_builder_event['image_tag']}-byompipelineimagebuilder"
    )


def test_get_required_keys(
    api_byom_event,  # NOSONAR:S107 this test function is designed to take many fixtures
    api_monitor_event,
    required_api_byom_realtime_builtin,
    required_api_byom_batch_builtin,
    required_api_byom_realtime_custom,
    required_api_byom_batch_custom,
    required_api_keys_model_monitor,
    required_api_image_builder,
):
    # Required keys in byom, realtime, builtin
    returned_keys = get_required_keys("byom_realtime_builtin")
    expected_keys = required_api_byom_realtime_builtin
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in byom, batch, builtin
    returned_keys = get_required_keys("byom_batch_builtin")
    expected_keys = required_api_byom_batch_builtin
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in byom, realtime, custom
    returned_keys = get_required_keys("byom_realtime_custom")
    expected_keys = required_api_byom_realtime_custom
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in byom, batch, custom
    returned_keys = get_required_keys("byom_batch_custom")
    expected_keys = required_api_byom_batch_custom
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in model_monitor, default (no monitoring_type provided)
    returned_keys = get_required_keys("byom_model_monitor")
    expected_keys = required_api_keys_model_monitor()
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in model_monitor, with monitoring_type provided
    returned_keys = get_required_keys("byom_model_monitor")
    expected_keys = required_api_keys_model_monitor(True)
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in image builder
    returned_keys = get_required_keys("byom_image_builder")
    expected_keys = required_api_image_builder
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # assert for exceptions
    with pytest.raises(BadRequest) as exceinfo:
        get_required_keys({"pipeline_type": "not_supported"})
    assert (
        str(exceinfo.value)
        == "Bad request format. Pipeline type not supported. Check documentation for API & config formats"
    )


def test_get_stage_param(api_byom_event):
    single_event = api_byom_event("byom_realtime_custom", False)
    TestCase().assertEqual(get_stage_param(single_event, "data_capture_location", None), "bucket/datacapture")
    multi_event = api_byom_event("byom_realtime_custom", True)
    TestCase().assertEqual(get_stage_param(multi_event, "data_capture_location", "dev"), "bucket/dev_datacapture")


def test_get_template_parameters(
    api_byom_event,
    api_image_builder_event,
    expected_params_realtime_custom,
    expected_image_builder_params,
    expected_batch_params,
):
    single_event = api_byom_event("byom_realtime_custom", False)
    TestCase().assertEqual(get_template_parameters(single_event, False), expected_params_realtime_custom)
    TestCase().assertEqual(get_template_parameters(api_image_builder_event, False), expected_image_builder_params)
    TestCase().assertEqual(
        get_template_parameters(api_byom_event("byom_batch_custom", False), False),
        expected_batch_params,
    )

    # test for exception
    with pytest.raises(BadRequest):
        get_template_parameters({"pipeline_type": "unsupported"}, False)


def test_get_common_realtime_batch_params(api_byom_event, expected_common_realtime_batch_params):
    realtime_event = api_byom_event("byom_realtime_custom", False)
    batch_event = api_byom_event("byom_batch_custom", False)
    realtime_event.update(batch_event)
    TestCase().assertEqual(
        get_common_realtime_batch_params(realtime_event, False, None), expected_common_realtime_batch_params
    )


def test_get_realtime_specific_params(api_byom_event, expected_realtime_specific_params):
    realtime_event = api_byom_event("byom_realtime_builtin", False)
    TestCase().assertEqual(get_realtime_specific_params(realtime_event, None), expected_realtime_specific_params)


def test_get_bacth_specific_params(api_byom_event, expected_batch_specific_params):
    batch_event = api_byom_event("byom_batch_custom", False)
    TestCase().assertEqual(get_bacth_specific_params(batch_event, None), expected_batch_specific_params)


def test_get_model_monitor_params(api_monitor_event, expected_model_monitor_params):
    TestCase().assertEqual(
        len(get_model_monitor_params(api_monitor_event, "us-east-1", None)), len(expected_model_monitor_params)
    )


def test_get_image_builder_params(api_image_builder_event, expected_image_builder_params):
    TestCase().assertEqual(get_image_builder_params(api_image_builder_event), expected_image_builder_params)


def test_format_template_parameters(
    expected_image_builder_params, expected_multi_account_params_format, expect_single_account_params_format
):
    TestCase().assertEqual(
        format_template_parameters(expected_image_builder_params, "True"), expected_multi_account_params_format
    )
    TestCase().assertEqual(
        format_template_parameters(expected_image_builder_params, "False"), expect_single_account_params_format
    )


@patch("lambda_helpers.sagemaker.image_uris.retrieve")
def test_get_image_uri(mocked_sm, api_byom_event):
    custom_event = api_byom_event("byom_realtime_custom", False)
    TestCase().assertEqual(get_image_uri("byom_realtime_custom", custom_event, "us-east-1"), "custom-image-uri")
    mocked_sm.return_value = "test-imge-uri"
    builtin_event = api_byom_event("byom_realtime_builtin", False)
    TestCase().assertEqual(get_image_uri("byom_realtime_builtin", builtin_event, "us-east-1"), "test-imge-uri")
    mocked_sm.assert_called_with(
        framework=builtin_event.get("model_framework"),
        region="us-east-1",
        version=builtin_event.get("model_framework_version"),
    )


@patch("boto3.client")
@patch("builtins.open")
@patch("lambda_helpers.shutil.make_archive")
@patch("lambda_helpers.write_params_to_json")
@patch("lambda_helpers.format_template_parameters")
@patch("lambda_helpers.get_template_parameters")
@patch("index.os.makedirs")
@patch("index.os.path.exists")
def test_create_template_zip_file(
    mocked_path,  # NOSONAR:S107 this test function is designed to take many fixtures
    mocked_mkdir,
    mocked_get_template,
    mocked_format,
    mocked_wrire,
    mocked_shutil,
    mocked_open,
    mocked_client,
    api_monitor_event,
):
    mocked_path.return_value = False
    s3_clinet = boto3.client("s3", region_name="us-east-1")
    # multi account
    create_template_zip_file(
        api_monitor_event, "blueprint", "assets_bucket", "byom/template.yaml", "zipfile", "True", s3_clinet
    )
    # single account
    create_template_zip_file(
        api_monitor_event, "blueprint", "assets_bucket", "byom/template.yaml", "zipfile", "False", s3_clinet
    )


def test_get_codepipeline_params():
    common_params = [
        ("NOTIFICATIONEMAIL", "test@example.com"),
        ("TEMPLATEZIPNAME", "template_zip_name"),
        ("TEMPLATEFILENAME", "template_file_name"),
        ("ASSETSBUCKET", "testassetsbucket"),
        ("STACKNAME", "stack_name"),
    ]
    # multi account codepipeline
    TestCase().assertEqual(
        get_codepipeline_params("True", "stack_name", "template_zip_name", "template_file_name"),
        common_params
        + [
            ("DEVPARAMSNAME", "dev_template_params.json"),
            ("STAGINGPARAMSNAME", "staging_template_params.json"),
            ("PRODPARAMSNAME", "prod_template_params.json"),
            ("DEVACCOUNTID", "dev_account_id"),
            ("DEVORGID", "dev_org_id"),
            ("STAGINGACCOUNTID", "staging_account_id"),
            ("STAGINGORGID", "staging_org_id"),
            ("PRODACCOUNTID", "prod_account_id"),
            ("PRODORGID", "prod_org_id"),
            ("BLUEPRINTBUCKET", "testbucket"),
        ],
    )
    # single account codepipeline
    TestCase().assertEqual(
        get_codepipeline_params("False", "stack_name", "template_zip_name", "template_file_name"),
        common_params + [("TEMPLATEPARAMSNAME", "template_params.json")],
    )


def test_validate(api_byom_event):
    # event with required keys
    valid_event = api_byom_event("byom_realtime_builtin")
    TestCase().assertDictEqual(validate(valid_event), valid_event)
    # event with missing required keys
    bad_event = api_byom_event("byom_batch_builtin")
    # remove required key
    del bad_event["model_artifact_location"]
    with pytest.raises(BadRequest) as execinfo:
        validate(bad_event)
    assert str(execinfo.value) == "Bad request. API body does not have the necessary parameter: model_artifact_location"
