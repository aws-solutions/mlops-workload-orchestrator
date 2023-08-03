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
from lib.blueprints.ml_pipelines.byom_custom_algorithm_image_builder import (
    BYOMCustomAlgorithmImageBuilderStack,
)
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from test.context_helper import get_cdk_context


class TestImageBuilder:
    """Tests for byom_custom_algorithm_image_builder stack"""

    def setup_class(self):
        """Tests setup"""
        app = cdk.App(context=get_cdk_context("././cdk.json")["context"])

        solution_id = get_cdk_context_value(app, "SolutionId")
        version = get_cdk_context_value(app, "Version")

        image_builder_stack = BYOMCustomAlgorithmImageBuilderStack(
            app,
            "BYOMCustomAlgorithmImageBuilderStack",
            description=(
                f"({solution_id}byom-caib) - Bring Your Own Model pipeline to build custom algorithm docker images"
                f"in MLOps Workload Orchestrator. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # create template
        self.template = Template.from_stack(image_builder_stack)

    def test_template_parameters(self):
        """Tests for templates parameters"""
        self.template.has_parameter(
            "AssetsBucket",
            {
                "Type": "String",
                "Description": "Bucket name where the model and baselines data are stored.",
                "MinLength": 3,
            },
        )

        self.template.has_parameter(
            "CustomImage",
            {
                "Type": "String",
                "Default": "",
                "Description": "Should point to a zip file containing dockerfile and assets for building a custom model. If empty it will be using containers from SageMaker Registry",
            },
        )

        self.template.has_parameter(
            "ECRRepoName",
            {
                "Type": "String",
                "AllowedPattern": "(?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*",
                "Description": "Name of the Amazon ECR repository. This repo will be used to store custom algorithms images.",
                "MinLength": 1,
            },
        )

        self.template.has_parameter(
            "ImageTag",
            {
                "Type": "String",
                "Description": "Docker image tag for the custom algorithm",
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

    def test_codebuild_policy(self):
        """Tests for Codebuild Policy"""
        self.template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "ecr:BatchCheckLayerAvailability",
                                "ecr:CompleteLayerUpload",
                                "ecr:InitiateLayerUpload",
                                "ecr:PutImage",
                                "ecr:UploadLayerPart",
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
                                        {"Ref": "ECRRepoName"},
                                    ],
                                ]
                            },
                        },
                        {
                            "Action": "ecr:GetAuthorizationToken",
                            "Effect": "Allow",
                            "Resource": "*",
                        },
                        {
                            "Action": [
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":logs:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":log-group:/aws/codebuild/",
                                            {"Ref": "ContainerFactory35DC485A"},
                                        ],
                                    ]
                                },
                                {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {"Ref": "AWS::Partition"},
                                            ":logs:",
                                            {"Ref": "AWS::Region"},
                                            ":",
                                            {"Ref": "AWS::AccountId"},
                                            ":log-group:/aws/codebuild/",
                                            {
                                                "Ref": Match.string_like_regexp(
                                                    "ContainerFactory*"
                                                )
                                            },
                                            ":*",
                                        ],
                                    ]
                                },
                            ],
                        },
                        {
                            "Action": [
                                "codebuild:CreateReportGroup",
                                "codebuild:CreateReport",
                                "codebuild:UpdateReport",
                                "codebuild:BatchPutTestCases",
                                "codebuild:BatchPutCodeCoverages",
                            ],
                            "Effect": "Allow",
                            "Resource": {
                                "Fn::Join": [
                                    "",
                                    [
                                        "arn:",
                                        {"Ref": "AWS::Partition"},
                                        ":codebuild:",
                                        {"Ref": "AWS::Region"},
                                        ":",
                                        {"Ref": "AWS::AccountId"},
                                        ":report-group/",
                                        {
                                            "Ref": Match.string_like_regexp(
                                                "ContainerFactory*"
                                            )
                                        },
                                        "-*",
                                    ],
                                ]
                            },
                        },
                        {
                            "Action": [
                                "s3:GetObject*",
                                "s3:GetBucket*",
                                "s3:List*",
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
                                            "BYOMPipelineRealtimeBuildArtifactsBucket*"
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
                                                        "BYOMPipelineRealtimeBuildArtifactsBucket*"
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
                "PolicyName": Match.string_like_regexp("codebuildRoleDefaultPolicy*"),
                "Roles": [{"Ref": Match.string_like_regexp("codebuildRole*")}],
            },
        )

    def test_codebuild_project(self):
        """Tests for Codebuild project"""
        self.template.has_resource_properties(
            "AWS::CodeBuild::Project",
            {
                "Artifacts": {"Type": "CODEPIPELINE"},
                "Environment": {
                    "ComputeType": "BUILD_GENERAL1_SMALL",
                    "EnvironmentVariables": [
                        {
                            "Name": "AWS_DEFAULT_REGION",
                            "Type": "PLAINTEXT",
                            "Value": {"Ref": "AWS::Region"},
                        },
                        {
                            "Name": "AWS_ACCOUNT_ID",
                            "Type": "PLAINTEXT",
                            "Value": {"Ref": "AWS::AccountId"},
                        },
                        {
                            "Name": "IMAGE_REPO_NAME",
                            "Type": "PLAINTEXT",
                            "Value": {"Ref": "ECRRepoName"},
                        },
                        {
                            "Name": "IMAGE_TAG",
                            "Type": "PLAINTEXT",
                            "Value": {"Ref": "ImageTag"},
                        },
                    ],
                    "Image": "aws/codebuild/standard:6.0",
                    "ImagePullCredentialsType": "CODEBUILD",
                    "PrivilegedMode": True,
                    "Type": "LINUX_CONTAINER",
                },
                "ServiceRole": {
                    "Fn::GetAtt": [Match.string_like_regexp("codebuildRole*"), "Arn"]
                },
                "Source": {
                    "BuildSpec": '{\n  "version": "0.2",\n  "phases": {\n    "pre_build": {\n      "commands": [\n        "echo Logging in to Amazon ECR...",\n        "aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com",\n        "find . -iname \\"serve\\" -exec chmod 777 \\"{}\\" \\\\;",\n        "find . -iname \\"train\\" -exec chmod 777 \\"{}\\" \\\\;"\n      ]\n    },\n    "build": {\n      "commands": [\n        "echo Build started on `date`",\n        "echo Building the Docker image...",\n        "docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .",\n        "docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG"\n      ]\n    },\n    "post_build": {\n      "commands": [\n        "echo Build completed on `date`",\n        "echo Pushing the Docker image...",\n        "docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG"\n      ]\n    }\n  }\n}',
                    "Type": "CODEPIPELINE",
                },
                "Cache": {"Type": "NO_CACHE"},
                "EncryptionKey": "alias/aws/s3",
            },
        )

    def test_codepipeline(self):
        """Tests for Codepipeline"""
        self.template.has_resource_properties(
            "AWS::CodePipeline::Pipeline",
            {
                "RoleArn": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("BYOMPipelineRealtimeBuildRole*"),
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
                                    "S3ObjectKey": {"Ref": "CustomImage"},
                                },
                                "Name": "S3Source",
                                "OutputArtifacts": [
                                    {"Name": "Artifact_Source_S3Source"}
                                ],
                                "RoleArn": {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "BYOMPipelineRealtimeBuildSourceS3SourceCodePipelineActionRole*"
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
                                            "ContainerFactory*"
                                        )
                                    }
                                },
                                "InputArtifacts": [
                                    {"Name": "Artifact_Source_S3Source"}
                                ],
                                "Name": "CodeBuild",
                                "OutputArtifacts": [
                                    {"Name": "Artifact_Build_CodeBuild"}
                                ],
                                "RoleArn": {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "BYOMPipelineRealtimeBuildCodeBuildCodePipelineActionRole*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                "RunOrder": 1,
                            }
                        ],
                        "Name": "Build",
                    },
                ],
                "ArtifactStore": {
                    "Location": {
                        "Ref": Match.string_like_regexp(
                            "BYOMPipelineRealtimeBuildArtifactsBucket*"
                        )
                    },
                    "Type": "S3",
                },
            },
        )

        self.template.has_resource(
            "AWS::CodePipeline::Pipeline",
            {
                "DependsOn": [
                    Match.string_like_regexp(
                        "BYOMPipelineRealtimeBuildRoleDefaultPolicy*"
                    ),
                    Match.string_like_regexp("BYOMPipelineRealtimeBuildRole*"),
                ]
            },
        )

    def test_events_rule(self):
        """Tests for Events Rule"""
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
                                            "BYOMPipelineRealtimeBuild*"
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
                            {
                                "Ref": Match.string_like_regexp(
                                    "BYOMPipelineRealtimeBuild*"
                                )
                            },
                            "/view?region=",
                            {"Ref": "AWS::Region"},
                        ],
                    ]
                }
            },
        )

        self.template.has_output(
            "CustomAlgorithmImageURI",
            {
                "Value": {
                    "Fn::Join": [
                        "",
                        [
                            {"Ref": "AWS::AccountId"},
                            ".dkr.ecr.",
                            {"Ref": "AWS::Region"},
                            ".amazonaws.com/",
                            {"Ref": "ECRRepoName"},
                            ":",
                            {"Ref": "ImageTag"},
                        ],
                    ]
                }
            },
        )
