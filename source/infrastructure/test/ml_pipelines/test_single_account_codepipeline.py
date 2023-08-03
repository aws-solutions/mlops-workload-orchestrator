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
from lib.blueprints.ml_pipelines.single_account_codepipeline import (
    SingleAccountCodePipelineStack,
)
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from test.context_helper import get_cdk_context


class TestSingleAccountCodePipelineStack:
    """Tests for single_account_codepipeline stack"""

    def setup_class(self):
        """Tests setup"""
        self.app = cdk.App(context=get_cdk_context("././cdk.json")["context"])

        solution_id = get_cdk_context_value(self.app, "SolutionId")
        version = get_cdk_context_value(self.app, "Version")

        single_codepipeline = SingleAccountCodePipelineStack(
            self.app,
            "SingleAccountCodePipelineStack",
            description=(
                f"({solution_id}byom-sac) - Single-account codepipeline. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # create template
        self.template = Template.from_stack(single_codepipeline)

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
            "TemplateParamsName",
            {
                "Type": "String",
                "AllowedPattern": "^.*\\.json$",
                "Description": "parameters json file's name for the main stage",
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
            "NotificationsSNSTopicArn",
            {
                "Type": "String",
                "AllowedPattern": "^arn:\\S+:sns:\\S+:\\d{12}:\\S+$",
                "Description": "AWS SNS Topics arn used by the MLOps Workload Orchestrator to notify the administrator.",
            },
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

        # assert all S3 buckets are retained after stack is deleted
        self.template.all_resources(
            "AWS::S3::Bucket",
            {
                "UpdateReplacePolicy": "Retain",
                "DeletionPolicy": "Retain",
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
                                                "SingleAccountPipelineArtifactsBucket*"
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
                                                            "SingleAccountPipelineArtifactsBucket*"
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
                        Match.string_like_regexp("SingleAccountPipelineRole*"),
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
                                            "SingleAccountPipelineSourceS3SourceCodePipelineActionRole*"
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
                                    "Category": "Deploy",
                                    "Owner": "AWS",
                                    "Provider": "CloudFormation",
                                    "Version": "1",
                                },
                                "Configuration": {
                                    "StackName": {"Ref": "StackName"},
                                    "Capabilities": "CAPABILITY_NAMED_IAM",
                                    "RoleArn": {
                                        "Fn::GetAtt": [
                                            Match.string_like_regexp(
                                                "SingleAccountPipelineDeployCloudFormationdeploystackRole*"
                                            ),
                                            "Arn",
                                        ]
                                    },
                                    "TemplateConfiguration": {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "Artifact_Source_S3Source::",
                                                {"Ref": "TemplateParamsName"},
                                            ],
                                        ]
                                    },
                                    "ActionMode": "REPLACE_ON_FAILURE",
                                    "TemplatePath": {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "Artifact_Source_S3Source::",
                                                {"Ref": "TemplateFileName"},
                                            ],
                                        ]
                                    },
                                },
                                "InputArtifacts": [
                                    {"Name": "Artifact_Source_S3Source"}
                                ],
                                "Name": "deploy_stack",
                                "Namespace": "deploy_stack-namespace",
                                "RoleArn": {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "SingleAccountPipelineDeployCloudFormationdeploystackCodePipelineActionRole*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                "RunOrder": 1,
                            }
                        ],
                        "Name": "DeployCloudFormation",
                    },
                ],
                "ArtifactStore": {
                    "Location": {
                        "Ref": Match.string_like_regexp(
                            "SingleAccountPipelineArtifactsBucket*"
                        )
                    },
                    "Type": "S3",
                },
            },
        )

        # assert codepipeline dependencies
        self.template.has_resource(
            "AWS::CodePipeline::Pipeline",
            {
                "DependsOn": [
                    Match.string_like_regexp("SingleAccountPipelineRoleDefaultPolicy*"),
                    Match.string_like_regexp("SingleAccountPipelineRole*"),
                ]
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
                                            "SingleAccountPipelineArtifactsBucket*"
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
                                                        "SingleAccountPipelineArtifactsBucket*"
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
                    "SingleAccountPipelineSourceS3SourceCodePipelineActionRoleDefaultPolicy*"
                ),
                "Roles": [
                    {
                        "Ref": Match.string_like_regexp(
                            "SingleAccountPipelineSourceS3SourceCodePipelineActionRole*"
                        )
                    }
                ],
            },
        )

        # assert Policy for Deploy stack stage
        self.template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": "iam:PassRole",
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::GetAtt": [
                                    Match.string_like_regexp(
                                        "SingleAccountPipelineDeployCloudFormationdeploystackRole*"
                                    ),
                                    "Arn",
                                ]
                            },
                        },
                        {
                            "Action": ["s3:GetObject*", "s3:GetBucket*", "s3:List*"],
                            "Effect": "Allow",
                            "Resource": [
                                {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "SingleAccountPipelineArtifactsBucket*"
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
                                                        "SingleAccountPipelineArtifactsBucket*"
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
                        {
                            "Action": [
                                "cloudformation:CreateStack",
                                "cloudformation:DeleteStack",
                                "cloudformation:DescribeStack*",
                                "cloudformation:GetStackPolicy",
                                "cloudformation:GetTemplate*",
                                "cloudformation:SetStackPolicy",
                                "cloudformation:UpdateStack",
                                "cloudformation:ValidateTemplate",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":cloudformation:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":stack/",
                                        {"Ref": "StackName"},
                                        "/*",
                                    ],
                                ]
                            },
                        },
                    ],
                    "Version": "2012-10-17",
                },
                "PolicyName": Match.string_like_regexp(
                    "SingleAccountPipelineDeployCloudFormationdeploystackCodePipelineActionRoleDefaultPolicy*"
                ),
                "Roles": [
                    {
                        "Ref": Match.string_like_regexp(
                            "SingleAccountPipelineDeployCloudFormationdeploystackCodePipelineActionRole*"
                        )
                    }
                ],
            },
        )

        # assert Policy for Deploy stack stage default policy
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
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "SingleAccountPipelineArtifactsBucket*"
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
                                                        "SingleAccountPipelineArtifactsBucket*"
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
                        {"Action": "*", "Effect": "Allow", "Resource": "*"},
                    ],
                    "Version": "2012-10-17",
                },
                "PolicyName": Match.string_like_regexp(
                    "SingleAccountPipelineDeployCloudFormationdeploystackRoleDefaultPolicy*"
                ),
                "Roles": [
                    {
                        "Ref": Match.string_like_regexp(
                            "SingleAccountPipelineDeployCloudFormationdeploystackRole*"
                        )
                    }
                ],
            },
        )

    def test_events_rule(self):
        """Tests for events Rule"""
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
                                            "SingleAccountPipeline*"
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
                            {"Ref": Match.string_like_regexp("SingleAccountPipeline*")},
                            "/view?region=",
                            {"Ref": "AWS::Region"},
                        ],
                    ]
                }
            },
        )
