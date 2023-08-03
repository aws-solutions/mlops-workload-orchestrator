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
import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
from lib.mlops_orchestrator_stack import MLOpsStack
from lib.blueprints.aspects.aws_sdk_config_aspect import AwsSDKConfigAspect
from lib.blueprints.aspects.protobuf_config_aspect import ProtobufConfigAspect
from lib.blueprints.aspects.app_registry_aspect import AppRegistry
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from test.context_helper import get_cdk_context


class TestAspects:
    """Tests for cdk aspects"""

    def setup_class(self):
        """Tests setup"""
        app = cdk.App(context=get_cdk_context("././cdk.json")["context"])

        solution_id = get_cdk_context_value(app, "SolutionId")
        version = get_cdk_context_value(app, "Version")
        solution_name = get_cdk_context_value(app, "SolutionName")
        app_registry_name = get_cdk_context_value(app, "AppRegistryName")
        application_type = get_cdk_context_value(app, "ApplicationType")

        # create single account stack
        single_mlops_stack = MLOpsStack(
            app,
            "mlops-workload-orchestrator-single-account",
            description=f"({solution_id}-sa) - MLOps Workload Orchestrator (Single Account Option). Version {version}",
            multi_account=False,
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # add app registry to single account stack

        cdk.Aspects.of(single_mlops_stack).add(
            AppRegistry(
                single_mlops_stack,
                "AppRegistrySingleAccount",
                solution_id=solution_id,
                solution_name=solution_name,
                solution_version=version,
                app_registry_name=app_registry_name,
                application_type=application_type,
            )
        )

        # add AWS_SDK_USER_AGENT env variable to Lambda functions
        cdk.Aspects.of(single_mlops_stack).add(
            AwsSDKConfigAspect(app, "SDKUserAgentSingle", solution_id, version)
        )

        # add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
        cdk.Aspects.of(single_mlops_stack).add(
            ProtobufConfigAspect(app, "ProtobufConfigSingle")
        )

        # create template
        self.template = Template.from_stack(single_mlops_stack)

    def test_app_registry_aspect(self):
        self.template.has_resource_properties(
            "AWS::ServiceCatalogAppRegistry::Application",
            {
                "Name": {
                    "Fn::Join": [
                        "-",
                        ["App", {"Ref": "AWS::StackName"}, "mlops"],
                    ]
                },
                "Description": "Service Catalog application to track and manage all your resources for the solution %%SOLUTION_NAME%%",
                "Tags": {
                    "Solutions:ApplicationType": "AWS-Solutions",
                    "Solutions:SolutionID": "SO0136",
                    "Solutions:SolutionName": "%%SOLUTION_NAME%%",
                    "Solutions:SolutionVersion": "%%VERSION%%",
                },
            },
        )

        self.template.has_resource_properties(
            "AWS::ServiceCatalogAppRegistry::ResourceAssociation",
            {
                "Application": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp(
                            "AppRegistrySingleAccountRegistrySetup*"
                        ),
                        "Id",
                    ]
                },
                "Resource": {"Ref": "AWS::StackId"},
                "ResourceType": "CFN_STACK",
            },
        )

        self.template.has_resource_properties(
            "AWS::ServiceCatalogAppRegistry::AttributeGroupAssociation",
            {
                "Application": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp(
                            "AppRegistrySingleAccountRegistrySetup*"
                        ),
                        "Id",
                    ]
                },
                "AttributeGroup": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp(
                            "AppRegistrySingleAccountAppAttributes*"
                        ),
                        "Id",
                    ]
                },
            },
        )

        self.template.has_resource_properties(
            "AWS::ServiceCatalogAppRegistry::AttributeGroup",
            {
                "Attributes": {
                    "applicationType": "AWS-Solutions",
                    "version": "%%VERSION%%",
                    "solutionID": "SO0136",
                    "solutionName": "%%SOLUTION_NAME%%",
                },
                "Name": {"Fn::Join": ["", ["AttrGrp-", {"Ref": "AWS::StackName"}]]},
                "Description": "Attributes for Solutions Metadata",
            },
        )

    def test_aws_sdk_config_aspect(self):
        self.template.all_resources_properties(
            "AWS::Lambda::Function",
            {
                "Environment": {
                    "Variables": {
                        "AWS_SDK_USER_AGENT": '{"user_agent_extra": "AwsSolution/SO0136/%%VERSION%%"}',
                    }
                }
            },
        )

    def test_aws_protocol_buffers_aspect(self):
        self.template.all_resources_properties(
            "AWS::Lambda::Function",
            {
                "Environment": {
                    "Variables": {
                        "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION": "python",
                    }
                }
            },
        )
