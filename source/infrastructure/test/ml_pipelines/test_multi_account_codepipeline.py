# #####################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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
from lib.blueprints.ml_pipelines.multi_account_codepipeline import (
    MultiAccountCodePipelineStack,
)
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from test.context_helper import get_cdk_context


class TestMultiAccountCodePipelineStack:
    """Tests for multi_account_codepipeline stack"""

    def setup_class(self):
        """Tests setup"""
        self.app = cdk.App(context=get_cdk_context("././cdk.json")["context"])

        solution_id = get_cdk_context_value(self.app, "SolutionId")
        version = get_cdk_context_value(self.app, "Version")

        multi_codepipeline = MultiAccountCodePipelineStack(
            self.app,
            "MultiAccountCodePipelineStack",
            description=(
                f"({solution_id}byom-mac) - Multi-account codepipeline. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # create template
        self.template = Template.from_stack(multi_codepipeline)

    def test_template_parameters(self):
        """Tests for templates parameters"""
        self.template.has_parameter(
            "TemplateZipFileName",
            {
                "Type": "String",
                "AllowedPattern": "^.*\\.zip$",
                "Description": "The zip file's name containing the CloudFormation template and its parameters files",
            },
        )

        self.template.has_parameter(
            "TemplateFileName",
            {
                "Type": "String",
                "AllowedPattern": "^.*\\.yaml$",
                "Description": "CloudFormation template's file name",
            },
        )

        self.template.has_parameter(
            "DevParamsName",
            {
                "Type": "String",
                "AllowedPattern": "^.*\\.json$",
                "Description": "parameters json file's name for the development stage",
            },
        )

        self.template.has_parameter(
            "StagingParamsName",
            {
                "Type": "String",
                "AllowedPattern": "^.*\\.json$",
                "Description": "parameters json file's name for the staging stage",
            },
        )

        self.template.has_parameter(
            "ProdParamsName",
            {
                "Type": "String",
                "AllowedPattern": "^.*\\.json$",
                "Description": "parameters json file's name for the production stage",
            },
        )

        self.template.has_parameter(
            "NotificationsSNSTopicArn",
            {
                "Type": "String",
                "AllowedPattern": "^arn:\\S+:sns:\\S+:\\d{12}:\\S+$",
                "Description": "AWS SNS Topics arn used by the MLOps Workload Orchestrator to notify the administrator.",
            },
        )

        self.template.has_parameter(
            "DevAccountId",
            {
                "Type": "String",
                "AllowedPattern": "^\\d{12}$",
                "Description": "AWS development account number where the CF template will be deployed",
            },
        )

        self.template.has_parameter(
            "DevOrgId",
            {
                "Type": "String",
                "AllowedPattern": "^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$",
                "Description": "AWS development organizational unit id where the CF template will be deployed",
            },
        )

        self.template.has_parameter(
            "StagingAccountId",
            {
                "Type": "String",
                "AllowedPattern": "^\\d{12}$",
                "Description": "AWS staging account number where the CF template will be deployed",
            },
        )

        self.template.has_parameter(
            "StagingOrgId",
            {
                "Type": "String",
                "AllowedPattern": "^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$",
                "Description": "AWS staging organizational unit id where the CF template will be deployed",
            },
        )

        self.template.has_parameter(
            "ProdAccountId",
            {
                "Type": "String",
                "AllowedPattern": "^\\d{12}$",
                "Description": "AWS production account number where the CF template will be deployed",
            },
        )

        self.template.has_parameter(
            "ProdOrgId",
            {
                "Type": "String",
                "AllowedPattern": "^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$",
                "Description": "AWS production organizational unit id where the CF template will be deployed",
            },
        )

        self.template.has_parameter(
            "BlueprintBucket",
            {
                "Type": "String",
                "Description": "Bucket name for blueprints of different types of ML Pipelines.",
                "MinLength": 3,
            },
        )

        self.template.has_parameter(
            "AssetsBucket",
            {
                "Type": "String",
                "Description": "Bucket name where the model and baselines data are stored.",
                "MinLength": 3,
            },
        )

        self.template.has_parameter(
            "StackName",
            {
                "Type": "String",
                "Description": "The name to assign to the deployed CF stack.",
                "MinLength": 1,
            },
        )

        self.template.has_parameter(
            "DelegatedAdminAccount",
            {
                "Type": "String",
                "Default": "Yes",
                "AllowedValues": ["Yes", "No"],
                "Description": "Is a delegated administrator account used to deploy across account",
            },
        )

    def test_template_conditions(self):
        """Tests for templates conditions"""
        self.template.has_condition(
            "UseDelegatedAdmin",
            {"Fn::Equals": [{"Ref": "DelegatedAdminAccount"}, "Yes"]},
        )

    def test_all_s3_buckets_properties(self):
        """Tests for S3 buckets properties"""
        self.template.resource_count_is("AWS::S3::Bucket", 1)
        # assert for all bucket, encryption is enabled and Public Access is Blocked
        self.template.all_resources_properties(
            "AWS::S3::Bucket",
            {
                "BucketEncryption": {
                    "ServerSideEncryptionConfiguration": [
                        {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "aws:kms"}}
                    ]
                },
                "PublicAccessBlockConfiguration": Match.object_equals(
                    {
                        "BlockPublicAcls": True,
                        "BlockPublicPolicy": True,
                        "IgnorePublicAcls": True,
                        "RestrictPublicBuckets": True,
                    }
                ),
            },
        )

    def test_all_s3_buckets_policy(self):
        """Tests for S3 buckets policies"""
        # we have 1 S3 bucket, so we should have 1 bucket policies
        self.template.resource_count_is("AWS::S3::BucketPolicy", 1)
        # assert all buckets have bucket policy to enforce SecureTransport
        self.template.all_resources_properties(
            "AWS::S3::BucketPolicy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            {
                                "Action": "s3:*",
                                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                                "Effect": "Deny",
                                "Principal": {"AWS": "*"},
                                "Resource": [
                                    {
                                        "Fn::GetAtt": [
                                            Match.string_like_regexp(
                                                "MultiAccountPipelineArtifactsBucket*"
                                            ),
                                            "Arn",
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                {
                                                    "Fn::GetAtt": [
                                                        Match.string_like_regexp(
                                                            "MultiAccountPipelineArtifactsBucket*"
                                                        ),
                                                        "Arn",
                                                    ]
                                                },
                                                "/*",
                                            ],
                                        ]
                                    },
                                ],
                            }
                        ]
                    ),
                    "Version": "2012-10-17",
                }
            },
        )

    def test_iam_policies(self):
        """Tests for IAM policies"""
        # assert Policy for pipeline S3 source
        self.template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": ["s3:GetObject*", "s3:GetBucket*", "s3:List*"],
                            "Effect": "Allow",
                            "Resource": [
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":s3:::",
                                            {"Ref": "AssetsBucket"},
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":s3:::",
                                            {"Ref": "AssetsBucket"},
                                            "/",
                                            {"Ref": "TemplateZipFileName"},
                                        ],
                                    ]
                                },
                            ],
                        },
                        {
                            "Action": [
                                "s3:DeleteObject*",
                                "s3:PutObject",
                                "s3:PutObjectLegalHold",
                                "s3:PutObjectRetention",
                                "s3:PutObjectTagging",
                                "s3:PutObjectVersionTagging",
                                "s3:Abort*",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "MultiAccountPipelineArtifactsBucket*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            {
                                                "Fn::GetAtt": [
                                                    Match.string_like_regexp(
                                                        "MultiAccountPipelineArtifactsBucket*"
                                                    ),
                                                    "Arn",
                                                ]
                                            },
                                            "/*",
                                        ],
                                    ]
                                },
                            ],
                        },
                    ],
                    "Version": "2012-10-17",
                },
                "PolicyName": Match.string_like_regexp(
                    "MultiAccountPipelineSourceS3SourceCodePipelineActionRoleDefaultPolicy*"
                ),
                "Roles": [
                    {
                        "Ref": Match.string_like_regexp(
                            "MultiAccountPipelineSourceS3SourceCodePipelineActionRole*"
                        )
                    }
                ],
            },
        )

    def test_iam_policies(self):
        """Tests for IAM policies"""
        # assert Policy for pipeline S3 source
        self.template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": ["s3:GetObject*", "s3:GetBucket*", "s3:List*"],
                            "Effect": "Allow",
                            "Resource": [
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":s3:::",
                                            {"Ref": "AssetsBucket"},
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":s3:::",
                                            {"Ref": "AssetsBucket"},
                                            "/",
                                            {"Ref": "TemplateZipFileName"},
                                        ],
                                    ]
                                },
                            ],
                        },
                        {
                            "Action": [
                                "s3:DeleteObject*",
                                "s3:PutObject",
                                "s3:PutObjectLegalHold",
                                "s3:PutObjectRetention",
                                "s3:PutObjectTagging",
                                "s3:PutObjectVersionTagging",
                                "s3:Abort*",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "MultiAccountPipelineArtifactsBucket*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            {
                                                "Fn::GetAtt": [
                                                    Match.string_like_regexp(
                                                        "MultiAccountPipelineArtifactsBucket*"
                                                    ),
                                                    "Arn",
                                                ]
                                            },
                                            "/*",
                                        ],
                                    ]
                                },
                            ],
                        },
                    ],
                    "Version": "2012-10-17",
                },
                "PolicyName": Match.string_like_regexp(
                    "MultiAccountPipelineSourceS3SourceCodePipelineActionRoleDefaultPolicy*"
                ),
                "Roles": [
                    {
                        "Ref": Match.string_like_regexp(
                            "MultiAccountPipelineSourceS3SourceCodePipelineActionRole*"
                        )
                    }
                ],
            },
        )

    def test_codepipeline(self):
        """Tests for CodePipeline"""
        # assert there is one codepipeline
        self.template.resource_count_is("AWS::CodePipeline::Pipeline", 1)

        # assert properties
        self.template.has_resource_properties(
            "AWS::CodePipeline::Pipeline",
            {
                "RoleArn": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("MultiAccountPipelineRole*"),
                        "Arn",
                    ]
                },
                "Stages": [
                    {
                        "Actions": [
                            {
                                "ActionTypeId": {
                                    "Category": "Source",
                                    "Owner": "AWS",
                                    "Provider": "S3",
                                    "Version": "1",
                                },
                                "Configuration": {
                                    "S3Bucket": {"Ref": "AssetsBucket"},
                                    "S3ObjectKey": {"Ref": "TemplateZipFileName"},
                                },
                                "Name": "S3Source",
                                "OutputArtifacts": [
                                    {"Name": "Artifact_Source_S3Source"}
                                ],
                                "RoleArn": {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "MultiAccountPipelineSourceS3SourceCodePipelineActionRole*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                "RunOrder": 1,
                            }
                        ],
                        "Name": "Source",
                    },
                    {
                        "Actions": [
                            {
                                "ActionTypeId": {
                                    "Category": "Invoke",
                                    "Owner": "AWS",
                                    "Provider": "Lambda",
                                    "Version": "1",
                                },
                                "Configuration": {
                                    "FunctionName": {
                                        "Ref": Match.string_like_regexp(
                                            "DeployDevStackSetstacksetlambda*"
                                        )
                                    },
                                    "UserParameters": {
                                        "Fn::Join": [
                                            "",
                                            [
                                                '{"stackset_name":"',
                                                {"Ref": "StackName"},
                                                "-dev-",
                                                {
                                                    "Fn::Select": [
                                                        0,
                                                        {
                                                            "Fn::Split": [
                                                                "-",
                                                                {
                                                                    "Fn::Select": [
                                                                        2,
                                                                        {
                                                                            "Fn::Split": [
                                                                                "/",
                                                                                {
                                                                                    "Ref": "AWS::StackId"
                                                                                },
                                                                            ]
                                                                        },
                                                                    ]
                                                                },
                                                            ]
                                                        },
                                                    ]
                                                },
                                                '","artifact":"Artifact_Source_S3Source","template_file":"',
                                                {"Ref": "TemplateFileName"},
                                                '","stage_params_file":"',
                                                {"Ref": "DevParamsName"},
                                                '","account_ids":["',
                                                {"Ref": "DevAccountId"},
                                                '"],"org_ids":["',
                                                {"Ref": "DevOrgId"},
                                                '"],"regions":["',
                                                {"Ref": "AWS::Region"},
                                                '"]}',
                                            ],
                                        ]
                                    },
                                },
                                "InputArtifacts": [
                                    {"Name": "Artifact_Source_S3Source"}
                                ],
                                "Name": "DeployDevStackSet",
                                "Namespace": "DeployDevStackSet-namespace",
                                "RoleArn": {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "MultiAccountPipelineDeployDevDeployDevStackSetCodePipelineActionRole*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                "RunOrder": 1,
                            },
                            {
                                "ActionTypeId": {
                                    "Category": "Approval",
                                    "Owner": "AWS",
                                    "Provider": "Manual",
                                    "Version": "1",
                                },
                                "Configuration": {
                                    "NotificationArn": {
                                        "Ref": "NotificationsSNSTopicArn"
                                    },
                                    "CustomData": "Please approve to deploy to staging account",
                                },
                                "Name": "DeployStaging",
                                "RoleArn": {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "MultiAccountPipelineDeployDevDeployStagingCodePipelineActionRole*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                "RunOrder": 2,
                            },
                        ],
                        "Name": "DeployDev",
                    },
                    {
                        "Actions": [
                            {
                                "ActionTypeId": {
                                    "Category": "Invoke",
                                    "Owner": "AWS",
                                    "Provider": "Lambda",
                                    "Version": "1",
                                },
                                "Configuration": {
                                    "FunctionName": {
                                        "Ref": Match.string_like_regexp(
                                            "DeployStagingStackSetstacksetlambda*"
                                        )
                                    },
                                    "UserParameters": {
                                        "Fn::Join": [
                                            "",
                                            [
                                                '{"stackset_name":"',
                                                {"Ref": "StackName"},
                                                "-staging-",
                                                {
                                                    "Fn::Select": [
                                                        0,
                                                        {
                                                            "Fn::Split": [
                                                                "-",
                                                                {
                                                                    "Fn::Select": [
                                                                        2,
                                                                        {
                                                                            "Fn::Split": [
                                                                                "/",
                                                                                {
                                                                                    "Ref": "AWS::StackId"
                                                                                },
                                                                            ]
                                                                        },
                                                                    ]
                                                                },
                                                            ]
                                                        },
                                                    ]
                                                },
                                                '","artifact":"Artifact_Source_S3Source","template_file":"',
                                                {"Ref": "TemplateFileName"},
                                                '","stage_params_file":"',
                                                {"Ref": "StagingParamsName"},
                                                '","account_ids":["',
                                                {"Ref": "StagingAccountId"},
                                                '"],"org_ids":["',
                                                {"Ref": "StagingOrgId"},
                                                '"],"regions":["',
                                                {"Ref": "AWS::Region"},
                                                '"]}',
                                            ],
                                        ]
                                    },
                                },
                                "InputArtifacts": [
                                    {"Name": "Artifact_Source_S3Source"}
                                ],
                                "Name": "DeployStagingStackSet",
                                "Namespace": "DeployStagingStackSet-namespace",
                                "RoleArn": {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "MultiAccountPipelineDeployStagingDeployStagingStackSetCodePipelineActionRole*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                "RunOrder": 1,
                            },
                            {
                                "ActionTypeId": {
                                    "Category": "Approval",
                                    "Owner": "AWS",
                                    "Provider": "Manual",
                                    "Version": "1",
                                },
                                "Configuration": {
                                    "NotificationArn": {
                                        "Ref": "NotificationsSNSTopicArn"
                                    },
                                    "CustomData": "Please approve to deploy to production account",
                                },
                                "Name": "DeployProd",
                                "RoleArn": {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "MultiAccountPipelineDeployStagingDeployProdCodePipelineActionRole*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                "RunOrder": 2,
                            },
                        ],
                        "Name": "DeployStaging",
                    },
                    {
                        "Actions": [
                            {
                                "ActionTypeId": {
                                    "Category": "Invoke",
                                    "Owner": "AWS",
                                    "Provider": "Lambda",
                                    "Version": "1",
                                },
                                "Configuration": {
                                    "FunctionName": {
                                        "Ref": Match.string_like_regexp(
                                            "DeployProdStackSetstacksetlambda*"
                                        )
                                    },
                                    "UserParameters": {
                                        "Fn::Join": [
                                            "",
                                            [
                                                '{"stackset_name":"',
                                                {"Ref": "StackName"},
                                                "-prod-",
                                                {
                                                    "Fn::Select": [
                                                        0,
                                                        {
                                                            "Fn::Split": [
                                                                "-",
                                                                {
                                                                    "Fn::Select": [
                                                                        2,
                                                                        {
                                                                            "Fn::Split": [
                                                                                "/",
                                                                                {
                                                                                    "Ref": "AWS::StackId"
                                                                                },
                                                                            ]
                                                                        },
                                                                    ]
                                                                },
                                                            ]
                                                        },
                                                    ]
                                                },
                                                '","artifact":"Artifact_Source_S3Source","template_file":"',
                                                {"Ref": "TemplateFileName"},
                                                '","stage_params_file":"',
                                                {"Ref": "ProdParamsName"},
                                                '","account_ids":["',
                                                {"Ref": "ProdAccountId"},
                                                '"],"org_ids":["',
                                                {"Ref": "ProdOrgId"},
                                                '"],"regions":["',
                                                {"Ref": "AWS::Region"},
                                                '"]}',
                                            ],
                                        ]
                                    },
                                },
                                "InputArtifacts": [
                                    {"Name": "Artifact_Source_S3Source"}
                                ],
                                "Name": "DeployProdStackSet",
                                "Namespace": "DeployProdStackSet-namespace",
                                "RoleArn": {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "MultiAccountPipelineDeployProdDeployProdStackSetCodePipelineActionRole*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                "RunOrder": 1,
                            }
                        ],
                        "Name": "DeployProd",
                    },
                ],
                "ArtifactStore": {
                    "Location": {
                        "Ref": Match.string_like_regexp(
                            "MultiAccountPipelineArtifactsBucket*"
                        )
                    },
                    "Type": "S3",
                },
            },
        )

    def test_events_rule(self):
        """Tests for events Rules"""
        # Rules to "Notify user of the outcome of the DeployDev|DeployStaging|DeployProd action"
        self.template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Description": Match.string_like_regexp(
                    "Notify user of the outcome of the (DeployDev|DeployStaging|DeployProd) action"
                ),
                "EventPattern": {
                    "detail": {
                        "state": ["SUCCEEDED", "FAILED"],
                        "stage": [
                            Match.string_like_regexp(
                                "(DeployDev|DeployStaging|DeployProd)"
                            )
                        ],
                        "action": [
                            Match.string_like_regexp(
                                "(DeployDevStackSet|DeployStagingStackSet|DeployProdStackSet)"
                            )
                        ],
                    },
                    "detail-type": ["CodePipeline Action Execution State Change"],
                    "source": ["aws.codepipeline"],
                    "resources": [
                        {
                            "Fn::Join": [
                                "",
                                [
                                    "arn:",
                                    {"Ref": "AWS::Partition"},
                                    ":codepipeline:",
                                    {"Ref": "AWS::Region"},
                                    ":",
                                    {"Ref": "AWS::AccountId"},
                                    ":",
                                    {
                                        "Ref": Match.string_like_regexp(
                                            "MultiAccountPipeline*"
                                        )
                                    },
                                ],
                            ]
                        }
                    ],
                },
                "State": "ENABLED",
                "Targets": [
                    {
                        "Arn": {"Ref": "NotificationsSNSTopicArn"},
                        "Id": "Target0",
                        "InputTransformer": {
                            "InputPathsMap": {
                                "detail-action": "$.detail.action",
                                "detail-pipeline": "$.detail.pipeline",
                                "detail-state": "$.detail.state",
                            },
                            "InputTemplate": Match.string_like_regexp(
                                '"(DeployDev|DeployStaging|DeployProd) action <detail-action> in the Pipeline <detail-pipeline> finished executing. Action execution result is <detail-state>"'
                            ),
                        },
                    }
                ],
            },
        )

        # Rule "Notify user of the outcome of the pipeline"
        self.template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Description": "Notify user of the outcome of the pipeline",
                "EventPattern": {
                    "detail": {"state": ["SUCCEEDED", "FAILED"]},
                    "source": ["aws.codepipeline"],
                    "resources": [
                        {
                            "Fn::Join": [
                                "",
                                [
                                    "arn:",
                                    {"Ref": "AWS::Partition"},
                                    ":codepipeline:",
                                    {"Ref": "AWS::Region"},
                                    ":",
                                    {"Ref": "AWS::AccountId"},
                                    ":",
                                    {
                                        "Ref": Match.string_like_regexp(
                                            "MultiAccountPipeline*"
                                        )
                                    },
                                ],
                            ]
                        }
                    ],
                    "detail-type": ["CodePipeline Pipeline Execution State Change"],
                },
                "State": "ENABLED",
                "Targets": [
                    {
                        "Arn": {"Ref": "NotificationsSNSTopicArn"},
                        "Id": "Target0",
                        "InputTransformer": {
                            "InputPathsMap": {
                                "detail-pipeline": "$.detail.pipeline",
                                "detail-state": "$.detail.state",
                            },
                            "InputTemplate": '"Pipeline <detail-pipeline> finished executing. Pipeline execution result is <detail-state>"',
                        },
                    }
                ],
            },
        )

    def test_template_outputs(self):
        """Tests for templates outputs"""
        self.template.has_output(
            "Pipelines",
            {
                "Value": {
                    "Fn::Join": [
                        "",
                        [
                            "https://console.aws.amazon.com/codesuite/codepipeline/pipelines/",
                            {"Ref": Match.string_like_regexp("MultiAccountPipeline*")},
                            "/view?region=",
                            {"Ref": "AWS::Region"},
                        ],
                    ]
                }
            },
        )
