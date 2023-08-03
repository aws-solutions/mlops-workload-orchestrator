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
from lib.blueprints.ml_pipelines.model_monitor import (
    ModelMonitorStack,
)
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from test.context_helper import get_cdk_context


class TestModelMonitor:
    """Tests for model_monitor stack"""

    def setup_class(self):
        """Tests setup"""
        app = cdk.App(context=get_cdk_context("././cdk.json")["context"])

        solution_id = get_cdk_context_value(app, "SolutionId")
        version = get_cdk_context_value(app, "Version")

        # data quality stack
        data_quality_monitor_stack = ModelMonitorStack(
            app,
            "DataQualityModelMonitorStack",
            monitoring_type="DataQuality",
            description=(
                f"({solution_id}byom-dqmm) - DataQuality Model Monitor pipeline. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )
        # model quality monitor
        model_quality_monitor_stack = ModelMonitorStack(
            app,
            "ModelQualityModelMonitorStack",
            monitoring_type="ModelQuality",
            description=(
                f"({solution_id}byom-mqmm) - ModelQuality Model Monitor pipeline. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # model bias stack
        model_bias_monitor_stack = ModelMonitorStack(
            app,
            "ModelBiasModelMonitorStack",
            monitoring_type="ModelBias",
            description=(
                f"({solution_id}byom-mqmb) - ModelBias Model Monitor pipeline. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # model explainability stack
        model_explainability_monitor_stack = ModelMonitorStack(
            app,
            "ModelExplainabilityModelMonitorStack",
            monitoring_type="ModelExplainability",
            description=(
                f"({solution_id}byom-mqme) - ModelExplainability Model Monitor pipeline. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # create templates
        self.data_quality_template = Template.from_stack(data_quality_monitor_stack)
        self.model_quality_template = Template.from_stack(model_quality_monitor_stack)
        self.model_bias_template = Template.from_stack(model_bias_monitor_stack)
        self.model_explainability_template = Template.from_stack(
            model_explainability_monitor_stack
        )

        # all templates
        self.templates = [
            self.data_quality_template,
            self.model_quality_template,
            self.model_bias_template,
            self.model_explainability_template,
        ]

    def test_template_parameters(self):
        """Tests for templates parameters"""
        for template in self.templates:
            template.has_parameter(
                "BlueprintBucket",
                {
                    "Type": "String",
                    "Description": "Bucket name for blueprints of different types of ML Pipelines.",
                    "MinLength": 3,
                },
            )
            template.has_parameter(
                "AssetsBucket",
                {
                    "Type": "String",
                    "Description": "Bucket name where the model and baselines data are stored.",
                    "MinLength": 3,
                },
            )

            template.has_parameter(
                "EndpointName",
                {
                    "Type": "String",
                    "Description": "The name of the AWS SageMaker's endpoint",
                    "MinLength": 1,
                },
            )

            template.has_parameter(
                "BaselineJobOutputLocation",
                {
                    "Type": "String",
                    "Description": "S3 path (including bucket name) to store the Data Baseline Job's output.",
                    "MinLength": 3,
                },
            )

            template.has_parameter(
                "BaselineData",
                {
                    "Type": "String",
                    "Description": "Location of the Baseline data in Assets S3 Bucket.",
                },
            )

            template.has_parameter(
                "InstanceType",
                {
                    "Type": "String",
                    "AllowedPattern": "^[a-zA-Z0-9_.+-]+\\.[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
                    "Description": "EC2 instance type that model monitoring jobs will be running on. E.g., ml.m5.large",
                    "MinLength": 7,
                },
            )

            template.has_parameter(
                "JobInstanceCount",
                {
                    "Type": "Number",
                    "Default": "1",
                    "Description": "Instance count used by the job. For example, 1",
                },
            )

            template.has_parameter(
                "InstanceVolumeSize",
                {
                    "Type": "Number",
                    "Description": "Instance volume size used by the job. E.g., 20",
                },
            )

            template.has_parameter(
                "BaselineMaxRuntimeSeconds",
                {
                    "Type": "String",
                    "Default": "",
                    "Description": "Optional Maximum runtime in seconds the baseline job is allowed to run. E.g., 3600",
                },
            )

            template.has_parameter(
                "MonitorMaxRuntimeSeconds",
                {
                    "Type": "Number",
                    "Default": "1800",
                    "Description": " Required Maximum runtime in seconds the job is allowed to run the ModelQuality baseline job. For data quality and model explainability, this can be up to 3600 seconds for an hourly schedule. For model bias and model quality hourly schedules, this can be up to 1800 seconds.",
                    "MaxValue": 86400,
                    "MinValue": 1,
                },
            )

            template.has_parameter(
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

            template.has_parameter(
                "BaselineJobName",
                {
                    "Type": "String",
                    "Description": "Unique name of the data baseline job",
                    "MaxLength": 63,
                    "MinLength": 3,
                },
            )

            template.has_parameter(
                "MonitoringScheduleName",
                {
                    "Type": "String",
                    "Description": "Unique name of the monitoring schedule job",
                    "MaxLength": 63,
                    "MinLength": 3,
                },
            )

            template.has_parameter(
                "DataCaptureBucket",
                {
                    "Type": "String",
                    "Description": "Bucket name where the data captured from SageMaker endpoint will be stored.",
                    "MinLength": 3,
                },
            )

            template.has_parameter(
                "BaselineOutputBucket",
                {
                    "Type": "String",
                    "Description": "Bucket name where the output of the baseline job will be stored.",
                    "MinLength": 3,
                },
            )

            template.has_parameter(
                "DataCaptureLocation",
                {
                    "Type": "String",
                    "Description": "S3 path (including bucket name) to store captured data from the Sagemaker endpoint.",
                    "MinLength": 3,
                },
            )

            template.has_parameter(
                "MonitoringOutputLocation",
                {
                    "Type": "String",
                    "Description": "S3 path (including bucket name) to store the output of the Monitoring Schedule.",
                    "MinLength": 3,
                },
            )

            template.has_parameter(
                "ScheduleExpression",
                {
                    "Type": "String",
                    "AllowedPattern": "^cron(\\S+\\s){5}\\S+$",
                    "Description": "cron expression to run the monitoring schedule. E.g., cron(0 * ? * * *), cron(0 0 ? * * *), etc.",
                },
            )

            template.has_parameter(
                "ImageUri",
                {
                    "Type": "String",
                    "Description": "The algorithm image uri (build-in or custom)",
                },
            )

    def test_template_conditions(self):
        """Tests for templates conditions"""
        for template in self.templates:
            template.has_condition(
                "KmsKeyProvided",
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "KmsKeyArn"}, ""]}]},
            )

    def test_sagemaker_layer(self):
        """Test for Lambda SageMaker layer"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::Lambda::LayerVersion",
                {
                    "Content": {
                        "S3Bucket": {"Ref": "BlueprintBucket"},
                        "S3Key": "blueprints/lambdas/sagemaker_layer.zip",
                    },
                    "CompatibleRuntimes": ["python3.9", "python3.10"],
                },
            )

    def test_training_kms_policy(self):
        """Tests for KMS policy"""
        for template in self.templates:
            template.has_resource_properties(
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
                                "Resource": {
                                    "Fn::If": [
                                        "KmsKeyProvided",
                                        {"Ref": "KmsKeyArn"},
                                        {"Ref": "AWS::NoValue"},
                                    ]
                                },
                            }
                        ],
                        "Version": "2012-10-17",
                    },
                    "PolicyName": Match.string_like_regexp("BaselineKmsPolicy*"),
                    "Roles": [
                        {
                            "Ref": Match.string_like_regexp(
                                "createbaselinesagemakerrole*"
                            )
                        }
                    ],
                },
            )

            template.has_resource("AWS::IAM::Policy", {"Condition": "KmsKeyProvided"})

    def test_create_baseline_policy(self):
        """Tests for Create Baseline Job policy"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::IAM::Policy",
                {
                    "PolicyDocument": {
                        "Statement": Match.array_with(
                            [
                                {
                                    "Action": "sts:AssumeRole",
                                    "Effect": "Allow",
                                    "Resource": {
                                        "Fn::GetAtt": [
                                            "createbaselinesagemakerroleEF4D9DF2",
                                            "Arn",
                                        ]
                                    },
                                },
                                {
                                    "Action": [
                                        "sagemaker:CreateProcessingJob",
                                        "sagemaker:DescribeProcessingJob",
                                        "sagemaker:StopProcessingJob",
                                    ],
                                    "Effect": "Allow",
                                    "Resource": {
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
                                                ":processing-job/",
                                                {"Ref": "BaselineJobName"},
                                            ],
                                        ]
                                    },
                                },
                                {
                                    "Action": [
                                        "sagemaker:AddTags",
                                        "sagemaker:DeleteTags",
                                    ],
                                    "Effect": "Allow",
                                    "Resource": {
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
                                                ":*",
                                            ],
                                        ]
                                    },
                                },
                                {
                                    "Action": ["s3:GetObject", "s3:ListBucket"],
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
                                                    {"Ref": "BaselineOutputBucket"},
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
                                                    {"Ref": "BaselineOutputBucket"},
                                                    "/*",
                                                ],
                                            ]
                                        },
                                    ],
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
                                                {"Ref": "BaselineJobOutputLocation"},
                                                "/*",
                                            ],
                                        ]
                                    },
                                },
                            ]
                        ),
                        "Version": "2012-10-17",
                    },
                    "PolicyName": Match.string_like_regexp(
                        "createbaselinesagemakerroleDefaultPolicy*"
                    ),
                    "Roles": [
                        {
                            "Ref": Match.string_like_regexp(
                                "createbaselinesagemakerrole*"
                            )
                        }
                    ],
                },
            )

    def test_create_baseline_lambda_policy(self):
        """Tests for Create baseline Lambda policy"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::IAM::Policy",
                {
                    "PolicyDocument": {
                        "Statement": Match.array_with(
                            [
                                {
                                    "Action": "iam:PassRole",
                                    "Effect": "Allow",
                                    "Resource": {
                                        "Fn::GetAtt": [
                                            Match.string_like_regexp(
                                                "createbaselinesagemakerrole*"
                                            ),
                                            "Arn",
                                        ]
                                    },
                                },
                                {
                                    "Action": [
                                        "sagemaker:CreateProcessingJob",
                                        "sagemaker:DescribeProcessingJob",
                                        "sagemaker:StopProcessingJob",
                                    ],
                                    "Effect": "Allow",
                                    "Resource": {
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
                                                ":processing-job/",
                                                {"Ref": "BaselineJobName"},
                                            ],
                                        ]
                                    },
                                },
                                {
                                    "Action": [
                                        "sagemaker:AddTags",
                                        "sagemaker:DeleteTags",
                                    ],
                                    "Effect": "Allow",
                                    "Resource": {
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
                                                ":*",
                                            ],
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
                                                {"Ref": "BaselineJobOutputLocation"},
                                                "/*",
                                            ],
                                        ]
                                    },
                                },
                                {
                                    "Action": ["s3:GetObject", "s3:ListBucket"],
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
                                                    {"Ref": "BaselineOutputBucket"},
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
                                                    {"Ref": "BaselineOutputBucket"},
                                                    "/*",
                                                ],
                                            ]
                                        },
                                    ],
                                },
                                {
                                    "Action": [
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
                                                    ":log-group:/aws/lambda/*",
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
                                                    ":log-group:*:log-stream:*",
                                                ],
                                            ]
                                        },
                                    ],
                                },
                                {
                                    "Action": "logs:CreateLogGroup",
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
                                },
                            ]
                        ),
                        "Version": "2012-10-17",
                    },
                    "PolicyName": Match.string_like_regexp(
                        "createbaselinejoblambdaroleDefaultPolicy*"
                    ),
                    "Roles": [
                        {
                            "Ref": Match.string_like_regexp(
                                "createbaselinejoblambdarole*"
                            )
                        }
                    ],
                },
            )

    def test_baseline_lambda(self):
        """Tests for Training Lambda function"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::Lambda::Function",
                {
                    "Code": {
                        "S3Bucket": {"Ref": "BlueprintBucket"},
                        "S3Key": "blueprints/lambdas/create_baseline_job.zip",
                    },
                    "Role": {
                        "Fn::GetAtt": ["createbaselinejoblambdaroleA17644CE", "Arn"]
                    },
                    "Environment": {
                        "Variables": {
                            "MONITORING_TYPE": Match.string_like_regexp(
                                "(DataQuality|ModelQuality|ModelBias|ModelExplainability)"
                            ),
                            "BASELINE_JOB_NAME": {"Ref": "BaselineJobName"},
                            "ASSETS_BUCKET": {"Ref": "AssetsBucket"},
                            "SAGEMAKER_ENDPOINT_NAME": {"Ref": "EndpointName"},
                            "BASELINE_DATA_LOCATION": {"Ref": "BaselineData"},
                            "BASELINE_JOB_OUTPUT_LOCATION": {
                                "Ref": "BaselineJobOutputLocation"
                            },
                            "INSTANCE_TYPE": {"Ref": "InstanceType"},
                            "INSTANCE_VOLUME_SIZE": {"Ref": "InstanceVolumeSize"},
                            "MAX_RUNTIME_SECONDS": {"Ref": "BaselineMaxRuntimeSeconds"},
                            "ROLE_ARN": {
                                "Fn::GetAtt": [
                                    "createbaselinesagemakerroleEF4D9DF2",
                                    "Arn",
                                ]
                            },
                            "KMS_KEY_ARN": {
                                "Fn::If": [
                                    "KmsKeyProvided",
                                    {"Ref": "KmsKeyArn"},
                                    {"Ref": "AWS::NoValue"},
                                ]
                            },
                            "ENDPOINT_NAME": {"Ref": "EndpointName"},
                            "MODEL_PREDICTED_LABEL_CONFIG": Match.any_value(),
                            "BIAS_CONFIG": Match.any_value(),
                            "SHAP_CONFIG": Match.any_value(),
                            "MODEL_SCORES": Match.any_value(),
                            "STACK_NAME": {"Ref": "AWS::StackName"},
                            "LOG_LEVEL": "INFO",
                        }
                    },
                    "Handler": "main.handler",
                    "Layers": [{"Ref": Match.string_like_regexp("sagemakerlayer*")}],
                    "Runtime": "python3.10",
                    "Timeout": 600,
                },
            )

            template.has_resource(
                "AWS::Lambda::Function",
                {
                    "DependsOn": [
                        Match.string_like_regexp(
                            "createbaselinejoblambdaroleDefaultPolicy*"
                        ),
                        Match.string_like_regexp("createbaselinejoblambdarole*"),
                    ]
                },
            )

    def test_invoke_lambda_policy(self):
        """Tests for Training Lambda function"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::IAM::Policy",
                {
                    "PolicyDocument": {
                        "Statement": [
                            {
                                "Action": "lambda:InvokeFunction",
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::GetAtt": [
                                        Match.string_like_regexp(
                                            "createdatabaselinejob*"
                                        ),
                                        "Arn",
                                    ]
                                },
                            }
                        ],
                        "Version": "2012-10-17",
                    },
                    "PolicyName": Match.string_like_regexp(
                        "InvokeBaselineLambdaServiceRoleDefaultPolicy*"
                    ),
                    "Roles": [
                        {
                            "Ref": Match.string_like_regexp(
                                "InvokeBaselineLambdaServiceRole*"
                            )
                        }
                    ],
                },
            )

    def test_custom_resource_invoke_lambda(self):
        """Tests for Custom resource to invoke Lambda function"""
        for template in self.templates:
            template.has_resource_properties(
                "Custom::InvokeLambda",
                {
                    "ServiceToken": {
                        "Fn::GetAtt": [
                            Match.string_like_regexp("InvokeBaselineLambda*"),
                            "Arn",
                        ]
                    },
                    "function_name": {
                        "Ref": Match.string_like_regexp("createdatabaselinejob*")
                    },
                    "message": {
                        "Fn::Join": [
                            "",
                            [
                                "Invoking lambda function: ",
                                {
                                    "Ref": Match.string_like_regexp(
                                        "createdatabaselinejob*"
                                    )
                                },
                            ],
                        ]
                    },
                    "Resource": "InvokeLambda",
                    "assets_bucket_name": {"Ref": "AssetsBucket"},
                    "monitoring_type": Match.string_like_regexp(
                        "(DataQuality|ModelQuality|ModelBias|ModelExplainability)"
                    ),
                    "baseline_job_name": {"Ref": "BaselineJobName"},
                    "baseline_data_location": {"Ref": "BaselineData"},
                    "baseline_output_bucket": {"Ref": "BaselineOutputBucket"},
                    "baseline_job_output_location": {
                        "Ref": "BaselineJobOutputLocation"
                    },
                    "endpoint_name": {"Ref": "EndpointName"},
                    "instance_type": {"Ref": "InstanceType"},
                    "instance_volume_size": {"Ref": "InstanceVolumeSize"},
                    "max_runtime_seconds": {"Ref": "BaselineMaxRuntimeSeconds"},
                    "kms_key_arn": {
                        "Fn::If": [
                            "KmsKeyProvided",
                            {"Ref": "KmsKeyArn"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    "stack_name": {"Ref": "AWS::StackName"},
                },
            )

            template.has_resource(
                "Custom::InvokeLambda",
                {
                    "DependsOn": [Match.string_like_regexp("createdatabaselinejob*")],
                    "UpdateReplacePolicy": "Delete",
                    "DeletionPolicy": "Delete",
                },
            )

    def test_data_quality_job_definition(self):
        """Test Data Quality Job Definition"""
        self.data_quality_template.has_resource_properties(
            "AWS::SageMaker::DataQualityJobDefinition",
            {
                "DataQualityAppSpecification": {"ImageUri": {"Ref": "ImageUri"}},
                "DataQualityJobInput": {
                    "EndpointInput": {
                        "EndpointName": {"Ref": "EndpointName"},
                        "LocalPath": "/opt/ml/processing/input/data_quality_input",
                    }
                },
                "DataQualityJobOutputConfig": {
                    "KmsKeyId": {
                        "Fn::If": [
                            "KmsKeyProvided",
                            {"Ref": "KmsKeyArn"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    "MonitoringOutputs": [
                        {
                            "S3Output": {
                                "LocalPath": "/opt/ml/processing/output/data_quality_output",
                                "S3UploadMode": "EndOfJob",
                                "S3Uri": {
                                    "Fn::Join": [
                                        "",
                                        ["s3://", {"Ref": "MonitoringOutputLocation"}],
                                    ]
                                },
                            }
                        }
                    ],
                },
                "JobResources": {
                    "ClusterConfig": {
                        "InstanceCount": {"Ref": "JobInstanceCount"},
                        "InstanceType": {"Ref": "InstanceType"},
                        "VolumeKmsKeyId": {
                            "Fn::If": [
                                "KmsKeyProvided",
                                {"Ref": "KmsKeyArn"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "VolumeSizeInGB": {"Ref": "InstanceVolumeSize"},
                    }
                },
                "RoleArn": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("MLOpsSagemakerMonitorRole*"),
                        "Arn",
                    ]
                },
                "DataQualityBaselineConfig": {
                    "ConstraintsResource": {
                        "S3Uri": {
                            "Fn::Join": [
                                "",
                                [
                                    "s3://",
                                    {"Ref": "BaselineJobOutputLocation"},
                                    "/constraints.json",
                                ],
                            ]
                        }
                    },
                    "StatisticsResource": {
                        "S3Uri": {
                            "Fn::Join": [
                                "",
                                [
                                    "s3://",
                                    {"Ref": "BaselineJobOutputLocation"},
                                    "/statistics.json",
                                ],
                            ]
                        }
                    },
                },
                "StoppingCondition": {
                    "MaxRuntimeInSeconds": {"Ref": "MonitorMaxRuntimeSeconds"}
                },
                "Tags": [{"Key": "stack-name", "Value": {"Ref": "AWS::StackName"}}],
            },
        )

        self.data_quality_template.has_resource(
            "AWS::SageMaker::DataQualityJobDefinition",
            {
                "DependsOn": [
                    "InvokeBaselineLambdaCustomResource",
                    Match.string_like_regexp("MLOpsSagemakerMonitorRoleDefaultPolicy*"),
                    Match.string_like_regexp("MLOpsSagemakerMonitorRole*"),
                ]
            },
        )

    def test_model_quality_job_definition(self):
        """Test Model Quality Job Definition"""
        self.model_quality_template.has_resource_properties(
            "AWS::SageMaker::ModelQualityJobDefinition",
            {
                "JobResources": {
                    "ClusterConfig": {
                        "InstanceCount": {"Ref": "JobInstanceCount"},
                        "InstanceType": {"Ref": "InstanceType"},
                        "VolumeKmsKeyId": {
                            "Fn::If": [
                                "KmsKeyProvided",
                                {"Ref": "KmsKeyArn"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "VolumeSizeInGB": {"Ref": "InstanceVolumeSize"},
                    }
                },
                "ModelQualityAppSpecification": {
                    "ImageUri": {"Ref": "ImageUri"},
                    "ProblemType": {"Ref": "ProblemType"},
                },
                "ModelQualityJobInput": {
                    "EndpointInput": {
                        "EndpointName": {"Ref": "EndpointName"},
                        "InferenceAttribute": {
                            "Fn::If": [
                                "InferenceAttributeProvided",
                                {"Ref": "MonitorInferenceAttribute"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "LocalPath": "/opt/ml/processing/input/model_quality_input",
                        "ProbabilityAttribute": {
                            "Fn::If": [
                                "ProblemTypeBinaryClassificationProbabilityAttributeProvided",
                                {"Ref": "MonitorProbabilityAttribute"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "ProbabilityThresholdAttribute": {
                            "Fn::If": [
                                "ProblemTypeBinaryClassificationProbabilityThresholdProvided",
                                {"Ref": "ProbabilityThresholdAttribute"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                    },
                    "GroundTruthS3Input": {
                        "S3Uri": {
                            "Fn::Join": [
                                "",
                                ["s3://", {"Ref": "MonitorGroundTruthInput"}],
                            ]
                        }
                    },
                },
                "ModelQualityJobOutputConfig": {
                    "KmsKeyId": {
                        "Fn::If": [
                            "KmsKeyProvided",
                            {"Ref": "KmsKeyArn"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    "MonitoringOutputs": [
                        {
                            "S3Output": {
                                "LocalPath": "/opt/ml/processing/output/model_quality_output",
                                "S3UploadMode": "EndOfJob",
                                "S3Uri": {
                                    "Fn::Join": [
                                        "",
                                        ["s3://", {"Ref": "MonitoringOutputLocation"}],
                                    ]
                                },
                            }
                        }
                    ],
                },
                "RoleArn": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("MLOpsSagemakerMonitorRole*"),
                        "Arn",
                    ]
                },
                "ModelQualityBaselineConfig": {
                    "ConstraintsResource": {
                        "S3Uri": {
                            "Fn::Join": [
                                "",
                                [
                                    "s3://",
                                    {"Ref": "BaselineJobOutputLocation"},
                                    "/constraints.json",
                                ],
                            ]
                        }
                    }
                },
                "StoppingCondition": {
                    "MaxRuntimeInSeconds": {"Ref": "MonitorMaxRuntimeSeconds"}
                },
                "Tags": [{"Key": "stack-name", "Value": {"Ref": "AWS::StackName"}}],
            },
        )

        self.model_quality_template.has_resource(
            "AWS::SageMaker::ModelQualityJobDefinition",
            {
                "DependsOn": [
                    "InvokeBaselineLambdaCustomResource",
                    Match.string_like_regexp("MLOpsSagemakerMonitorRoleDefaultPolicy*"),
                    Match.string_like_regexp("MLOpsSagemakerMonitorRole*"),
                ]
            },
        )

    def test_model_bias_job_definition(self):
        """Test Model Bias Job Definition"""
        self.model_bias_template.has_resource_properties(
            "AWS::SageMaker::ModelBiasJobDefinition",
            {
                "JobResources": {
                    "ClusterConfig": {
                        "InstanceCount": {"Ref": "JobInstanceCount"},
                        "InstanceType": {"Ref": "InstanceType"},
                        "VolumeKmsKeyId": {
                            "Fn::If": [
                                "KmsKeyProvided",
                                {"Ref": "KmsKeyArn"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "VolumeSizeInGB": {"Ref": "InstanceVolumeSize"},
                    }
                },
                "ModelBiasAppSpecification": {
                    "ConfigUri": {
                        "Fn::Join": [
                            "",
                            [
                                "s3://",
                                {"Ref": "BaselineJobOutputLocation"},
                                "/monitor/analysis_config.json",
                            ],
                        ]
                    },
                    "ImageUri": {"Ref": "ImageUri"},
                },
                "ModelBiasJobInput": {
                    "EndpointInput": {
                        "EndpointName": {"Ref": "EndpointName"},
                        "FeaturesAttribute": {
                            "Fn::If": [
                                "FeaturesAttributeProvided",
                                {"Ref": "FeaturesAttribute"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "InferenceAttribute": {
                            "Fn::If": [
                                "InferenceAttributeProvided",
                                {"Ref": "MonitorInferenceAttribute"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "LocalPath": "/opt/ml/processing/input/model_bias_input",
                        "ProbabilityAttribute": {
                            "Fn::If": [
                                "ProblemTypeBinaryClassificationProbabilityAttributeProvided",
                                {"Ref": "MonitorProbabilityAttribute"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "ProbabilityThresholdAttribute": {
                            "Fn::If": [
                                "ProblemTypeBinaryClassificationProbabilityThresholdProvided",
                                {"Ref": "ProbabilityThresholdAttribute"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                    },
                    "GroundTruthS3Input": {
                        "S3Uri": {
                            "Fn::Join": [
                                "",
                                ["s3://", {"Ref": "MonitorGroundTruthInput"}],
                            ]
                        }
                    },
                },
                "ModelBiasJobOutputConfig": {
                    "KmsKeyId": {
                        "Fn::If": [
                            "KmsKeyProvided",
                            {"Ref": "KmsKeyArn"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    "MonitoringOutputs": [
                        {
                            "S3Output": {
                                "LocalPath": "/opt/ml/processing/output/model_bias_output",
                                "S3UploadMode": "EndOfJob",
                                "S3Uri": {
                                    "Fn::Join": [
                                        "",
                                        ["s3://", {"Ref": "MonitoringOutputLocation"}],
                                    ]
                                },
                            }
                        }
                    ],
                },
                "RoleArn": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("MLOpsSagemakerMonitorRole*"),
                        "Arn",
                    ]
                },
                "ModelBiasBaselineConfig": {
                    "ConstraintsResource": {
                        "S3Uri": {
                            "Fn::Join": [
                                "",
                                [
                                    "s3://",
                                    {"Ref": "BaselineJobOutputLocation"},
                                    "/analysis.json",
                                ],
                            ]
                        }
                    }
                },
                "StoppingCondition": {
                    "MaxRuntimeInSeconds": {"Ref": "MonitorMaxRuntimeSeconds"}
                },
                "Tags": [{"Key": "stack-name", "Value": {"Ref": "AWS::StackName"}}],
            },
        )

        self.model_bias_template.has_resource(
            "AWS::SageMaker::ModelBiasJobDefinition",
            {
                "DependsOn": [
                    "InvokeBaselineLambdaCustomResource",
                    Match.string_like_regexp("MLOpsSagemakerMonitorRoleDefaultPolicy*"),
                    Match.string_like_regexp("MLOpsSagemakerMonitorRole*"),
                ]
            },
        )

    def test_model_explainability_job_definition(self):
        """Test Model Explainability Job Definition"""
        self.model_explainability_template.has_resource_properties(
            "AWS::SageMaker::ModelExplainabilityJobDefinition",
            {
                "JobResources": {
                    "ClusterConfig": {
                        "InstanceCount": {"Ref": "JobInstanceCount"},
                        "InstanceType": {"Ref": "InstanceType"},
                        "VolumeKmsKeyId": {
                            "Fn::If": [
                                "KmsKeyProvided",
                                {"Ref": "KmsKeyArn"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "VolumeSizeInGB": {"Ref": "InstanceVolumeSize"},
                    }
                },
                "ModelExplainabilityAppSpecification": {
                    "ConfigUri": {
                        "Fn::Join": [
                            "",
                            [
                                "s3://",
                                {"Ref": "BaselineJobOutputLocation"},
                                "/monitor/analysis_config.json",
                            ],
                        ]
                    },
                    "ImageUri": {"Ref": "ImageUri"},
                },
                "ModelExplainabilityJobInput": {
                    "EndpointInput": {
                        "EndpointName": {"Ref": "EndpointName"},
                        "FeaturesAttribute": {
                            "Fn::If": [
                                "FeaturesAttributeProvided",
                                {"Ref": "FeaturesAttribute"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "InferenceAttribute": {
                            "Fn::If": [
                                "InferenceAttributeProvided",
                                {"Ref": "MonitorInferenceAttribute"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "LocalPath": "/opt/ml/processing/input/model_explainability_input",
                        "ProbabilityAttribute": {
                            "Fn::If": [
                                "ProblemTypeBinaryClassificationProbabilityAttributeProvided",
                                {"Ref": "MonitorProbabilityAttribute"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                    }
                },
                "ModelExplainabilityJobOutputConfig": {
                    "KmsKeyId": {
                        "Fn::If": [
                            "KmsKeyProvided",
                            {"Ref": "KmsKeyArn"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    "MonitoringOutputs": [
                        {
                            "S3Output": {
                                "LocalPath": "/opt/ml/processing/output/model_explainability_output",
                                "S3UploadMode": "EndOfJob",
                                "S3Uri": {
                                    "Fn::Join": [
                                        "",
                                        ["s3://", {"Ref": "MonitoringOutputLocation"}],
                                    ]
                                },
                            }
                        }
                    ],
                },
                "RoleArn": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("MLOpsSagemakerMonitorRole*"),
                        "Arn",
                    ]
                },
                "ModelExplainabilityBaselineConfig": {
                    "ConstraintsResource": {
                        "S3Uri": {
                            "Fn::Join": [
                                "",
                                [
                                    "s3://",
                                    {"Ref": "BaselineJobOutputLocation"},
                                    "/analysis.json",
                                ],
                            ]
                        }
                    }
                },
                "StoppingCondition": {
                    "MaxRuntimeInSeconds": {"Ref": "MonitorMaxRuntimeSeconds"}
                },
                "Tags": [{"Key": "stack-name", "Value": {"Ref": "AWS::StackName"}}],
            },
        )

        self.model_explainability_template.has_resource(
            "AWS::SageMaker::ModelExplainabilityJobDefinition",
            {
                "DependsOn": [
                    "InvokeBaselineLambdaCustomResource",
                    Match.string_like_regexp("MLOpsSagemakerMonitorRoleDefaultPolicy*"),
                    Match.string_like_regexp("MLOpsSagemakerMonitorRole*"),
                ]
            },
        )

    def test_monitoring_schedule(self):
        """Tests for SageMaker Monitor Schedule"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::SageMaker::MonitoringSchedule",
                {
                    "MonitoringScheduleConfig": {
                        "MonitoringJobDefinitionName": {
                            "Fn::GetAtt": [
                                Match.string_like_regexp(
                                    "(DataQualityJobDefinition|ModelQualityJobDefinition|ModelBiasJobDefinition|ModelExplainabilityJobDefinition)"
                                ),
                                "JobDefinitionName",
                            ]
                        },
                        "MonitoringType": Match.string_like_regexp(
                            "(DataQuality|ModelQuality|ModelBias|ModelExplainability)"
                        ),
                        "ScheduleConfig": {
                            "ScheduleExpression": {"Ref": "ScheduleExpression"}
                        },
                    },
                    "MonitoringScheduleName": {"Ref": "MonitoringScheduleName"},
                    "Tags": [{"Key": "stack-name", "Value": {"Ref": "AWS::StackName"}}],
                },
            )

            template.has_resource(
                "AWS::SageMaker::MonitoringSchedule",
                {
                    "DependsOn": [
                        Match.string_like_regexp(
                            "(DataQualityJobDefinition|ModelQualityJobDefinition|ModelBiasJobDefinition|ModelExplainabilityJobDefinition)"
                        )
                    ]
                },
            )

    def test_template_outputs(self):
        """Tests for templates outputs"""
        for template in self.templates:
            template.has_output(
                "BaselineName",
                {"Value": {"Ref": "BaselineJobName"}},
            )

            template.has_output(
                "MonitoringScheduleJobName",
                {"Value": {"Ref": "MonitoringScheduleName"}},
            )

            template.has_output(
                "MonitoringScheduleType",
                {
                    "Value": Match.string_like_regexp(
                        "(DataQuality|ModelQuality|ModelBias|ModelExplainability)"
                    )
                },
            )

            template.has_output(
                "BaselineJobOutput",
                {
                    "Value": {
                        "Fn::Join": [
                            "",
                            [
                                "https://s3.console.aws.amazon.com/s3/buckets/",
                                {"Ref": "BaselineJobOutputLocation"},
                                "/",
                            ],
                        ]
                    }
                },
            )

            template.has_output(
                "MonitoringScheduleOutput",
                {
                    "Value": {
                        "Fn::Join": [
                            "",
                            [
                                "https://s3.console.aws.amazon.com/s3/buckets/",
                                {"Ref": "MonitoringOutputLocation"},
                                "/",
                                {"Ref": "EndpointName"},
                                "/",
                                {"Ref": "MonitoringScheduleName"},
                                "/",
                            ],
                        ]
                    }
                },
            )

            template.has_output(
                "MonitoredSagemakerEndpoint",
                {"Value": {"Ref": "EndpointName"}},
            )

            template.has_output(
                "DataCaptureS3Location",
                {
                    "Value": {
                        "Fn::Join": [
                            "",
                            [
                                "https://s3.console.aws.amazon.com/s3/buckets/",
                                {"Ref": "DataCaptureLocation"},
                                "/",
                                {"Ref": "EndpointName"},
                                "/",
                            ],
                        ]
                    }
                },
            )
