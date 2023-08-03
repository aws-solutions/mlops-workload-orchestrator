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
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from test.context_helper import get_cdk_context


class TestMLOpsStacks:
    """Tests for mlops_orchestrator_stack.py (single and multi account templates)"""

    def setup_class(self):
        """Tests setup"""
        self.app = cdk.App(context=get_cdk_context("././cdk.json")["context"])

        solution_id = get_cdk_context_value(self.app, "SolutionId")
        version = get_cdk_context_value(self.app, "Version")

        # create single account stack
        single_mlops_stack = MLOpsStack(
            self.app,
            "mlops-workload-orchestrator-single-account",
            description=f"({solution_id}-sa) - MLOps Workload Orchestrator (Single Account Option). Version {version}",
            multi_account=False,
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # create multi account stack
        multi_mlops_stack = MLOpsStack(
            self.app,
            "mlops-workload-orchestrator-multi-account",
            description=f"({solution_id}-ma) - MLOps Workload Orchestrator (Multi Account Option). Version {version}",
            multi_account=True,
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # create templates
        self.template_single = Template.from_stack(single_mlops_stack)
        self.template_multi = Template.from_stack(multi_mlops_stack)
        # all templates
        self.templates = [self.template_single, self.template_multi]

    def test_template_parameters(self):
        """Tests for templates parameters"""
        # Template parameters shared across single and multi account
        for template in self.templates:
            template.has_parameter(
                "NotificationEmail",
                {
                    "Type": "String",
                    "AllowedPattern": "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
                    "ConstraintDescription": "Please enter an email address with correct format (example@example.com)",
                    "Description": "email for pipeline outcome notifications",
                    "MaxLength": 320,
                    "MinLength": 5,
                },
            )

            template.has_parameter(
                "CodeCommitRepoAddress",
                {
                    "Type": "String",
                    "AllowedPattern": "^(((https:\\/\\/|ssh:\\/\\/)(git\\-codecommit)\\.[a-zA-Z0-9_.+-]+(amazonaws\\.com\\/)[a-zA-Z0-9-.]+(\\/)[a-zA-Z0-9-.]+(\\/)[a-zA-Z0-9-.]+$)|^$)",
                    "ConstraintDescription": "CodeCommit address must follow the pattern: ssh or https://git-codecommit.REGION.amazonaws.com/version/repos/REPONAME",
                    "Description": "AWS CodeCommit repository clone URL to connect to the framework.",
                    "MaxLength": 320,
                    "MinLength": 0,
                },
            )

            template.has_parameter(
                "ExistingS3Bucket",
                {
                    "Type": "String",
                    "AllowedPattern": "((?=^.{3,63}$)(?!^(\\d+\\.)+\\d+$)(^(([a-z0-9]|[a-z0-9][a-z0-9\\-]*[a-z0-9])\\.)*([a-z0-9]|[a-z0-9][a-z0-9\\-]*[a-z0-9])$)|^$)",
                    "Description": "Name of existing S3 bucket to be used for ML assets. S3 Bucket must be in the same region as the deployed stack, and has versioning enabled. If not provided, a new S3 bucket will be created.",
                    "MaxLength": 63,
                    "MinLength": 0,
                },
            )

            template.has_parameter(
                "ExistingECRRepo",
                {
                    "Type": "String",
                    "AllowedPattern": "((?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*|^$)",
                    "Description": "Name of existing Amazon ECR repository for custom algorithms. If not provided, a new ECR repo will be created.",
                    "MaxLength": 63,
                    "MinLength": 0,
                },
            )

            template.has_parameter(
                "UseModelRegistry",
                {
                    "Type": "String",
                    "Default": "No",
                    "AllowedValues": ["Yes", "No"],
                    "Description": "Will Amazon SageMaker's Model Registry be used to provision models?",
                },
            )

            template.has_parameter(
                "CreateModelRegistry",
                {
                    "Type": "String",
                    "Default": "No",
                    "AllowedValues": ["Yes", "No"],
                    "Description": "Do you want the solution to create the SageMaker Model Package Group Name (i.e., Model Registry)",
                },
            )

            template.has_parameter(
                "AllowDetailedErrorMessage",
                {
                    "Type": "String",
                    "Default": "Yes",
                    "AllowedValues": ["Yes", "No"],
                    "Description": "Allow including a detailed message of any server-side errors in the API call's response",
                },
            )

        # Parameters only for multi account template
        self.template_multi.has_parameter(
            "DelegatedAdminAccount",
            {
                "Type": "String",
                "Default": "Yes",
                "AllowedValues": ["Yes", "No"],
                "Description": "Is a delegated administrator account used to deploy across account",
            },
        )

        self.template_multi.has_parameter(
            "DevAccountId",
            {
                "Type": "String",
                "AllowedPattern": "^\\d{12}$",
                "Description": "AWS development account number where the CF template will be deployed",
            },
        )

        self.template_multi.has_parameter(
            "DevOrgId",
            {
                "Type": "String",
                "AllowedPattern": "^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$",
                "Description": "AWS development organizational unit id where the CF template will be deployed",
            },
        )

        self.template_multi.has_parameter(
            "StagingAccountId",
            {
                "Type": "String",
                "AllowedPattern": "^\\d{12}$",
                "Description": "AWS staging account number where the CF template will be deployed",
            },
        )

        self.template_multi.has_parameter(
            "StagingOrgId",
            {
                "Type": "String",
                "AllowedPattern": "^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$",
                "Description": "AWS staging organizational unit id where the CF template will be deployed",
            },
        )

        self.template_multi.has_parameter(
            "ProdAccountId",
            {
                "Type": "String",
                "AllowedPattern": "^\\d{12}$",
                "Description": "AWS production account number where the CF template will be deployed",
            },
        )

        self.template_multi.has_parameter(
            "ProdOrgId",
            {
                "Type": "String",
                "AllowedPattern": "^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$",
                "Description": "AWS production organizational unit id where the CF template will be deployed",
            },
        )

    def test_template_conditions(self):
        """Tests for templates conditions"""
        # single and multi account templates should have the same conditions
        for template in self.templates:
            template.has_condition(
                "GitAddressProvided",
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "CodeCommitRepoAddress"}, ""]}]},
            )

            template.has_condition(
                "S3BucketProvided",
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "ExistingS3Bucket"}, ""]}]},
            )

            template.has_condition(
                "ECRProvided",
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "ExistingECRRepo"}, ""]}]},
            )

            template.has_condition(
                "CreateModelRegistryCondition",
                {"Fn::Equals": [{"Ref": "CreateModelRegistry"}, "Yes"]},
            )

            template.has_condition(
                "CreateS3Bucket", {"Fn::Equals": [{"Ref": "ExistingS3Bucket"}, ""]}
            )

            template.has_condition(
                "CreateECRRepo", {"Fn::Equals": [{"Ref": "ExistingECRRepo"}, ""]}
            )

            template.has_condition(
                "AnonymizedDatatoAWS",
                {
                    "Fn::Equals": [
                        {
                            "Fn::FindInMap": [
                                "AnonymizedData",
                                "SendAnonymizedData",
                                "Data",
                            ]
                        },
                        "Yes",
                    ]
                },
            )

    def test_all_s3_buckets_properties(self):
        """Tests for S3 buckets properties"""
        for template in self.templates:
            template.resource_count_is("AWS::S3::Bucket", 4)
            # assert for all bucket, encryption is enabled and Public Access is Blocked
            template.all_resources_properties(
                "AWS::S3::Bucket",
                {
                    "BucketEncryption": {
                        "ServerSideEncryptionConfiguration": [
                            {
                                "ServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": Match.string_like_regexp(
                                        "(AES256|aws:kms)"
                                    )
                                }
                            }
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
            template.all_resources(
                "AWS::S3::Bucket",
                {
                    "UpdateReplacePolicy": "Retain",
                    "DeletionPolicy": "Retain",
                },
            )

            # assert for blueprints and assets buckets logging is configured
            template.resource_properties_count_is(
                "AWS::S3::Bucket",
                {
                    "LoggingConfiguration": {
                        "DestinationBucketName": {
                            "Ref": Match.string_like_regexp("accessLogs*")
                        },
                        "LogFilePrefix": Match.string_like_regexp(
                            "(assets_bucket_access_logs|blueprint-repository*)"
                        ),
                    }
                },
                2,
            )

    def test_all_s3_buckets_policy(self):
        """Tests for S3 buckets policies"""
        for template in self.templates:
            # we have 4 S3 buckets, so we should have 4 bucket policies
            template.resource_count_is("AWS::S3::BucketPolicy", 4)
            # assert all buckets have bucket policy to enforce SecureTransport
            template.all_resources_properties(
                "AWS::S3::BucketPolicy",
                {
                    "PolicyDocument": {
                        "Statement": Match.array_with(
                            [
                                {
                                    "Action": "s3:*",
                                    "Condition": {
                                        "Bool": {"aws:SecureTransport": "false"}
                                    },
                                    "Effect": "Deny",
                                    "Principal": {"AWS": "*"},
                                    "Resource": [
                                        {
                                            "Fn::GetAtt": [
                                                Match.string_like_regexp(
                                                    "(accessLogs*|blueprintrepository*|pipelineassets*|MLOpsCodeCommitPipelineArtifactsBucket)"
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
                                                                "(accessLogs*|blueprintrepository*|pipelineassets*|MLOpsCodeCommitPipelineArtifactsBucket)"
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

            # assert the access logging bucket has permissions for blueprints and assets buckets
            template.resource_properties_count_is(
                "AWS::S3::BucketPolicy",
                {
                    "PolicyDocument": {
                        "Statement": Match.array_with(
                            [
                                {
                                    "Action": "s3:PutObject",
                                    "Condition": {
                                        "ArnLike": {
                                            "aws:SourceArn": [
                                                {
                                                    "Fn::Join": [
                                                        "",
                                                        [
                                                            "arn:",
                                                            {"Ref": "AWS::Partition"},
                                                            ":s3:::",
                                                            {
                                                                "Fn::If": [
                                                                    "S3BucketProvided",
                                                                    {
                                                                        "Ref": "ExistingS3Bucket"
                                                                    },
                                                                    {
                                                                        "Ref": Match.string_like_regexp(
                                                                            "pipelineassets*"
                                                                        )
                                                                    },
                                                                ]
                                                            },
                                                        ],
                                                    ]
                                                },
                                                {
                                                    "Fn::GetAtt": [
                                                        Match.string_like_regexp(
                                                            "blueprintrepository*"
                                                        ),
                                                        "Arn",
                                                    ]
                                                },
                                            ]
                                        },
                                        "StringEquals": {
                                            "aws:SourceAccount": {
                                                "Ref": "AWS::AccountId"
                                            }
                                        },
                                    },
                                    "Effect": "Allow",
                                    "Principal": {
                                        "Service": "logging.s3.amazonaws.com"
                                    },
                                    "Resource": {
                                        "Fn::Join": [
                                            "",
                                            [
                                                {
                                                    "Fn::GetAtt": [
                                                        Match.string_like_regexp(
                                                            "accessLogs*"
                                                        ),
                                                        "Arn",
                                                    ]
                                                },
                                                "/*",
                                            ],
                                        ]
                                    },
                                }
                            ]
                        ),
                        "Version": "2012-10-17",
                    }
                },
                1,
            )

        # for multi account, assert that the Blueprints and assets buckets policies give permissions to
        # dev, staging, and prod accounts
        self.template_multi.resource_properties_count_is(
            "AWS::S3::BucketPolicy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            {
                                "Action": ["s3:GetObject", "s3:ListBucket"],
                                "Effect": "Allow",
                                "Principal": {
                                    "AWS": [
                                        {
                                            "Fn::Join": [
                                                "",
                                                [
                                                    "arn:",
                                                    {"Ref": "AWS::Partition"},
                                                    ":iam::",
                                                    {"Ref": "DevAccountId"},
                                                    ":root",
                                                ],
                                            ]
                                        },
                                        {
                                            "Fn::Join": [
                                                "",
                                                [
                                                    "arn:",
                                                    {"Ref": "AWS::Partition"},
                                                    ":iam::",
                                                    {"Ref": "StagingAccountId"},
                                                    ":root",
                                                ],
                                            ]
                                        },
                                        {
                                            "Fn::Join": [
                                                "",
                                                [
                                                    "arn:",
                                                    {"Ref": "AWS::Partition"},
                                                    ":iam::",
                                                    {"Ref": "ProdAccountId"},
                                                    ":root",
                                                ],
                                            ]
                                        },
                                    ]
                                },
                                "Resource": [
                                    {
                                        "Fn::GetAtt": [
                                            Match.string_like_regexp(
                                                "(blueprintrepository*|pipelineassets*)"
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
                                                            "(blueprintrepository*|pipelineassets*)"
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
                        ]
                    ),
                    "Version": "2012-10-17",
                }
            },
            2,
        )

    def test_template_ecr_repo(self):
        for template in self.templates:
            # assert there is only ECR repo, which has ScanOnPush enabled
            template.resource_properties_count_is(
                "AWS::ECR::Repository",
                {
                    "ImageScanningConfiguration": Match.object_equals(
                        {"ScanOnPush": True}
                    )
                },
                1,
            )

            # assert the ECR repo has the expected other properties
            template.has_resource(
                "AWS::ECR::Repository",
                {
                    "UpdateReplacePolicy": "Retain",
                    "DeletionPolicy": "Retain",
                    "Condition": "CreateECRRepo",
                },
            )

        # for multi account, assert the ECR repo has resource policy to grant permissions to
        # dev, staging, and prod accounts
        self.template_multi.resource_properties_count_is(
            "AWS::ECR::Repository",
            {
                "RepositoryPolicyText": {
                    "Statement": [
                        {
                            "Action": [
                                "ecr:DescribeImages",
                                "ecr:DescribeRepositories",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchGetImage",
                                "ecr:BatchCheckLayerAvailability",
                            ],
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":iam::",
                                                {"Ref": "DevAccountId"},
                                                ":root",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":iam::",
                                                {"Ref": "StagingAccountId"},
                                                ":root",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":iam::",
                                                {"Ref": "ProdAccountId"},
                                                ":root",
                                            ],
                                        ]
                                    },
                                ]
                            },
                        }
                    ],
                    "Version": "2012-10-17",
                }
            },
            1,
        )

    def test_template_custom_resource_uuid(self):
        """Tests for UUID custom resource"""
        for template in self.templates:
            # assert the count
            template.resource_count_is("Custom::CreateUUID", 1)

            # assert custom resource properties
            template.has_resource_properties(
                "Custom::CreateUUID",
                {
                    "ServiceToken": {
                        "Fn::GetAtt": [
                            Match.string_like_regexp("SolutionHelper*"),
                            "Arn",
                        ]
                    },
                    "Resource": "UUID",
                    "CreateModelRegistry": {"Ref": "CreateModelRegistry"},
                },
            )

    def test_template_custom_resource_anonymized_data(self):
        """Tests for Anonymized data custom resource"""
        for template in self.templates:
            # assert the count
            template.resource_count_is("Custom::AnonymizedData", 1)
            # assert custom resource properties
            template.has_resource_properties(
                "Custom::AnonymizedData",
                {
                    "ServiceToken": {
                        "Fn::GetAtt": [
                            Match.string_like_regexp("SolutionHelper*"),
                            "Arn",
                        ]
                    },
                    "Resource": "AnonymizedMetric",
                    "UUID": {"Fn::GetAtt": ["CreateUniqueID", "UUID"]},
                    "bucketSelected": {"Fn::If": ["S3BucketProvided", "True", "False"]},
                    "gitSelected": {"Fn::If": ["GitAddressProvided", "True", "False"]},
                    "Region": {"Ref": "AWS::Region"},
                    "IsMultiAccount": Match.string_like_regexp(
                        "(False|True)"
                    ),  # single account=False, multi=True
                    "IsDelegatedAccount": {
                        "Ref": Match.string_like_regexp(
                            "(AWS::NoValue|DelegatedAdminAccount)"
                        )
                    },  # single account=AWS::NoValue, multi=DelegatedAdminAccount
                    "UseModelRegistry": {"Ref": "UseModelRegistry"},
                    "SolutionId": "SO0136",
                    "Version": "%%VERSION%%",
                },
            )

            # assert the custom resource other properties
            template.has_resource(
                "Custom::AnonymizedData",
                {
                    "Type": "Custom::AnonymizedData",
                    "Properties": Match.any_value(),
                    "UpdateReplacePolicy": "Delete",
                    "DeletionPolicy": "Delete",
                    "Condition": "AnonymizedDatatoAWS",
                },
            )

    def test_custom_resource_copy_assets(self):
        """Tests for copy assets custom resource"""
        for template in self.templates:
            # assert the is only one custom resource
            template.resource_count_is("AWS::CloudFormation::CustomResource", 1)

            # assert properties
            template.has_resource_properties(
                "AWS::CloudFormation::CustomResource",
                {
                    "ServiceToken": {
                        "Fn::GetAtt": [
                            Match.string_like_regexp("CustomResourceLambda*"),
                            "Arn",
                        ]
                    }
                },
            )

            # assert other properties
            template.has_resource(
                "AWS::CloudFormation::CustomResource",
                {
                    "DependsOn": [
                        Match.string_like_regexp("blueprintrepository(.*)Policy*"),
                        Match.string_like_regexp("blueprintrepository*"),
                    ],
                    "UpdateReplacePolicy": "Delete",
                    "DeletionPolicy": "Delete",
                },
            )

    def test_orchestrator_policy(self):
        """Tests for Lambda orchestrator policy"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::IAM::Policy",
                {
                    "PolicyDocument": {
                        "Statement": [
                            {
                                "Action": [
                                    "cloudformation:CreateStack",
                                    "cloudformation:DeleteStack",
                                    "cloudformation:UpdateStack",
                                    "cloudformation:DescribeStacks",
                                    "cloudformation:ListStackResources",
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
                                            ":stack/mlops-pipeline*/*",
                                        ],
                                    ]
                                },
                            },
                            {
                                "Action": [
                                    "iam:CreateRole",
                                    "iam:DeleteRole",
                                    "iam:DeleteRolePolicy",
                                    "iam:GetRole",
                                    "iam:GetRolePolicy",
                                    "iam:PassRole",
                                    "iam:PutRolePolicy",
                                    "iam:AttachRolePolicy",
                                    "iam:DetachRolePolicy",
                                    "iam:UntagRole",
                                    "iam:TagRole",
                                ],
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":iam::",
                                            {"Ref": "AWS::AccountId"},
                                            ":role/mlops-pipeline*",
                                        ],
                                    ]
                                },
                            },
                            {
                                "Action": [
                                    "ecr:CreateRepository",
                                    "ecr:DescribeRepositories",
                                ],
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":ecr:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":repository/",
                                            {
                                                "Fn::If": [
                                                    "ECRProvided",
                                                    {"Ref": "ExistingECRRepo"},
                                                    {"Ref": "ECRRepoC36DC9E6"},
                                                ]
                                            },
                                        ],
                                    ]
                                },
                            },
                            {
                                "Action": [
                                    "codebuild:CreateProject",
                                    "codebuild:DeleteProject",
                                    "codebuild:BatchGetProjects",
                                ],
                                "Effect": "Allow",
                                "Resource": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":codebuild:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":project/ContainerFactory*",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":codebuild:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":project/VerifySagemaker*",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":codebuild:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":report-group/*",
                                            ],
                                        ]
                                    },
                                ],
                            },
                            {
                                "Action": [
                                    "lambda:CreateFunction",
                                    "lambda:DeleteFunction",
                                    "lambda:InvokeFunction",
                                    "lambda:PublishLayerVersion",
                                    "lambda:DeleteLayerVersion",
                                    "lambda:GetLayerVersion",
                                    "lambda:GetFunctionConfiguration",
                                    "lambda:GetFunction",
                                    "lambda:AddPermission",
                                    "lambda:RemovePermission",
                                    "lambda:UpdateFunctionConfiguration",
                                    "lambda:TagResource",
                                ],
                                "Effect": "Allow",
                                "Resource": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":lambda:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":layer:*",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":lambda:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":function:*",
                                            ],
                                        ]
                                    },
                                ],
                            },
                            {
                                "Action": ["s3:GetObject", "s3:ListBucket"],
                                "Effect": "Allow",
                                "Resource": [
                                    {
                                        "Fn::GetAtt": [
                                            Match.string_like_regexp(
                                                "blueprintrepository*"
                                            ),
                                            "Arn",
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":s3:::",
                                                {
                                                    "Fn::If": [
                                                        "S3BucketProvided",
                                                        {"Ref": "ExistingS3Bucket"},
                                                        {
                                                            "Ref": Match.string_like_regexp(
                                                                "pipelineassets*"
                                                            )
                                                        },
                                                    ]
                                                },
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                {
                                                    "Fn::GetAtt": [
                                                        Match.string_like_regexp(
                                                            "blueprintrepository*"
                                                        ),
                                                        "Arn",
                                                    ]
                                                },
                                                "/*",
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
                                                {
                                                    "Fn::If": [
                                                        "S3BucketProvided",
                                                        {"Ref": "ExistingS3Bucket"},
                                                        {
                                                            "Ref": Match.string_like_regexp(
                                                                "pipelineassets*"
                                                            )
                                                        },
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
                                    "servicecatalog:CreateApplication",
                                    "servicecatalog:GetApplication",
                                    "servicecatalog:UpdateApplication",
                                    "servicecatalog:DeleteApplication",
                                    "servicecatalog:CreateAttributeGroup",
                                    "servicecatalog:GetAttributeGroup",
                                    "servicecatalog:UpdateAttributeGroup",
                                    "servicecatalog:DeleteAttributeGroup",
                                    "servicecatalog:AssociateResource",
                                    "servicecatalog:DisassociateResource",
                                    "servicecatalog:AssociateAttributeGroup",
                                    "servicecatalog:DisassociateAttributeGroup",
                                    "servicecatalog:TagResource",
                                ],
                                "Effect": "Allow",
                                "Resource": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":servicecatalog:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":/applications/*",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":servicecatalog:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":/attribute-groups/*",
                                            ],
                                        ]
                                    },
                                ],
                            },
                            {
                                "Action": [
                                    "codepipeline:CreatePipeline",
                                    "codepipeline:UpdatePipeline",
                                    "codepipeline:DeletePipeline",
                                    "codepipeline:GetPipeline",
                                    "codepipeline:GetPipelineState",
                                    "codepipeline:TagResource",
                                    "codepipeline:UntagResource",
                                ],
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":codepipeline:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":mlops-pipeline*",
                                        ],
                                    ]
                                },
                            },
                            {
                                "Action": [
                                    "apigateway:POST",
                                    "apigateway:PATCH",
                                    "apigateway:DELETE",
                                    "apigateway:GET",
                                    "apigateway:PUT",
                                ],
                                "Effect": "Allow",
                                "Resource": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":apigateway:",
                                                {"Ref": "AWS::Region"},
                                                "::/restapis/*",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":apigateway:",
                                                {"Ref": "AWS::Region"},
                                                "::/restapis",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":apigateway:",
                                                {"Ref": "AWS::Region"},
                                                "::/account",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":apigateway:",
                                                {"Ref": "AWS::Region"},
                                                "::/usageplans",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":apigateway:",
                                                {"Ref": "AWS::Region"},
                                                "::/usageplans/*",
                                            ],
                                        ]
                                    },
                                ],
                            },
                            {
                                "Action": [
                                    "logs:CreateLogGroup",
                                    "logs:DescribeLogGroups",
                                ],
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":logs:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":log-group:*",
                                        ],
                                    ]
                                },
                            },
                            {
                                "Action": [
                                    "s3:CreateBucket",
                                    "s3:PutEncryptionConfiguration",
                                    "s3:PutBucketVersioning",
                                    "s3:PutBucketPublicAccessBlock",
                                    "s3:PutBucketLogging",
                                    "s3:GetBucketPolicy",
                                    "s3:PutBucketPolicy",
                                    "s3:DeleteBucketPolicy",
                                ],
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::Join": [
                                        "",
                                        ["arn:", {"Ref": "AWS::Partition"}, ":s3:::*"],
                                    ]
                                },
                            },
                            {
                                "Action": "s3:PutObject",
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":s3:::",
                                            {
                                                "Fn::If": [
                                                    "S3BucketProvided",
                                                    {"Ref": "ExistingS3Bucket"},
                                                    {
                                                        "Ref": Match.string_like_regexp(
                                                            "pipelineassets*"
                                                        )
                                                    },
                                                ]
                                            },
                                            "/*",
                                        ],
                                    ]
                                },
                            },
                            {
                                "Action": [
                                    "sns:CreateTopic",
                                    "sns:DeleteTopic",
                                    "sns:Subscribe",
                                    "sns:Unsubscribe",
                                    "sns:GetTopicAttributes",
                                    "sns:SetTopicAttributes",
                                ],
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":sns:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":mlops-pipeline*-*PipelineNotification*",
                                        ],
                                    ]
                                },
                            },
                            {
                                "Action": [
                                    "events:PutRule",
                                    "events:DescribeRule",
                                    "events:PutTargets",
                                    "events:RemoveTargets",
                                    "events:DeleteRule",
                                    "events:PutEvents",
                                ],
                                "Effect": "Allow",
                                "Resource": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":events:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":rule/*",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":events:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":event-bus/*",
                                            ],
                                        ]
                                    },
                                ],
                            },
                            {
                                "Action": [
                                    "sagemaker:CreateModelCard",
                                    "sagemaker:DescribeModelCard",
                                    "sagemaker:UpdateModelCard",
                                    "sagemaker:DeleteModelCard",
                                    "sagemaker:CreateModelCardExportJob",
                                    "sagemaker:DescribeModelCardExportJob",
                                    "sagemaker:DescribeModel",
                                    "sagemaker:DescribeTrainingJob",
                                ],
                                "Effect": "Allow",
                                "Resource": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":sagemaker:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":model-card/*",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":sagemaker:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":model/*",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":sagemaker:",
                                                {"Ref": "AWS::Region"},
                                                ":",
                                                {"Ref": "AWS::AccountId"},
                                                ":training-job/*",
                                            ],
                                        ]
                                    },
                                ],
                            },
                            {
                                "Action": [
                                    "sagemaker:ListModelCards",
                                    "sagemaker:Search",
                                ],
                                "Effect": "Allow",
                                "Resource": "*",
                            },
                        ],
                        "Version": "2012-10-17",
                    },
                },
            )

    def test_template_sns(self):
        """Tests for sns topic"""
        for template in self.templates:
            # assert template has one SNS Topic
            template.resource_count_is("AWS::SNS::Topic", 1)

            # assert there one SNS subscription with these properties
            template.resource_properties_count_is(
                "AWS::SNS::Subscription",
                {
                    "Protocol": "email",
                    "TopicArn": {
                        "Ref": Match.string_like_regexp("MLOpsNotificationsTopic*")
                    },
                    "Endpoint": {"Ref": "NotificationEmail"},
                },
                1,
            )

            # assert there one Topic Policy with these properties
            template.resource_properties_count_is(
                "AWS::SNS::TopicPolicy",
                {
                    "PolicyDocument": {
                        "Statement": [
                            {
                                "Action": "sns:Publish",
                                "Effect": "Allow",
                                "Principal": {"Service": "events.amazonaws.com"},
                                "Resource": {
                                    "Ref": Match.string_like_regexp(
                                        "MLOpsNotificationsTopic*"
                                    )
                                },
                                "Sid": "0",
                            }
                        ],
                        "Version": "2012-10-17",
                    },
                    "Topics": [
                        {"Ref": Match.string_like_regexp("MLOpsNotificationsTopic*")}
                    ],
                },
                1,
            )

    def test_sagemaker_sdk_layer(self):
        """Test for SageMaker SDK Lambda layer"""
        for template in self.templates:
            # assert there is only one layer
            template.resource_count_is("AWS::Lambda::LayerVersion", 1)
            # assert layer properties
            template.has_resource_properties(
                "AWS::Lambda::LayerVersion",
                {
                    "Content": {
                        "S3Bucket": {
                            "Ref": Match.string_like_regexp("blueprintrepository*")
                        },
                        "S3Key": "blueprints/lambdas/sagemaker_layer.zip",
                    },
                    "CompatibleRuntimes": ["python3.9", "python3.10"],
                },
            )
            # assert layer's dependency
            template.has_resource(
                "AWS::Lambda::LayerVersion", {"DependsOn": ["CustomResourceCopyAssets"]}
            )

    def test_api_gateway(self):
        """Test for API Gateway"""
        for template in self.templates:
            # assert template has one Rest API
            template.resource_count_is("AWS::ApiGateway::RestApi", 1)

            # assert API properties
            template.has_resource_properties(
                "AWS::ApiGateway::RestApi",
                {
                    "EndpointConfiguration": {"Types": ["EDGE"]},
                    "Name": {
                        "Fn::Join": ["", [{"Ref": "AWS::StackName"}, "-orchestrator"]]
                    },
                },
            )

            # assert template has one API Deployment
            template.resource_count_is("AWS::ApiGateway::Deployment", 1)

            # assert API deployment properties
            template.has_resource_properties(
                "AWS::ApiGateway::Deployment",
                {
                    "RestApiId": {
                        "Ref": Match.string_like_regexp(
                            "PipelineOrchestrationLambdaRestApi*"
                        )
                    },
                    "Description": "Automatically created by the RestApi construct",
                },
            )

            # assert API deployment dependencies
            template.has_resource(
                "AWS::ApiGateway::Deployment",
                {
                    "DependsOn": [
                        Match.string_like_regexp(
                            "PipelineOrchestrationLambdaRestApipipelinestatusPOST*"
                        ),
                        Match.string_like_regexp(
                            "PipelineOrchestrationLambdaRestApipipelinestatus*"
                        ),
                        Match.string_like_regexp(
                            "PipelineOrchestrationLambdaRestApiprovisionpipelinePOST*"
                        ),
                        Match.string_like_regexp(
                            "PipelineOrchestrationLambdaRestApiprovisionpipeline*"
                        ),
                    ]
                },
            )

            # assert API gateway has permissions to invoke the orchestrator Lambda
            template.has_resource_properties(
                "AWS::Lambda::Permission",
                {
                    "Action": "lambda:InvokeFunction",
                    "FunctionName": {
                        "Fn::GetAtt": [
                            Match.string_like_regexp(
                                "PipelineOrchestrationLambdaFunction*"
                            ),
                            "Arn",
                        ]
                    },
                    "Principal": "apigateway.amazonaws.com",
                    "SourceArn": {
                        "Fn::Join": [
                            "",
                            [
                                "arn:",
                                {"Ref": "AWS::Partition"},
                                ":execute-api:",
                                {"Ref": "AWS::Region"},
                                ":",
                                {"Ref": "AWS::AccountId"},
                                ":",
                                {
                                    "Ref": Match.string_like_regexp(
                                        "PipelineOrchestrationLambdaRestApi*"
                                    )
                                },
                                "/",
                                {
                                    "Ref": Match.string_like_regexp(
                                        "PipelineOrchestrationLambdaRestApiDeploymentStageprod*"
                                    )
                                },
                                "/POST/provisionpipeline",
                            ],
                        ]
                    },
                },
            )

            # assert all methods has Authorization Type "AWS_IAM"
            template.all_resources_properties(
                "AWS::ApiGateway::Method",
                {
                    "AuthorizationType": "AWS_IAM",
                },
            )

            # assert we have two APIs resources: /pipelinestatus and /provisionpipeline
            template.has_resource_properties(
                "AWS::ApiGateway::Resource",
                {
                    "PathPart": Match.string_like_regexp(
                        "(pipelinestatus|provisionpipeline)"
                    ),
                },
            )

    def test_events_rule(self):
        """Tests for events Rule"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::Events::Rule",
                {
                    "EventPattern": {
                        "source": ["aws.codecommit"],
                        "resources": [
                            {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":codecommit:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":",
                                        {
                                            "Fn::Select": [
                                                5,
                                                {
                                                    "Fn::Split": [
                                                        "/",
                                                        {
                                                            "Ref": "CodeCommitRepoAddress"
                                                        },
                                                    ]
                                                },
                                            ]
                                        },
                                    ],
                                ]
                            }
                        ],
                        "detail-type": ["CodeCommit Repository State Change"],
                        "detail": {
                            "event": ["referenceCreated", "referenceUpdated"],
                            "referenceName": ["main"],
                        },
                    },
                    "State": "ENABLED",
                    "Targets": [
                        {
                            "Arn": {
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
                                                "MLOpsCodeCommitPipeline*"
                                            )
                                        },
                                    ],
                                ]
                            },
                            "Id": "Target0",
                            "RoleArn": {
                                "Fn::GetAtt": [
                                    Match.string_like_regexp(
                                        "MLOpsCodeCommitPipelineEventsRole*"
                                    ),
                                    "Arn",
                                ]
                            },
                        }
                    ],
                },
            )

    def test_codebuild(self):
        """Tests for Codebuild"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::CodeBuild::Project",
                {
                    "Artifacts": {"Type": "CODEPIPELINE"},
                    "Environment": Match.object_equals(
                        {
                            "ComputeType": "BUILD_GENERAL1_SMALL",
                            "Image": "aws/codebuild/standard:1.0",
                            "ImagePullCredentialsType": "CODEBUILD",
                            "PrivilegedMode": False,
                            "Type": "LINUX_CONTAINER",
                        }
                    ),
                    "ServiceRole": {
                        "Fn::GetAtt": ["TakeconfigfileRoleD1BE5721", "Arn"]
                    },
                    "Source": {
                        "BuildSpec": {
                            "Fn::Join": [
                                "",
                                [
                                    '{\n  "version": "0.2",\n  "phases": {\n    "build": {\n      "commands": [\n        "ls -a",\n        "aws lambda invoke --function-name ',
                                    {
                                        "Ref": "PipelineOrchestrationLambdaFunction7EE5E931"
                                    },
                                    ' --payload fileb://mlops-config.json response.json --invocation-type RequestResponse"\n      ]\n    }\n  }\n}',
                                ],
                            ]
                        },
                        "Type": "CODEPIPELINE",
                    },
                    "Cache": {"Type": "NO_CACHE"},
                    "EncryptionKey": "alias/aws/s3",
                },
            )

    def test_codepipeline(self):
        """Tests for CodePipeline"""
        for template in self.templates:
            # assert there is one codepipeline
            template.resource_count_is("AWS::CodePipeline::Pipeline", 1)

            # assert properties
            template.has_resource_properties(
                "AWS::CodePipeline::Pipeline",
                {
                    "RoleArn": {
                        "Fn::GetAtt": [
                            Match.string_like_regexp("MLOpsCodeCommitPipelineRole*"),
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
                                        "Provider": "CodeCommit",
                                        "Version": "1",
                                    },
                                    "Configuration": Match.object_equals(
                                        {
                                            "RepositoryName": {
                                                "Fn::Select": [
                                                    5,
                                                    {
                                                        "Fn::Split": [
                                                            "/",
                                                            {
                                                                "Ref": "CodeCommitRepoAddress"
                                                            },
                                                        ]
                                                    },
                                                ]
                                            },
                                            "BranchName": "main",
                                            "PollForSourceChanges": False,
                                        }
                                    ),
                                    "Name": "CodeCommit",
                                    "OutputArtifacts": [
                                        {"Name": "Artifact_Source_CodeCommit"}
                                    ],
                                    "RoleArn": {
                                        "Fn::GetAtt": [
                                            Match.string_like_regexp(
                                                "MLOpsCodeCommitPipelineSourceCodeCommitCodePipelineActionRole*"
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
                                        "Category": "Build",
                                        "Owner": "AWS",
                                        "Provider": "CodeBuild",
                                        "Version": "1",
                                    },
                                    "Configuration": {
                                        "ProjectName": {
                                            "Ref": Match.string_like_regexp(
                                                "Takeconfigfile*"
                                            )
                                        }
                                    },
                                    "InputArtifacts": [
                                        {"Name": "Artifact_Source_CodeCommit"}
                                    ],
                                    "Name": "provision_pipeline",
                                    "RoleArn": {
                                        "Fn::GetAtt": [
                                            Match.string_like_regexp(
                                                "MLOpsCodeCommitPipelineTakeConfigprovisionpipelineCodePipelineActionRole*"
                                            ),
                                            "Arn",
                                        ]
                                    },
                                    "RunOrder": 1,
                                }
                            ],
                            "Name": "TakeConfig",
                        },
                    ],
                    "ArtifactStore": {
                        "Location": {
                            "Ref": Match.string_like_regexp(
                                "MLOpsCodeCommitPipelineArtifactsBucket*"
                            )
                        },
                        "Type": "S3",
                    },
                },
            )

            # assert codepipeline dependencies and condition
            template.has_resource(
                "AWS::CodePipeline::Pipeline",
                {
                    "DependsOn": [
                        Match.string_like_regexp(
                            "MLOpsCodeCommitPipelineRoleDefaultPolicy*"
                        ),
                        Match.string_like_regexp("MLOpsCodeCommitPipelineRole*"),
                    ],
                    "Condition": "GitAddressProvided",
                },
            )

    def test_sagemaker_model_registry(self):
        """Tests for SageMaker Model Registry"""
        for template in self.templates:
            # assert template has one ModelPackageGroup
            template.resource_count_is("AWS::SageMaker::ModelPackageGroup", 1)

            # assert registry properties
            template.has_resource_properties(
                "AWS::SageMaker::ModelPackageGroup",
                {
                    "ModelPackageGroupName": {
                        "Fn::Join": [
                            "",
                            [
                                "mlops-model-registry-",
                                {
                                    "Fn::Select": [
                                        0,
                                        {
                                            "Fn::Split": [
                                                "-",
                                                {
                                                    "Fn::GetAtt": [
                                                        "CreateUniqueID",
                                                        "UUID",
                                                    ]
                                                },
                                            ]
                                        },
                                    ]
                                },
                            ],
                        ]
                    },
                    "ModelPackageGroupDescription": "SageMaker model package group name (model registry) for mlops",
                    "Tags": [{"Key": "stack-name", "Value": {"Ref": "AWS::StackName"}}],
                },
            )

            # assert the model registry other properties, dependency and condition
            template.has_resource(
                "AWS::SageMaker::ModelPackageGroup",
                {
                    "DependsOn": ["CreateUniqueID"],
                    "UpdateReplacePolicy": "Retain",
                    "DeletionPolicy": "Retain",
                    "Condition": "CreateModelRegistryCondition",
                },
            )

        # for multi account, assert the model registry resource policy grants permissions
        # to dev, staging and prod accounts
        self.template_multi.has_resource_properties(
            "AWS::SageMaker::ModelPackageGroup",
            {
                "ModelPackageGroupPolicy": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "AddPermModelPackageGroup",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":iam::",
                                                {"Ref": "DevAccountId"},
                                                ":root",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":iam::",
                                                {"Ref": "StagingAccountId"},
                                                ":root",
                                            ],
                                        ]
                                    },
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:",
                                                {"Ref": "AWS::Partition"},
                                                ":iam::",
                                                {"Ref": "ProdAccountId"},
                                                ":root",
                                            ],
                                        ]
                                    },
                                ]
                            },
                            "Action": [
                                "sagemaker:DescribeModelPackageGroup",
                                "sagemaker:DescribeModelPackage",
                                "sagemaker:ListModelPackages",
                                "sagemaker:UpdateModelPackage",
                                "sagemaker:CreateModel",
                            ],
                            "Resource": [
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            {
                                                "Fn::Sub": [
                                                    "arn:${PARTITION}:sagemaker:${REGION}:${ACCOUNT_ID}",
                                                    {
                                                        "PARTITION": {
                                                            "Ref": "AWS::Partition"
                                                        },
                                                        "REGION": {
                                                            "Ref": "AWS::Region"
                                                        },
                                                        "ACCOUNT_ID": {
                                                            "Ref": "AWS::AccountId"
                                                        },
                                                    },
                                                ]
                                            },
                                            ":model-package-group/mlops-model-registry-",
                                            {
                                                "Fn::Select": [
                                                    0,
                                                    {
                                                        "Fn::Split": [
                                                            "-",
                                                            {
                                                                "Fn::GetAtt": [
                                                                    "CreateUniqueID",
                                                                    "UUID",
                                                                ]
                                                            },
                                                        ]
                                                    },
                                                ]
                                            },
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            {
                                                "Fn::Sub": [
                                                    "arn:${PARTITION}:sagemaker:${REGION}:${ACCOUNT_ID}",
                                                    {
                                                        "PARTITION": {
                                                            "Ref": "AWS::Partition"
                                                        },
                                                        "REGION": {
                                                            "Ref": "AWS::Region"
                                                        },
                                                        "ACCOUNT_ID": {
                                                            "Ref": "AWS::AccountId"
                                                        },
                                                    },
                                                ]
                                            },
                                            ":model-package/mlops-model-registry-",
                                            {
                                                "Fn::Select": [
                                                    0,
                                                    {
                                                        "Fn::Split": [
                                                            "-",
                                                            {
                                                                "Fn::GetAtt": [
                                                                    "CreateUniqueID",
                                                                    "UUID",
                                                                ]
                                                            },
                                                        ]
                                                    },
                                                ]
                                            },
                                            "/*",
                                        ],
                                    ]
                                },
                            ],
                        }
                    ],
                },
            },
        )

    def test_template_outputs(self):
        """Tests for templates outputs"""
        # both single and multi templates should have teh same outputs
        for template in self.templates:
            template.has_output(
                "PipelineOrchestrationLambdaRestApiEndpoint9B628338",
                {
                    "Value": {
                        "Fn::Join": [
                            "",
                            [
                                "https://",
                                {
                                    "Ref": Match.string_like_regexp(
                                        "PipelineOrchestrationLambdaRestApi*"
                                    )
                                },
                                ".execute-api.",
                                {"Ref": "AWS::Region"},
                                ".",
                                {"Ref": "AWS::URLSuffix"},
                                "/",
                                {
                                    "Ref": Match.string_like_regexp(
                                        "PipelineOrchestrationLambdaRestApiDeploymentStageprod*"
                                    )
                                },
                                "/",
                            ],
                        ]
                    }
                },
            )

            template.has_output(
                "BlueprintsBucket",
                {
                    "Description": "S3 Bucket to upload MLOps Framework Blueprints",
                    "Value": {
                        "Fn::Join": [
                            "",
                            [
                                "https://s3.console.aws.amazon.com/s3/buckets/",
                                {
                                    "Ref": Match.string_like_regexp(
                                        "blueprintrepository*"
                                    )
                                },
                            ],
                        ]
                    },
                },
            )

            template.has_output(
                "AssetsBucket",
                {
                    "Description": "S3 Bucket to upload model artifact",
                    "Value": {
                        "Fn::Join": [
                            "",
                            [
                                "https://s3.console.aws.amazon.com/s3/buckets/",
                                {
                                    "Fn::If": [
                                        "S3BucketProvided",
                                        {"Ref": "ExistingS3Bucket"},
                                        {
                                            "Ref": Match.string_like_regexp(
                                                "pipelineassets*"
                                            )
                                        },
                                    ]
                                },
                            ],
                        ]
                    },
                },
            )

            template.has_output(
                "ECRRepoName",
                {
                    "Description": "Amazon ECR repository's name",
                    "Value": {
                        "Fn::If": [
                            "ECRProvided",
                            {"Ref": "ExistingECRRepo"},
                            {"Ref": Match.string_like_regexp("ECRRepo*")},
                        ]
                    },
                },
            )

            template.has_output(
                "ECRRepoArn",
                {
                    "Description": "Amazon ECR repository's arn",
                    "Value": {
                        "Fn::If": [
                            "ECRProvided",
                            {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":ecr:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":repository/",
                                        {"Ref": "ExistingECRRepo"},
                                    ],
                                ]
                            },
                            {
                                "Fn::GetAtt": [
                                    Match.string_like_regexp("ECRRepo*"),
                                    "Arn",
                                ]
                            },
                        ]
                    },
                },
            )

            template.has_output(
                "ModelRegistryArn",
                {
                    "Description": "SageMaker model package group arn",
                    "Value": {
                        "Fn::If": [
                            "CreateModelRegistryCondition",
                            {
                                "Fn::GetAtt": [
                                    "SageMakerModelRegistry",
                                    "ModelPackageGroupArn",
                                ]
                            },
                            "[No Model Package Group was created]",
                        ]
                    },
                },
            )

            template.has_output(
                "MLOpsNotificationsTopicArn",
                {
                    "Description": "MLOps notifications SNS topic arn.",
                    "Value": {
                        "Ref": Match.string_like_regexp("MLOpsNotificationsTopic*")
                    },
                },
            )
