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
import datetime
from unittest.mock import MagicMock, patch
import botocore.session
from botocore.stub import Stubber, ANY
from pipeline_orchestration.index import (
    handler,
    provision_pipeline,
    pipeline_status,
    DateTimeEncoder,
)

mock_env_variables = {
    "NOTIFICATION_EMAIL": "test@example.com",
    "BLUEPRINT_BUCKET": "testbucket",
    "BLUEPRINT_BUCKET_URL": "testurl",
    "ACCESS_BUCKET": "testaccessbucket",
    "PIPELINE_STACK_NAME": "teststack",
    "CFN_ROLE_ARN": "arn:aws:role:region:account:action",
}


def test_handler():
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
                {"message": "Bad request format. Expected httpMethod or pipeline_type, recevied none. Check documentation for API & config formats."}
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


@patch.dict(os.environ, mock_env_variables)
def test_provision_pipeline():

    client = botocore.session.get_session().create_client("cloudformation")
    cp_client = botocore.session.get_session().create_client("codepipeline")

    stubber = Stubber(client)
    cp_stubber = Stubber(cp_client)
    cfn_response = {"StackId": "1234"}
    expected_params = {
        "Capabilities": ["CAPABILITY_IAM"],
        "OnFailure": "DO_NOTHING",
        "Parameters": [
            {
                "ParameterKey": "NOTIFICATIONEMAIL",
                "ParameterValue": "test@example.com",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "BLUEPRINTBUCKET",
                "ParameterValue": "testbucket",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "ACCESSBUCKET",
                "ParameterValue": "testaccessbucket",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "CUSTOMCONTAINER",
                "ParameterValue": "",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "MODELFRAMEWORK",
                "ParameterValue": "xgboost",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "MODELFRAMEWORKVERSION",
                "ParameterValue": "1.0-1",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "MODELNAME",
                "ParameterValue": "testmodel",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "MODELARTIFACTLOCATION",
                "ParameterValue": "model.tar.gz",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "TRAININGDATA",
                "ParameterValue": "training/data.csv",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "INFERENCEINSTANCE",
                "ParameterValue": "ml.m5.large",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "INFERENCETYPE",
                "ParameterValue": "realtime",
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "BATCHINFERENCEDATA",
                "ParameterValue": "inference/data.csv",
                "UsePreviousValue": True,
            },
        ],
        "RoleARN": "arn:aws:role:region:account:action",
        "StackName": "teststack-testmodel",
        "Tags": [{"Key": "purpose", "Value": "test"}],
        "TemplateURL": "https://testurl/blueprints/byom/byom_realtime_builtin_container.yaml",
    }
    expected_response = {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": json.dumps(
            {"message": "success: stack creation started", "pipeline_id": "1234"}
        ),
        "headers": {"Content-Type": "plain/text"},
    }
    event = {
        "pipeline_type": "byom",
        "custom_model_container": "",
        "model_framework": "xgboost",
        "model_framework_version": "1.0-1",
        "model_name": "testmodel",
        "model_artifact_location": "model.tar.gz",
        "training_data": "training/data.csv",
        "inference_instance": "ml.m5.large",
        "inference_type": "realtime",
        "batch_inference_data": "inference/data.csv",
    }
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
            response = pipeline_status(
                event, cfn_client=cfn_client, cp_client=cp_client
            )
            assert response == expected_response
