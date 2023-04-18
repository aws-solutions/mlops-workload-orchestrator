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
import json
import pytest


@pytest.fixture()
def stackset_name():
    return "mlops-stackset"


@pytest.fixture()
def mocked_org_ids():
    return ["ou-x9x7-xxx1xxx3"]


@pytest.fixture()
def mocked_account_ids():
    return ["Test_Account_Id"]


@pytest.fixture()
def mocked_regions():
    return ["us-east-1"]


@pytest.fixture()
def mocked_job_id():
    return "mocked_job_id"


@pytest.fixture()
def mocked_cp_success_message():
    return "StackSet Job SUCCEEDED"


@pytest.fixture()
def mocked_cp_failure_message():
    return "StackSet Job Failed"

@pytest.fixture()
def mocked_describe_response():
    return {'StackInstance':{"StackInstanceStatus": {"DetailedStatus": "SUCCEEDED"}}}

@pytest.fixture()
def mocked_cp_continuation_message():
    return "StackSet Job is continued"


@pytest.fixture()
def required_user_params():
    return [
        "stackset_name",
        "artifact",
        "template_file",
        "stage_params_file",
        "account_ids",
        "org_ids",
        "regions",
    ]


@pytest.fixture()
def mocked_decoded_parameters():
    return {
        "stackset_name": "model2",
        "artifact": "SourceArtifact",
        "template_file": "template.yaml",
        "stage_params_file": "staging-config-test.json",
        "account_ids": ["mocked_account_id"],
        "org_ids": ["mocked_org_unit_id"],
        "regions": ["us-east-1"],
    }


@pytest.fixture()
def mocked_codepipeline_event(mocked_decoded_parameters):
    return {
        "CodePipeline.job": {
            "id": "11111111-abcd-1111-abcd-111111abcdef",
            "accountId": "test-account-id",
            "data": {
                "actionConfiguration": {
                    "configuration": {
                        "FunctionName": "stacketset-lambda",
                        "UserParameters": json.dumps(mocked_decoded_parameters),
                    }
                },
                "inputArtifacts": [
                    {
                        "location": {
                            "s3Location": {
                                "bucketName": "test-bucket",
                                "objectKey": "template.zip",
                            },
                            "type": "S3",
                        },
                        "revision": None,
                        "name": "SourceArtifact",
                    }
                ],
                "outputArtifacts": [],
                "artifactCredentials": {
                    "secretAccessKey": "test-secretkey",
                    "sessionToken": "test-tockedn",
                    "accessKeyId": "test-accesskey",
                },
            },
        }
    }


@pytest.fixture()
def mocked_invalid_user_parms(mocked_decoded_parameters):
    return {
        "CodePipeline.job": {
            "id": "11111111-abcd-1111-abcd-111111abcdef",
            "accountId": "test-account-id",
            "data": {
                "actionConfiguration": {
                    "configuration": {
                        "FunctionName": "stacketset-lambda",
                        "UserParameters": mocked_decoded_parameters,
                    }
                }
            },
        }
    }


@pytest.fixture()
def mocked_template_parameters():
    return json.dumps(
        [
            {"ParameterKey": "TagDescription", "ParameterValue": "StackSetValue"},
            {"ParameterKey": "TagName", "ParameterValue": "StackSetValue2"},
        ]
    )


@pytest.fixture()
def mocked_template():
    template = """---
  AWSTemplateFormatVersion: 2010-09-09
Description: Stack1 with yaml template
Parameters:
  TagDescription:
    Type: String
  TagName:
    Type: String
Resources:
  EC2Instance1:
    Type: AWS::EC2::Instance
    Properties:
      ImageId: ami-03cf127a
      KeyName: dummy
      InstanceType: t2.micro
      Tags:
        - Key: Description
          Value:
            Ref: TagDescription
        - Key: Name
          Value: !Ref TagName
  """
    return template


@pytest.fixture(scope="function")
def mocked_stackset(cf_client, stackset_name, mocked_template_parameters):
    cf_client.create_stack_set(
        StackSetName=stackset_name,
        TemplateBody=stackset_name,
        Parameters=mocked_template_parameters,
    )
