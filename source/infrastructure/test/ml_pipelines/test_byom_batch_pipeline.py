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
from lib.blueprints.ml_pipelines.byom_batch_pipeline import (
    BYOMBatchStack,
)
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from test.context_helper import get_cdk_context


class TestBatchInference:
    """Tests for byom_batch_pipeline stack"""

    def setup_class(self):
        """Tests setup"""
        self.app = cdk.App(context=get_cdk_context("././cdk.json")["context"])

        solution_id = get_cdk_context_value(self.app, "SolutionId")
        version = get_cdk_context_value(self.app, "Version")

        batch_stack = BYOMBatchStack(
            self.app,
            "BYOMBatchStack",
            description=(
                f"({solution_id}byom-bt) - BYOM Batch Transform pipeline in MLOps Workload Orchestrator. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # create template
        self.template = Template.from_stack(batch_stack)

    def test_template_parameters(self):
        """Tests for templates parameters"""
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
            "CustomAlgorithmsECRRepoArn",
            {
                "Type": "String",
                "AllowedPattern": "(^arn:(aws|aws-cn|aws-us-gov):ecr:(us(-gov)?|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\\d:\\d{12}:repository/.+|^$)",
                "ConstraintDescription": "Please enter valid ECR repo ARN",
                "Description": "The arn of the Amazon ECR repository where custom algorithm image is stored (optional)",
                "MaxLength": 2048,
                "MinLength": 0,
            },
        )

        self.template.has_parameter(
            "KmsKeyArn",
            {
                "Type": "String",
                "AllowedPattern": "(^arn:(aws|aws-cn|aws-us-gov):kms:(us(-gov)?|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\\d:\\d{12}:key/.+|^$)",
                "ConstraintDescription": "Please enter kmsKey ARN",
                "Description": "The KMS ARN to encrypt the output of the batch transform job and instance volume (optional).",
                "MaxLength": 2048,
                "MinLength": 0,
            },
        )

        self.template.has_parameter(
            "ImageUri",
            {
                "Type": "String",
                "Description": "The algorithm image uri (build-in or custom)",
            },
        )

        self.template.has_parameter(
            "ModelName",
            {
                "Type": "String",
                "Description": "An arbitrary name for the model.",
                "MinLength": 1,
            },
        )

        self.template.has_parameter(
            "ModelArtifactLocation",
            {
                "Type": "String",
                "Description": "Path to model artifact inside assets bucket.",
            },
        )

        self.template.has_parameter(
            "InferenceInstance",
            {
                "Type": "String",
                "AllowedPattern": "^[a-zA-Z0-9_.+-]+\\.[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
                "Description": "Inference instance that inference requests will be running on. E.g., ml.m5.large",
                "MinLength": 7,
            },
        )

        self.template.has_parameter(
            "BatchInputBucket",
            {
                "Type": "String",
                "Description": "Bucket name where the data input of the bact transform is stored.",
                "MinLength": 3,
            },
        )

        self.template.has_parameter(
            "BatchInferenceData",
            {
                "Type": "String",
                "Description": "S3 bucket path (including bucket name) to batch inference data file.",
            },
        )

        self.template.has_parameter(
            "BatchOutputLocation",
            {
                "Type": "String",
                "Description": "S3 path (including bucket name) to store the results of the batch job.",
            },
        )

        self.template.has_parameter(
            "ModelPackageGroupName",
            {
                "Type": "String",
                "Description": "SageMaker model package group name",
                "MinLength": 0,
            },
        )

        self.template.has_parameter(
            "ModelPackageName",
            {
                "Type": "String",
                "AllowedPattern": "(^arn:aws[a-z\\-]*:sagemaker:[a-z0-9\\-]*:[0-9]{12}:model-package/.*|^$)",
                "Description": "The model name (version arn) in SageMaker's model package name group",
            },
        )

    def test_template_conditions(self):
        """Tests for templates conditions"""
        self.template.has_condition(
            "CustomECRRepoProvided",
            {"Fn::Not": [{"Fn::Equals": [{"Ref": "CustomAlgorithmsECRRepoArn"}, ""]}]},
        )

        self.template.has_condition(
            "KmsKeyProvided",
            {"Fn::Not": [{"Fn::Equals": [{"Ref": "KmsKeyArn"}, ""]}]},
        )

        self.template.has_condition(
            "ModelRegistryProvided",
            {"Fn::Not": [{"Fn::Equals": [{"Ref": "ModelPackageName"}, ""]}]},
        )

    def test_sagemaker_layer(self):
        """Test for Lambda SageMaker layer"""
        self.template.has_resource_properties(
            "AWS::Lambda::LayerVersion",
            {
                "Content": {
                    "S3Bucket": {"Ref": "BlueprintBucket"},
                    "S3Key": "blueprints/lambdas/sagemaker_layer.zip",
                },
                "CompatibleRuntimes": ["python3.9", "python3.10"],
            },
        )

    def test_ecr_policy(self):
        """Test for MLOpd ECR policy"""
        self.template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            {
                                "Action": [
                                    "ecr:BatchCheckLayerAvailability",
                                    "ecr:GetDownloadUrlForLayer",
                                    "ecr:DescribeRepositories",
                                    "ecr:DescribeImages",
                                    "ecr:BatchGetImage",
                                ],
                                "Effect": "Allow",
                                "Resource": {"Ref": "CustomAlgorithmsECRRepoArn"},
                            },
                            {
                                "Action": "ecr:GetAuthorizationToken",
                                "Effect": "Allow",
                                "Resource": "*",
                            },
                        ]
                    ),
                    "Version": "2012-10-17",
                },
                "PolicyName": Match.string_like_regexp("MLOpsECRPolicy*"),
                "Roles": [
                    {"Ref": Match.string_like_regexp("MLOpsSagemakerBatchRole*")}
                ],
            },
        )

        self.template.has_resource(
            "AWS::IAM::Policy",
            {
                "Metadata": {
                    "cfn_nag": {
                        "rules_to_suppress": [
                            {
                                "id": "W12",
                                "reason": "This ECR Policy (ecr:GetAuthorizationToken) can not have a restricted resource.",
                            }
                        ]
                    }
                },
                "Condition": "CustomECRRepoProvided",
            },
        )

    def test_kms_policy(self):
        """Tests for MLOps KMS key policy"""
        self.template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "kms:Encrypt",
                                "kms:Decrypt",
                                "kms:CreateGrant",
                                "kms:ReEncrypt*",
                                "kms:GenerateDataKey*",
                                "kms:DescribeKey",
                            ],
                            "Effect": "Allow",
                            "Resource": {"Ref": "KmsKeyArn"},
                        }
                    ],
                    "Version": "2012-10-17",
                },
                "PolicyName": Match.string_like_regexp("MLOpsKmsPolicy*"),
                "Roles": [
                    {"Ref": Match.string_like_regexp("MLOpsSagemakerBatchRole*")}
                ],
            },
        )

        self.template.has_resource("AWS::IAM::Policy", {"Condition": "KmsKeyProvided"})

    def test_model_registry_policy(self):
        """Tests for SageMaker Model Registry Policy"""
        self.template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            {
                                "Action": [
                                    "sagemaker:DescribeModelPackageGroup",
                                    "sagemaker:DescribeModelPackage",
                                    "sagemaker:ListModelPackages",
                                    "sagemaker:UpdateModelPackage",
                                    "sagemaker:CreateModel",
                                ],
                                "Effect": "Allow",
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
                                                ":model-package-group/",
                                                {"Ref": "ModelPackageGroupName"},
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
                                                ":model-package/",
                                                {"Ref": "ModelPackageGroupName"},
                                                "/*",
                                            ],
                                        ]
                                    },
                                ],
                            }
                        ]
                    ),
                    "Version": "2012-10-17",
                },
            },
        )

        self.template.has_resource(
            "AWS::IAM::Policy", {"Condition": "ModelRegistryProvided"}
        )

    def test_sagemaker_model(self):
        """Tests SageMaker Model probs"""
        self.template.has_resource_properties(
            "AWS::SageMaker::Model",
            {
                "ExecutionRoleArn": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("MLOpsSagemakerBatchRole*"),
                        "Arn",
                    ]
                },
                "PrimaryContainer": {
                    "Image": {
                        "Fn::If": [
                            "ModelRegistryProvided",
                            {"Ref": "AWS::NoValue"},
                            {"Ref": "ImageUri"},
                        ]
                    },
                    "ModelDataUrl": {
                        "Fn::If": [
                            "ModelRegistryProvided",
                            {"Ref": "AWS::NoValue"},
                            {
                                "Fn::Join": [
                                    "",
                                    [
                                        "s3://",
                                        {"Ref": "AssetsBucket"},
                                        "/",
                                        {"Ref": "ModelArtifactLocation"},
                                    ],
                                ]
                            },
                        ]
                    },
                    "ModelPackageName": {
                        "Fn::If": [
                            "ModelRegistryProvided",
                            {"Ref": "ModelPackageName"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                },
                "Tags": [{"Key": "model_name", "Value": {"Ref": "ModelName"}}],
            },
        )

        self.template.has_resource(
            "AWS::SageMaker::Model",
            {
                "DependsOn": [
                    Match.string_like_regexp("MLOpsSagemakerBatchRoleDefaultPolicy*"),
                    Match.string_like_regexp("MLOpsSagemakerBatchRole*"),
                ]
            },
        )

    def test_batch_lambda(self):
        """Tests for Batch Lambda function"""
        self.template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Code": {
                    "S3Bucket": {"Ref": "BlueprintBucket"},
                    "S3Key": "blueprints/lambdas/batch_transform.zip",
                },
                "Role": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("batchtransformlambdarole*"),
                        "Arn",
                    ]
                },
                "Environment": {
                    "Variables": {
                        "model_name": {
                            "Fn::GetAtt": ["MLOpsSagemakerModel", "ModelName"]
                        },
                        "inference_instance": {"Ref": "InferenceInstance"},
                        "assets_bucket": {"Ref": "AssetsBucket"},
                        "batch_inference_data": {"Ref": "BatchInferenceData"},
                        "batch_job_output_location": {"Ref": "BatchOutputLocation"},
                        "kms_key_arn": {
                            "Fn::If": [
                                "KmsKeyProvided",
                                {"Ref": "KmsKeyArn"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "LOG_LEVEL": "INFO",
                    }
                },
                "Handler": "main.handler",
                "Layers": [{"Ref": Match.string_like_regexp("sagemakerlayer*")}],
                "Runtime": "python3.10",
            },
        )

    def test_invoke_lambda(self):
        """Tests for Invoke Lambda function"""
        self.template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Code": {
                    "S3Bucket": {"Ref": "BlueprintBucket"},
                    "S3Key": "blueprints/lambdas/invoke_lambda_custom_resource.zip",
                },
                "Role": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("InvokeBatchLambdaServiceRole*"),
                        "Arn",
                    ]
                },
                "Handler": "index.handler",
                "Runtime": "python3.10",
                "Timeout": 300,
            },
        )

    def test_custom_resource_invoke_lambda(self):
        """Tests for Custom resource to invoke Lambda function"""
        self.template.has_resource_properties(
            "Custom::InvokeLambda",
            {
                "ServiceToken": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("InvokeBatchLambda*"),
                        "Arn",
                    ]
                },
                "function_name": {
                    "Ref": Match.string_like_regexp("BatchTranformLambda*")
                },
                "message": {
                    "Fn::Join": [
                        "",
                        [
                            "Invoking lambda function: ",
                            {"Ref": Match.string_like_regexp("BatchTranformLambda*")},
                        ],
                    ]
                },
                "Resource": "InvokeLambda",
                "sagemaker_model_name": {
                    "Fn::GetAtt": ["MLOpsSagemakerModel", "ModelName"]
                },
                "model_name": {"Ref": "ModelName"},
                "inference_instance": {"Ref": "InferenceInstance"},
                "algorithm_image": {"Ref": "ImageUri"},
                "model_artifact": {"Ref": "ModelArtifactLocation"},
                "assets_bucket": {"Ref": "AssetsBucket"},
                "batch_inference_data": {"Ref": "BatchInferenceData"},
                "batch_job_output_location": {"Ref": "BatchOutputLocation"},
                "custom_algorithms_ecr_arn": {"Ref": "CustomAlgorithmsECRRepoArn"},
                "kms_key_arn": {"Ref": "KmsKeyArn"},
            },
        )

        self.template.has_resource(
            "Custom::InvokeLambda",
            {
                "DependsOn": [Match.string_like_regexp("BatchTranformLambda*")],
                "UpdateReplacePolicy": "Delete",
                "DeletionPolicy": "Delete",
            },
        )

    def test_template_outputs(self):
        """Tests for templates outputs"""
        self.template.has_output(
            "SageMakerModelName",
            {"Value": {"Fn::GetAtt": ["MLOpsSagemakerModel", "ModelName"]}},
        )

        self.template.has_output(
            "BatchTransformJobName",
            {
                "Description": "The name of the SageMaker batch transform job",
                "Value": {
                    "Fn::Join": [
                        "",
                        [
                            {"Fn::GetAtt": ["MLOpsSagemakerModel", "ModelName"]},
                            "-batch-transform-*",
                        ],
                    ]
                },
            },
        )

        self.template.has_output(
            "BatchTransformOutputLocation",
            {
                "Description": "Output location of the batch transform. Our will be saved under the job name",
                "Value": {
                    "Fn::Join": [
                        "",
                        [
                            "https://s3.console.aws.amazon.com/s3/buckets/",
                            {"Ref": "BatchOutputLocation"},
                            "/",
                        ],
                    ]
                },
            },
        )
