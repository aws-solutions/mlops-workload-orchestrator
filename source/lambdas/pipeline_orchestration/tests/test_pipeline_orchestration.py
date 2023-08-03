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
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from moto import mock_s3
from pipeline_orchestration.lambda_helpers import (
    clean_param,
    get_stack_name,
    get_common_realtime_batch_params,
    get_batch_specific_params,
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
    get_built_in_model_monitor_image_uri,
)
from pipeline_orchestration.index import (
    handler,
    provision_pipeline,
    create_codepipeline_stack,
    update_stack,
    pipeline_status,
    DateTimeEncoder,
    provision_model_card,
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
    stack_id,
    api_data_quality_event,
    api_model_quality_event,
    expected_update_response,
    expected_data_quality_monitor_params,
    expected_model_quality_monitor_params,
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
    api_model_bias_event,
    api_model_explainability_event,
    expected_model_bias_monitor_params,
    expected_model_explainability_monitor_params,
    required_api_keys_model_monitor,
    template_parameters_common,
    template_parameters_realtime_builtin,
    template_parameters_batch_builtin,
    template_parameters_realtime_custom,
    template_parameters_batch_custom,
    template_parameters_model_monitor,
    get_parameters_keys,
    cf_client_params,
    api_training_event,
)


content_type = "plain/text"


def test_handler():
    # event["path"] == "/provisionpipeline" and pipeline_type is model_crad operation
    with patch(
        "pipeline_orchestration.index.provision_model_card"
    ) as mock_provision_card:
        event = {
            "httpMethod": "POST",
            "path": "/provisionpipeline",
            "body": json.dumps({"pipeline_type": "create_model_card", "test": "test"}),
        }
        handler(event, {})
        assert mock_provision_card.called is True
    # event["path"] == "/provisionpipeline"
    with patch(
        "pipeline_orchestration.index.provision_pipeline"
    ) as mock_provision_pipeline:
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
                    "message": "A BadRequest exception occurred",
                    "detailedMessage": "Bad request format. Expected httpMethod or pipeline_type, received none. Check documentation for API & config formats.",
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
                {
                    "message": "A BadRequest exception occurred",
                    "detailedMessage": "Unacceptable event path. Path must be /provisionpipeline or /pipelinestatus",
                }
            ),
            "headers": {"Content-Type": content_type},
        }

    # test event["path"] == "/pipelinestatus"
    with patch("pipeline_orchestration.index.pipeline_status") as mock_pipeline_status:
        event = {
            "httpMethod": "POST",
            "path": "/pipelinestatus",
            "body": json.dumps({"test": "test"}),
        }
        handler(event, {})
        mock_pipeline_status.assert_called_with(json.loads(event["body"]))

        # test for client error exception
        mock_pipeline_status.side_effect = ClientError(
            {
                "Error": {"Code": "500", "Message": "Some error message"},
                "ResponseMetadata": {"HTTPStatusCode": 400},
            },
            "test",
        )
        response = handler(event, {})
        assert response == {
            "statusCode": 400,
            "isBase64Encoded": False,
            "body": json.dumps(
                {
                    "message": "A boto3 ClientError occurred",
                    "detailedMessage": "An error occurred (500) when calling the test operation: Some error message",
                }
            ),
            "headers": {"Content-Type": content_type},
        }

        # test for other exceptions
        message = "An Unexpected Server side exception occurred"
        mock_pipeline_status.side_effect = Exception(message)
        response = handler(event, {})
        assert response == {
            "statusCode": 500,
            "isBase64Encoded": False,
            "body": json.dumps(
                {
                    "message": message,
                    "detailedMessage": message,
                }
            ),
            "headers": {"Content-Type": content_type},
        }


def test_clean_param():
    test_path = "path/to/prefix"
    TestCase().assertEqual(clean_param(f"{test_path}/"), test_path)
    TestCase().assertEqual(clean_param(test_path), test_path)


def test_template_url():
    url = "https://" + os.environ["BLUEPRINT_BUCKET_URL"] + "/blueprints"
    TestCase().assertEqual(
        template_url("byom_batch_custom"), "blueprints/byom_batch_pipeline.yaml"
    )
    TestCase().assertEqual(
        template_url("single_account_codepipeline"),
        f"{url}/single_account_codepipeline.yaml",
    )
    with pytest.raises(Exception):
        template_url("byom_not_supported")


def test_provision_pipeline(api_image_builder_event, api_byom_event):
    client = botocore.session.get_session().create_client("cloudformation")
    stubber = Stubber(client)
    expected_response = {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": json.dumps(
            {"message": "success: stack creation started", "pipeline_id": "1234"}
        ),
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
                testfile.name,
                "testbucket",
                "blueprints/byom_realtime_inference_pipeline.yaml",
                s3_client,
            )
            s3_client.create_bucket(Bucket="testassetsbucket")
            response = provision_pipeline(event, client, s3_client)
            assert response == expected_response


@mock_s3
def test_upload_file_to_s3():
    s3_client = boto3.client("s3", region_name="us-east-1")
    testfile = tempfile.NamedTemporaryFile()
    s3_client.create_bucket(Bucket="assetsbucket")
    upload_file_to_s3(testfile.name, "assetsbucket", os.environ["TESTFILE"], s3_client)


@mock_s3
def test_download_file_from_s3():
    s3_client = boto3.client("s3", region_name="us-east-1")
    testfile = tempfile.NamedTemporaryFile()
    s3_client.create_bucket(Bucket="assetsbucket")
    upload_file_to_s3(testfile.name, "assetsbucket", os.environ["TESTFILE"], s3_client)
    download_file_from_s3(
        "assetsbucket", os.environ["TESTFILE"], testfile.name, s3_client
    )


def test_create_codepipeline_stack(
    cf_client_params, stack_name, stack_id, expected_update_response
):
    cf_client = botocore.session.get_session().create_client("cloudformation")
    not_image_stack = "teststack-testmodel-BYOMPipelineReatimeBuiltIn"
    stubber = Stubber(cf_client)
    expected_params = cf_client_params
    cfn_response = {"StackId": stack_id}

    stubber.add_response("create_stack", cfn_response, expected_params)
    with stubber:
        response = create_codepipeline_stack(
            not_image_stack,
            expected_params["TemplateURL"],
            expected_params["Parameters"],
            cf_client,
        )
        assert response["StackId"] == cfn_response["StackId"]

    stubber.add_client_error("create_stack", expected_params=expected_params)

    with stubber:
        with pytest.raises(Exception):
            create_codepipeline_stack(
                not_image_stack,
                expected_params["TemplateURL"],
                expected_params["Parameters"],
                cf_client,
            )
    stubber.add_client_error("create_stack", service_message="already exists")
    expected_response = {
        "StackId": stack_id,
        "message": f"Pipeline {not_image_stack} is already provisioned. Updating template parameters.",
    }
    describe_expected_params = {"StackName": not_image_stack}
    describe_cfn_response = {
        "Stacks": [
            {
                "StackId": stack_id,
                "StackName": not_image_stack,
                "CreationTime": "2021-11-03T00:23:37.630000+00:00",
                "StackStatus": "CREATE_COMPLETE",
            }
        ]
    }
    stubber.add_response(
        "describe_stacks", describe_cfn_response, describe_expected_params
    )
    with stubber:
        response = create_codepipeline_stack(
            not_image_stack,
            expected_params["TemplateURL"],
            expected_params["Parameters"],
            cf_client,
        )

        assert response == expected_response

    # Test if the stack is image builder
    describe_expected_params["StackName"] = stack_name
    describe_cfn_response["Stacks"][0]["StackName"] = stack_name
    stubber.add_client_error("create_stack", service_message="already exists")
    stubber.add_response(
        "describe_stacks", describe_cfn_response, describe_expected_params
    )
    stubber.add_client_error(
        "update_stack", service_message="No updates are to be performed"
    )
    expected_response = expected_update_response
    with stubber:
        response = create_codepipeline_stack(
            stack_name,
            expected_params["TemplateURL"],
            expected_params["Parameters"],
            cf_client,
        )

        assert response == expected_response


def test_update_stack(cf_client_params, stack_name, stack_id, expected_update_response):
    cf_client = botocore.session.get_session().create_client("cloudformation")
    expected_params = cf_client_params
    stubber = Stubber(cf_client)
    expected_params["StackName"] = stack_name
    expected_params["Tags"] = [{"Key": "stack_name", "Value": stack_name}]
    del expected_params["OnFailure"]
    cfn_response = {"StackId": stack_id}

    stubber.add_response("update_stack", cfn_response, expected_params)

    with stubber:
        response = update_stack(
            stack_name,
            expected_params["TemplateURL"],
            expected_params["Parameters"],
            cf_client,
            stack_id,
        )
        assert response == {
            **cfn_response,
            "message": f"Pipeline {stack_name} is being updated.",
        }

    # Test for no update error
    stubber.add_client_error(
        "update_stack", service_message="No updates are to be performed"
    )
    expected_response = expected_update_response
    with stubber:
        response = update_stack(
            stack_name,
            expected_params["TemplateURL"],
            expected_params["Parameters"],
            cf_client,
            stack_id,
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
                stack_id,
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
            response = pipeline_status(
                event, cfn_client=cfn_client, cp_client=cp_client
            )
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
    cfn_stubber.add_response(
        "list_stack_resources", no_cp_cfn_response, cfn_expected_params
    )

    with cfn_stubber:
        with cp_stubber:
            response = pipeline_status(
                event, cfn_client=cfn_client, cp_client=cp_client
            )
            assert response == expected_response_no_cp


def test_get_stack_name(
    api_byom_event,
    api_data_quality_event,
    api_model_quality_event,
    api_model_bias_event,
    api_model_explainability_event,
    api_image_builder_event,
):
    # realtime builtin pipeline
    realtime_builtin = api_byom_event("byom_realtime_builtin")
    assert (
        get_stack_name(realtime_builtin)
        == f"mlops-pipeline-{realtime_builtin['model_name']}-byompipelinerealtimebuiltin"
    )
    # batch builtin pipeline
    batch_builtin = api_byom_event("byom_batch_builtin")
    assert (
        get_stack_name(batch_builtin)
        == f"mlops-pipeline-{batch_builtin['model_name']}-byompipelinebatchbuiltin"
    )

    # data quality monitor pipeline
    assert (
        get_stack_name(api_data_quality_event)
        == f"mlops-pipeline-{api_data_quality_event['model_name']}-byomdataqualitymonitor"
    )

    # model quality monitor pipeline
    assert (
        get_stack_name(api_model_quality_event)
        == f"mlops-pipeline-{api_model_quality_event['model_name']}-byommodelqualitymonitor"
    )

    # model bias monitor pipeline
    assert (
        get_stack_name(api_model_bias_event)
        == f"mlops-pipeline-{api_model_bias_event['model_name']}-byommodelbiasmonitor"
    )

    # model explainability monitor pipeline
    assert (
        get_stack_name(api_model_explainability_event)
        == f"mlops-pipeline-{api_model_explainability_event['model_name']}-byommodelexplainabilitymonitor"
    )

    # image builder pipeline
    assert (
        get_stack_name(api_image_builder_event)
        == f"mlops-pipeline-{api_image_builder_event['image_tag']}-byompipelineimagebuilder"
    )


@patch("sagemaker.Session")
@patch("solution_model_card.SolutionModelCardAPIs.list_model_cards")
@patch("solution_model_card.SolutionModelCardAPIs.export_to_pdf")
@patch("solution_model_card.SolutionModelCardAPIs.delete")
@patch("solution_model_card.SolutionModelCardAPIs.describe")
@patch("solution_model_card.SolutionModelCardAPIs.update")
@patch("solution_model_card.SolutionModelCardAPIs.create")
def test_provision_model_card(
    patched_create,
    patched_update,
    patched_describe,
    patched_delete,
    patched_export,
    patched_list,
    patched_session,
):
    # assert the create APIs is called when pipeline_type=create_model_card
    event = dict(pipeline_type="create_model_card")
    provision_model_card(event, patched_session)
    assert patched_create.called is True

    # assert the create APIs is called when pipeline_type=update_model_card
    event["pipeline_type"] = "update_model_card"
    provision_model_card(event, patched_session)
    assert patched_update.called is True

    # assert the create APIs is called when pipeline_type=delete_model_card
    event["pipeline_type"] = "delete_model_card"
    provision_model_card(event, patched_session)
    assert patched_delete.called is True

    # assert the create APIs is called when pipeline_type=describe_model_card
    event["pipeline_type"] = "describe_model_card"
    provision_model_card(event, patched_session)
    assert patched_describe.called is True

    # assert the create APIs is called when pipeline_type=export_model_card
    event["pipeline_type"] = "export_model_card"
    provision_model_card(event, patched_session)
    assert patched_export.called is True

    # assert the create APIs is called when pipeline_type=list_model_cardd
    event["pipeline_type"] = "list_model_cards"
    provision_model_card(event, patched_session)
    assert patched_list.called is True

    # assert for error if the pipeline_type is incorrect
    event["pipeline_type"] = "wrong_pipeline_type"
    with pytest.raises(BadRequest) as error_info:
        provision_model_card(event, patched_session)
    assert (
        str(error_info.value)
        == "pipeline_type must be on of create_model_card|update_model_card|describe_model_card|delete_model_card|export_model_card"
    )


def test_get_required_keys(
    api_byom_event,  # NOSONAR:S107 this test function is designed to take many fixtures
    api_data_quality_event,
    api_model_quality_event,
    required_api_byom_realtime_builtin,
    required_api_byom_batch_builtin,
    required_api_byom_realtime_custom,
    required_api_byom_batch_custom,
    required_api_keys_model_monitor,
    required_api_image_builder,
):
    # Required keys in byom, realtime, builtin
    returned_keys = get_required_keys("byom_realtime_builtin", "No")
    expected_keys = required_api_byom_realtime_builtin("No")
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in byom, batch, builtin
    returned_keys = get_required_keys("byom_batch_builtin", "No")
    expected_keys = required_api_byom_batch_builtin
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in byom, realtime, custom
    returned_keys = get_required_keys("byom_realtime_custom", "No")
    expected_keys = required_api_byom_realtime_custom
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in byom, batch, custom
    returned_keys = get_required_keys("byom_batch_custom", "No")
    expected_keys = required_api_byom_batch_custom
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in data quality monitor
    returned_keys = get_required_keys("byom_data_quality_monitor", "No")
    expected_keys = required_api_keys_model_monitor("DataQuality")
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in model quality monitor, problem type Regression
    returned_keys = get_required_keys("byom_model_quality_monitor", "No", "Regression")
    expected_keys = required_api_keys_model_monitor("ModelQuality", "Regression")
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in model quality monitor, problem type BinaryClassification
    returned_keys = get_required_keys(
        "byom_model_quality_monitor", "No", "BinaryClassification"
    )
    expected_keys = required_api_keys_model_monitor(
        "ModelQuality", "BinaryClassification"
    )
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in model bias monitor, problem type BinaryClassification
    returned_keys = get_required_keys(
        "byom_model_bias_monitor", "No", "BinaryClassification"
    )
    expected_keys = required_api_keys_model_monitor("ModelBias", "BinaryClassification")
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # Required keys in model expainability monitor, problem type Regression
    returned_keys = get_required_keys(
        "byom_model_explainability_monitor", "No", "Regression"
    )
    expected_keys = required_api_keys_model_monitor("ModelExplainability", "Regression")
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # test exception for unsupported problem type
    with pytest.raises(BadRequest) as error:
        get_required_keys("byom_model_quality_monitor", "No", "UnsupportedProblemType")
    assert (
        str(error.value)
        == "Bad request format. Unsupported problem_type in byom_model_quality_monitor pipeline"
    )
    # Required keys in image builder
    returned_keys = get_required_keys("byom_image_builder", "No")
    expected_keys = required_api_image_builder
    TestCase().assertCountEqual(expected_keys, returned_keys)
    # assert for exceptions
    with pytest.raises(BadRequest) as exceinfo:
        get_required_keys("not_supported", "No")
    assert (
        str(exceinfo.value)
        == "Bad request format. Pipeline type not supported. Check documentation for API & config formats"
    )
    # Test with model registry used
    returned_keys = get_required_keys("byom_realtime_builtin", "Yes")
    expected_keys = required_api_byom_realtime_builtin("Yes")
    TestCase().assertCountEqual(expected_keys, returned_keys)


def test_get_stage_param(api_byom_event):
    single_event = api_byom_event("byom_realtime_custom", False)
    TestCase().assertEqual(
        get_stage_param(single_event, "data_capture_location", "None"),
        "bucket/datacapture",
    )
    multi_event = api_byom_event("byom_realtime_custom", True)
    TestCase().assertEqual(
        get_stage_param(multi_event, "data_capture_location", "dev"),
        "bucket/dev_datacapture",
    )


def test_get_template_parameters(
    api_byom_event,  # NOSONAR:S107 this function is designed to take many arguments
    api_image_builder_event,
    api_data_quality_event,
    api_model_quality_event,
    api_model_bias_event,
    api_model_explainability_event,
    expected_params_realtime_custom,
    expected_image_builder_params,
    expected_batch_params,
    expected_data_quality_monitor_params,
    expected_model_quality_monitor_params,
    expected_model_bias_monitor_params,
    expected_model_explainability_monitor_params,
    api_training_event,
):
    single_event = api_byom_event("byom_realtime_custom", False)
    # realtime pipeline
    TestCase().assertEqual(
        get_template_parameters(single_event, False), expected_params_realtime_custom()
    )
    # image builder pipeline
    TestCase().assertEqual(
        get_template_parameters(api_image_builder_event, False),
        expected_image_builder_params,
    )
    # batch pipeline
    TestCase().assertEqual(
        get_template_parameters(api_byom_event("byom_batch_custom", False), False),
        expected_batch_params,
    )

    # additional params used by Model Monitor asserts
    common_params = [
        ("AssetsBucket", "testassetsbucket"),
        ("KmsKeyArn", ""),
        ("BlueprintBucket", "testbucket"),
    ]
    # data quality pipeline
    assert len(get_template_parameters(api_data_quality_event, False)) == len(
        [
            *expected_data_quality_monitor_params,
            *common_params,
        ]
    )

    # model quality pipeline
    assert len(get_template_parameters(api_model_quality_event, False)) == len(
        [
            *expected_model_quality_monitor_params,
            *common_params,
        ]
    )

    # model bias pipeline
    assert len(get_template_parameters(api_model_bias_event, False)) == len(
        [
            *expected_model_bias_monitor_params,
            *common_params,
        ]
    )

    # model explainability pipeline
    assert len(get_template_parameters(api_model_explainability_event, False)) == len(
        [
            *expected_model_explainability_monitor_params,
            *common_params,
        ]
    )

    # autopilot templeate params single account
    assert (
        len(
            get_template_parameters(
                api_training_event("model_autopilot_training"), False
            )
        )
        == 16
    )

    # autopilot templeate params multi account
    assert (
        len(
            get_template_parameters(
                api_training_event("model_autopilot_training"), True
            )
        )
        == 16
    )

    with patch("lambda_helpers.sagemaker.image_uris.retrieve") as patched_uri:
        patched_uri.return_value = "algo-image"
        # training pipeline params
        assert (
            len(
                get_template_parameters(
                    api_training_event("model_training_builtin"), True
                )
            )
            == 24
        )

        # hyperparameter tuning
        assert (
            len(
                get_template_parameters(api_training_event("model_tuner_builtin"), True)
            )
            == 26
        )

    # test for exception
    with pytest.raises(BadRequest):
        get_template_parameters({"pipeline_type": "unsupported"}, False)


def test_get_common_realtime_batch_params(
    api_byom_event, expected_common_realtime_batch_params
):
    realtime_event = api_byom_event("byom_realtime_custom", False)
    batch_event = api_byom_event("byom_batch_custom", False)
    realtime_event.update(batch_event)
    TestCase().assertEqual(
        get_common_realtime_batch_params(realtime_event, "us-east-1", "None"),
        expected_common_realtime_batch_params,
    )


def test_get_realtime_specific_params(
    api_byom_event, expected_realtime_specific_params
):
    # test with endpoint_name not provided
    realtime_event = api_byom_event("byom_realtime_builtin", False)
    TestCase().assertEqual(
        get_realtime_specific_params(realtime_event, "None"),
        expected_realtime_specific_params(),
    )
    # test with endpoint_name provided
    realtime_event = api_byom_event("byom_realtime_builtin", False, True)
    TestCase().assertEqual(
        get_realtime_specific_params(realtime_event, "None"),
        expected_realtime_specific_params(True),
    )
    # test with endpoint_name provided for multi-account
    realtime_event = api_byom_event("byom_realtime_builtin", False, True)
    TestCase().assertEqual(
        get_realtime_specific_params(realtime_event, "dev"),
        expected_realtime_specific_params(True),
    )


def test_get_batch_specific_params(api_byom_event, expected_batch_specific_params):
    batch_event = api_byom_event("byom_batch_custom", False)
    TestCase().assertEqual(
        get_batch_specific_params(batch_event, "None"), expected_batch_specific_params
    )


def test_get_built_in_model_monitor_container_uri():
    # The 156813124566 is one of the actual account ids for a public Model Monitor Image provided
    # by the SageMaker service. The reason is I need to provide a valid image URI because the SDK
    # has validation for the inputs
    # assert the returned value by an actual Model Monitor Image URI for the region.
    assert (
        get_built_in_model_monitor_image_uri("us-east-1", "model-monitor")
        == "156813124566.dkr.ecr.us-east-1.amazonaws.com/sagemaker-model-monitor-analyzer"
    )
    # The 205585389593 is one of the actual account ids for a public Clarify image provided
    # by the SageMaker service.
    # assert the returned value by an actual clarify Image URI for the region.
    assert (
        get_built_in_model_monitor_image_uri("us-east-1", "clarify")
        == "205585389593.dkr.ecr.us-east-1.amazonaws.com/sagemaker-clarify-processing:1.0"
    )


@patch("lambda_helpers.sagemaker.image_uris.retrieve")
def test_get_model_monitor_params(
    mocked_image_retrieve,
    api_data_quality_event,
    api_model_quality_event,
    expected_data_quality_monitor_params,
    expected_model_quality_monitor_params,
):
    # The 156813124566 is one of the actual account ids for a public Model Monitor Image provided
    # by the SageMaker service. The reason is I need to provide a valid image URI because the SDK
    # has validation for the inputs
    mocked_image_retrieve.return_value = (
        "156813124566.dkr.ecr.us-east-1.amazonaws.com/sagemaker-model-monitor-analyzer"
    )
    # data quality monitor
    TestCase().assertEqual(
        len(get_model_monitor_params(api_data_quality_event, "us-east-1", "None")),
        len(expected_data_quality_monitor_params),
    )
    # model quality monitor
    TestCase().assertEqual(
        len(
            get_model_monitor_params(
                api_model_quality_event,
                "us-east-1",
                "None",
                monitoring_type="ModelQuality",
            )
        ),
        len(expected_model_quality_monitor_params),
    )


def test_get_image_builder_params(
    api_image_builder_event, expected_image_builder_params
):
    TestCase().assertEqual(
        get_image_builder_params(api_image_builder_event), expected_image_builder_params
    )


def test_format_template_parameters(
    expected_image_builder_params,
    expected_multi_account_params_format,
    expect_single_account_params_format,
):
    TestCase().assertEqual(
        format_template_parameters(expected_image_builder_params, "True"),
        expected_multi_account_params_format,
    )
    TestCase().assertEqual(
        format_template_parameters(expected_image_builder_params, "False"),
        expect_single_account_params_format,
    )


@patch("lambda_helpers.sagemaker.image_uris.retrieve")
def test_get_image_uri(mocked_sm, api_byom_event):
    custom_event = api_byom_event("byom_realtime_custom", False)
    TestCase().assertEqual(
        get_image_uri("byom_realtime_custom", custom_event, "us-east-1"),
        "custom-image-uri",
    )
    mocked_sm.return_value = "test-image-uri"
    builtin_event = api_byom_event("byom_realtime_builtin", False)
    TestCase().assertEqual(
        get_image_uri("byom_realtime_builtin", builtin_event, "us-east-1"),
        "test-image-uri",
    )
    mocked_sm.assert_called_with(
        framework=builtin_event.get("model_framework"),
        region="us-east-1",
        version=builtin_event.get("model_framework_version"),
    )
    # assert exception for an unsupported pipeline
    with pytest.raises(Exception) as exc:
        get_image_uri("not_spoorted_pipeline", builtin_event, "us-east-1")
    assert str(exc.value) == "Unsupported pipeline by get_image_uri function"


@patch("lambda_helpers.sagemaker.image_uris.retrieve")
@patch("boto3.client")
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
    mocked_write,
    mocked_shutil,
    mocked_client,
    mocked_get_image,
    api_image_builder_event,
):
    mocked_path.return_value = False
    s3_client = boto3.client("s3", region_name="us-east-1")
    # multi account
    create_template_zip_file(
        api_image_builder_event,
        "blueprint",
        "assets_bucket",
        "byom/template.yaml",
        "zipfile",
        "True",
        s3_client,
    )
    # single account
    create_template_zip_file(
        api_image_builder_event,
        "blueprint",
        "assets_bucket",
        "byom/template.yaml",
        "zipfile",
        "False",
        s3_client,
    )


def test_get_codepipeline_params():
    common_params = [
        ("NotificationsSNSTopicArn", os.environ["MLOPS_NOTIFICATIONS_SNS_TOPIC"]),
        ("TemplateZipFileName", "template_zip_name"),
        ("TemplateFileName", "template_file_name"),
        ("AssetsBucket", "testassetsbucket"),
        ("StackName", "stack_name"),
    ]
    # multi account codepipeline
    TestCase().assertEqual(
        get_codepipeline_params(
            "True",
            "byom_realtime_builtin",
            "stack_name",
            "template_zip_name",
            "template_file_name",
        ),
        common_params
        + [
            ("DevParamsName", "dev_template_params.json"),
            ("StagingParamsName", "staging_template_params.json"),
            ("ProdParamsName", "prod_template_params.json"),
            ("DevAccountId", "dev_account_id"),
            ("DevOrgId", "dev_org_id"),
            ("StagingAccountId", "staging_account_id"),
            ("StagingOrgId", "staging_org_id"),
            ("ProdAccountId", "prod_account_id"),
            ("ProdOrgId", "prod_org_id"),
            ("BlueprintBucket", "testbucket"),
            ("DelegatedAdminAccount", "No"),
        ],
    )

    # test training pipeline with multi-account
    TestCase().assertEqual(
        get_codepipeline_params(
            "True",
            "model_training_builtin",
            "stack_name",
            "template_zip_name",
            "template_file_name",
        ),
        common_params + [("TemplateParamsName", "template_params.json")],
    )

    # single account codepipeline
    TestCase().assertEqual(
        get_codepipeline_params(
            "False",
            "byom_realtime_builtin",
            "stack_name",
            "template_zip_name",
            "template_file_name",
        ),
        common_params + [("TemplateParamsName", "template_params.json")],
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
    assert (
        str(execinfo.value)
        == "Bad request. API body does not have the necessary parameter: model_artifact_location"
    )
