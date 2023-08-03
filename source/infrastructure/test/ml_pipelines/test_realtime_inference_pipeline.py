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
from lib.blueprints.aspects.aws_sdk_config_aspect import AwsSDKConfigAspect
from lib.blueprints.aspects.protobuf_config_aspect import ProtobufConfigAspect
from lib.blueprints.ml_pipelines.realtime_inference_pipeline import (
    BYOMRealtimePipelineStack,
)
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from test.context_helper import get_cdk_context


class TestRealtimeInference:
    """Tests for realtime_inference_pipeline stack"""

    def setup_class(self):
        """Tests setup"""
        app = cdk.App(context=get_cdk_context("././cdk.json")["context"])

        solution_id = get_cdk_context_value(app, "SolutionId")
        version = get_cdk_context_value(app, "Version")

        realtime_stack = BYOMRealtimePipelineStack(
            app,
            "BYOMRealtimePipelineStack",
            description=(
                f"({solution_id}byom-rip) - BYOM Realtime Inference Pipeline. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # add AWS_SDK_USER_AGENT env variable to Lambda functions
        cdk.Aspects.of(realtime_stack).add(
            AwsSDKConfigAspect(app, "SDKUserAgentSingle", solution_id, version)
        )

        # add PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to handle protobuf breaking changes
        cdk.Aspects.of(realtime_stack).add(
            ProtobufConfigAspect(app, "ProtobufConfigSingle")
        )

        # create template
        self.template = Template.from_stack(realtime_stack)

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
            "BlueprintBucket",
            {
                "Type": "String",
                "Description": "Bucket name for blueprints of different types of ML Pipelines.",
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
            "DataCaptureLocation",
            {
                "Type": "String",
                "Description": "S3 path (including bucket name) to store captured data from the Sagemaker endpoint.",
                "MinLength": 3,
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

        self.template.has_parameter(
            "EndpointName",
            {
                "Type": "String",
                "Description": "The name of the AWS SageMaker's endpoint",
                "MinLength": 0,
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

        self.template.has_condition(
            "EndpointNameProvided",
            {"Fn::Not": [{"Fn::Equals": [{"Ref": "EndpointName"}, ""]}]},
        )

    def test_inference_lambda_policy(self):
        """Tests for Inference Lambda policy"""
        self.template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "xray:PutTraceSegments",
                                "xray:PutTelemetryRecords",
                            ],
                            "Effect": "Allow",
                            "Resource": "*",
                        },
                        {
                            "Action": "sagemaker:InvokeEndpoint",
                            "Effect": "Allow",
                            "Resource": {"Ref": "MLOpsSagemakerEndpoint"},
                        },
                    ],
                    "Version": "2012-10-17",
                },
                "PolicyName": Match.string_like_regexp(
                    "BYOMInferenceLambdaFunctionServiceRoleDefaultPolicy*"
                ),
            },
        )

    def test_inference_lambda_props(self):
        """Test Inference Lambda props"""
        self.template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Code": {
                    "S3Bucket": {"Ref": "BlueprintBucket"},
                    "S3Key": "blueprints/lambdas/inference.zip",
                },
                "Role": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp(
                            "BYOMInferenceLambdaFunctionServiceRole*"
                        ),
                        "Arn",
                    ]
                },
                "Environment": {
                    "Variables": {
                        "SAGEMAKER_ENDPOINT_NAME": {
                            "Fn::GetAtt": ["MLOpsSagemakerEndpoint", "EndpointName"]
                        },
                        "AWS_SDK_USER_AGENT": '{"user_agent_extra": "AwsSolution/SO0136/%%VERSION%%"}',
                        "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION": "python",
                    }
                },
                "Handler": "main.handler",
                "Runtime": "python3.10",
                "Timeout": 300,
                "TracingConfig": {"Mode": "Active"},
            },
        )

        self.template.has_resource(
            "AWS::Lambda::Function",
            {
                "DependsOn": [
                    Match.string_like_regexp(
                        "BYOMInferenceLambdaFunctionServiceRoleDefaultPolicy*"
                    ),
                    Match.string_like_regexp("BYOMInferenceLambdaFunctionServiceRole*"),
                ],
                "Metadata": {
                    "cfn_nag": {
                        "rules_to_suppress": [
                            {
                                "id": "W89",
                                "reason": "The lambda function does not need to be attached to a vpc.",
                            },
                            {
                                "id": "W58",
                                "reason": "The lambda functions role already has permissions to write cloudwatch logs",
                            },
                            {
                                "id": "W92",
                                "reason": "The lambda function does need to define ReservedConcurrentExecutions",
                            },
                        ]
                    }
                },
            },
        )

    def test_inference_api_gateway(self):
        """Tests for Inference APIs"""
        self.template.has_resource_properties(
            "AWS::ApiGateway::RestApi",
            {
                "EndpointConfiguration": {"Types": ["EDGE"]},
                "Name": {"Fn::Join": ["", [{"Ref": "AWS::StackName"}, "-inference"]]},
            },
        )

        self.template.has_resource_properties(
            "AWS::ApiGateway::Deployment",
            {
                "RestApiId": {
                    "Ref": Match.string_like_regexp("BYOMInferenceLambdaRestApi*")
                },
                "Description": "Automatically created by the RestApi construct",
            },
        )

        self.template.has_resource(
            "AWS::ApiGateway::Deployment",
            {
                "DependsOn": [
                    Match.string_like_regexp(
                        "BYOMInferenceLambdaRestApiinferencePOST*"
                    ),
                    Match.string_like_regexp("BYOMInferenceLambdaRestApiinference*"),
                ]
            },
        )

        self.template.has_resource_properties(
            "AWS::ApiGateway::Stage",
            {
                "RestApiId": {
                    "Ref": Match.string_like_regexp("BYOMInferenceLambdaRestApi*")
                },
                "AccessLogSetting": {
                    "DestinationArn": {
                        "Fn::GetAtt": [
                            Match.string_like_regexp("BYOMInferenceApiAccessLogGroup*"),
                            "Arn",
                        ]
                    },
                    "Format": '{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","user":"$context.identity.user","caller":"$context.identity.caller","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","resourcePath":"$context.resourcePath","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength"}',
                },
                "DeploymentId": {
                    "Ref": Match.string_like_regexp(
                        "BYOMInferenceLambdaRestApiDeployment*"
                    )
                },
                "MethodSettings": [
                    {
                        "DataTraceEnabled": False,
                        "HttpMethod": "*",
                        "LoggingLevel": "INFO",
                        "ResourcePath": "/*",
                    }
                ],
                "StageName": "prod",
                "TracingEnabled": True,
            },
        )

        self.template.has_resource_properties(
            "AWS::ApiGateway::Resource",
            {
                "ParentId": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("BYOMInferenceLambdaRestApi*"),
                        "RootResourceId",
                    ]
                },
                "PathPart": "inference",
                "RestApiId": {
                    "Ref": Match.string_like_regexp("BYOMInferenceLambdaRestApi*")
                },
            },
        )

        self.template.has_resource_properties(
            "AWS::Lambda::Permission",
            {
                "Action": "lambda:InvokeFunction",
                "FunctionName": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("BYOMInferenceLambdaFunction*"),
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
                                    "BYOMInferenceLambdaRestApi*"
                                )
                            },
                            "/",
                            {
                                "Ref": Match.string_like_regexp(
                                    "BYOMInferenceLambdaRestApiDeploymentStageprod*"
                                )
                            },
                            "/POST/inference",
                        ],
                    ]
                },
            },
        )

        self.template.has_resource_properties(
            "AWS::Lambda::Permission",
            {
                "Action": "lambda:InvokeFunction",
                "FunctionName": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("BYOMInferenceLambdaFunction*"),
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
                                    "BYOMInferenceLambdaRestApi*"
                                )
                            },
                            "/test-invoke-stage/POST/inference",
                        ],
                    ]
                },
            },
        )

        self.template.has_resource_properties(
            "AWS::ApiGateway::Method",
            {
                "HttpMethod": "POST",
                "ResourceId": {
                    "Ref": Match.string_like_regexp(
                        "BYOMInferenceLambdaRestApiinference*"
                    )
                },
                "RestApiId": {
                    "Ref": Match.string_like_regexp("BYOMInferenceLambdaRestApi*")
                },
                "AuthorizationType": "AWS_IAM",
                "Integration": {
                    "IntegrationHttpMethod": "POST",
                    "Type": "AWS_PROXY",
                    "Uri": {
                        "Fn::Join": [
                            "",
                            [
                                "arn:",
                                {"Ref": "AWS::Partition"},
                                ":apigateway:",
                                {"Ref": "AWS::Region"},
                                ":lambda:path/2015-03-31/functions/",
                                {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "BYOMInferenceLambdaFunction*"
                                        ),
                                        "Arn",
                                    ]
                                },
                                "/invocations",
                            ],
                        ]
                    },
                },
            },
        )

        self.template.has_resource_properties(
            "AWS::ApiGateway::Account",
            {
                "CloudWatchRoleArn": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp(
                            "BYOMInferenceLambdaRestApiCloudWatchRole*"
                        ),
                        "Arn",
                    ]
                }
            },
        )

        self.template.has_resource(
            "AWS::ApiGateway::Account",
            {"DependsOn": [Match.string_like_regexp("BYOMInferenceLambdaRestApi*")]},
        )

    def test_api_cloudwatch_role(self):
        """Test for Inference APIs role"""
        self.template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {"Service": "apigateway.amazonaws.com"},
                        }
                    ],
                    "Version": "2012-10-17",
                },
                "Policies": [
                    {
                        "PolicyDocument": {
                            "Statement": [
                                {
                                    "Action": [
                                        "logs:CreateLogGroup",
                                        "logs:CreateLogStream",
                                        "logs:DescribeLogGroups",
                                        "logs:DescribeLogStreams",
                                        "logs:PutLogEvents",
                                        "logs:GetLogEvents",
                                        "logs:FilterLogEvents",
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
                                                ":*",
                                            ],
                                        ]
                                    },
                                }
                            ],
                            "Version": "2012-10-17",
                        },
                    }
                ],
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
            },
        )

        self.template.has_resource("AWS::IAM::Policy", {"Condition": "KmsKeyProvided"})

    def test_model_registry_policy(self):
        """Tests for SageMaker Model Registry Policy"""
        self.template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_equals(
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
                        Match.string_like_regexp("MLOpsRealtimeSagemakerRole*"),
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
                    Match.string_like_regexp(
                        "MLOpsRealtimeSagemakerRoleDefaultPolicy*"
                    ),
                    Match.string_like_regexp("MLOpsRealtimeSagemakerRole*"),
                ]
            },
        )

    def test_sagemaker_endpoint_config(self):
        """ "Tests for SageMaker Endpoint Config"""
        self.template.has_resource_properties(
            "AWS::SageMaker::EndpointConfig",
            {
                "ProductionVariants": [
                    {
                        "InitialInstanceCount": 1,
                        "InitialVariantWeight": 1,
                        "InstanceType": {"Ref": "InferenceInstance"},
                        "ModelName": {
                            "Fn::GetAtt": ["MLOpsSagemakerModel", "ModelName"]
                        },
                        "VariantName": "AllTraffic",
                    }
                ],
                "DataCaptureConfig": {
                    "CaptureContentTypeHeader": {"CsvContentTypes": ["text/csv"]},
                    "CaptureOptions": [
                        {"CaptureMode": "Output"},
                        {"CaptureMode": "Input"},
                    ],
                    "DestinationS3Uri": {
                        "Fn::Join": ["", ["s3://", {"Ref": "DataCaptureLocation"}]]
                    },
                    "EnableCapture": True,
                    "InitialSamplingPercentage": 100,
                    "KmsKeyId": {
                        "Fn::If": [
                            "KmsKeyProvided",
                            {"Ref": "KmsKeyArn"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                },
                "KmsKeyId": {
                    "Fn::If": [
                        "KmsKeyProvided",
                        {"Ref": "KmsKeyArn"},
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Tags": [
                    {
                        "Key": "endpoint-config-name",
                        "Value": {
                            "Fn::Join": ["", [{"Ref": "ModelName"}, "-endpoint-config"]]
                        },
                    }
                ],
            },
        )

        self.template.has_resource(
            "AWS::SageMaker::EndpointConfig",
            {"DependsOn": ["MLOpsSagemakerModel"]},
        )

    def test_sagemaker_endpoint(self):
        """Tests for SageMaker Endpoint"""
        self.template.has_resource_properties(
            "AWS::SageMaker::Endpoint",
            {
                "EndpointConfigName": {
                    "Fn::GetAtt": ["MLOpsSagemakerEndpointConfig", "EndpointConfigName"]
                },
                "EndpointName": {
                    "Fn::If": [
                        "EndpointNameProvided",
                        {"Ref": "EndpointName"},
                        {"Ref": "AWS::NoValue"},
                    ]
                },
                "Tags": [
                    {
                        "Key": "endpoint-name",
                        "Value": {
                            "Fn::Join": ["", [{"Ref": "ModelName"}, "-endpoint"]]
                        },
                    }
                ],
            },
        )

        self.template.has_resource(
            "AWS::SageMaker::Endpoint",
            {"DependsOn": ["MLOpsSagemakerEndpointConfig"]},
        )

    def test_template_outputs(self):
        """Tests for templates outputs"""
        self.template.has_output(
            "BYOMInferenceLambdaRestApiEndpoint1F9BE989",
            {
                "Value": {
                    "Fn::Join": [
                        "",
                        [
                            "https://",
                            {
                                "Ref": Match.string_like_regexp(
                                    "BYOMInferenceLambdaRestApi*"
                                )
                            },
                            ".execute-api.",
                            {"Ref": "AWS::Region"},
                            ".",
                            {"Ref": "AWS::URLSuffix"},
                            "/",
                            {
                                "Ref": Match.string_like_regexp(
                                    "BYOMInferenceLambdaRestApiDeploymentStageprod*"
                                )
                            },
                            "/",
                        ],
                    ]
                }
            },
        )

        self.template.has_output(
            "SageMakerModelName",
            {"Value": {"Fn::GetAtt": ["MLOpsSagemakerModel", "ModelName"]}},
        )

        self.template.has_output(
            "SageMakerEndpointConfigName",
            {
                "Value": {
                    "Fn::GetAtt": ["MLOpsSagemakerEndpointConfig", "EndpointConfigName"]
                }
            },
        )

        self.template.has_output(
            "SageMakerEndpointName",
            {"Value": {"Fn::GetAtt": ["MLOpsSagemakerEndpoint", "EndpointName"]}},
        )

        self.template.has_output(
            "EndpointDataCaptureLocation",
            {
                "Description": "Endpoint data capture location (to be used by Model Monitor)",
                "Value": {
                    "Fn::Join": [
                        "",
                        [
                            "https://s3.console.aws.amazon.com/s3/buckets/",
                            {"Ref": "DataCaptureLocation"},
                            "/",
                        ],
                    ]
                },
            },
        )
