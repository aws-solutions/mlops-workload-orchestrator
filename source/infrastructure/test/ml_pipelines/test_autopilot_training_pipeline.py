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
from lib.blueprints.ml_pipelines.autopilot_training_pipeline import (
    AutopilotJobStack,
)
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from test.context_helper import get_cdk_context


class TestAutoPilotTraining:
    """Tests for autopilot_training_pipeline stack"""

    def setup_class(self):
        """Tests setup"""
        app = cdk.App(context=get_cdk_context("././cdk.json")["context"])

        solution_id = get_cdk_context_value(app, "SolutionId")
        version = get_cdk_context_value(app, "Version")

        autopilot_stack = AutopilotJobStack(
            app,
            "AutopilotJobStack",
            description=(
                f"({solution_id}-autopilot) - Autopilot training pipeline. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # create template
        self.template = Template.from_stack(autopilot_stack)

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
            "JobName",
            {
                "Type": "String",
                "AllowedPattern": "^[a-zA-Z0-9](-*[a-zA-Z0-9]){0,62}",
                "Description": "Unique name of the training job",
                "MaxLength": 63,
                "MinLength": 1,
            },
        )

        self.template.has_parameter(
            "ProblemType",
            {
                "Type": "String",
                "Default": "",
                "AllowedValues": [
                    "",
                    "Regression",
                    "BinaryClassification",
                    "MulticlassClassification",
                ],
                "Description": "Optional Problem type. Possible values: Regression | BinaryClassification | MulticlassClassification. If not provided, the Autopilot will infere the probelm type from the target attribute. Note: if ProblemType is provided, the AutopilotJobObjective must be provided too.",
            },
        )

        self.template.has_parameter(
            "AutopilotJobObjective",
            {
                "Type": "String",
                "Default": "",
                "AllowedValues": ["", "Accuracy", "MSE", "F1", "F1macro", "AUC"],
                "Description": "Optional metric to optimize. If not provided, F1: used or binary classification, Accuracy: used for multiclass classification, and MSE: used for regression. Note: if AutopilotJobObjective is provided, the ProblemType must be provided too.",
            },
        )

        self.template.has_parameter(
            "TrainingData",
            {
                "Type": "String",
                "AllowedPattern": ".*",
                "Description": "Training data key (located in the Assets bucket)",
                "MaxLength": 128,
                "MinLength": 1,
            },
        )

        self.template.has_parameter(
            "TargetAttribute",
            {
                "Type": "String",
                "AllowedPattern": ".*",
                "Description": "Target attribute name in the training data",
                "MaxLength": 128,
                "MinLength": 1,
            },
        )

        self.template.has_parameter(
            "JobOutputLocation",
            {
                "Type": "String",
                "AllowedPattern": ".*",
                "Description": "S3 output prefix (located in the Assets bucket)",
                "MaxLength": 128,
                "MinLength": 1,
            },
        )

        self.template.has_parameter(
            "CompressionType",
            {
                "Type": "String",
                "Default": "",
                "AllowedValues": ["", "Gzip"],
                "Description": "Optional compression type for the training data",
            },
        )

        self.template.has_parameter(
            "AutopilotMaxCandidates",
            {
                "Type": "Number",
                "Default": 10,
                "Description": "Max number of candidates to be tried by teh autopilot job",
                "MinValue": 1,
            },
        )

        self.template.has_parameter(
            "EncryptInnerTraffic",
            {
                "Type": "String",
                "Default": "True",
                "AllowedValues": ["True", "False"],
                "Description": "Encrypt inner-container traffic for the job",
            },
        )

        self.template.has_parameter(
            "MaxRuntimePerJob",
            {
                "Type": "Number",
                "Default": 86400,
                "Description": "Max runtime (in seconds) allowed per training job ",
                "MaxValue": 259200,
                "MinValue": 600,
            },
        )

        self.template.has_parameter(
            "AutopilotTotalRuntime",
            {
                "Type": "Number",
                "Default": 2592000,
                "Description": "Autopilot total runtime (in seconds) allowed for the job",
                "MaxValue": 2592000,
                "MinValue": 3600,
            },
        )

        self.template.has_parameter(
            "GenerateDefinitionsOnly",
            {
                "Type": "String",
                "Default": "False",
                "AllowedValues": ["True", "False"],
                "Description": "generate candidate definitions only by the autopilot job",
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
            "NotificationsSNSTopicArn",
            {
                "Type": "String",
                "AllowedPattern": "^arn:\\S+:sns:\\S+:\\d{12}:\\S+$",
                "Description": "AWS SNS Topics arn used by the MLOps Workload Orchestrator to notify the administrator.",
            },
        )

    def test_template_conditions(self):
        """Tests for templates conditions"""
        self.template.has_condition(
            "ProblemTypeProvided",
            {"Fn::Not": [{"Fn::Equals": [{"Ref": "ProblemType"}, ""]}]},
        )

        self.template.has_condition(
            "JobObjectiveProvided",
            {"Fn::Not": [{"Fn::Equals": [{"Ref": "AutopilotJobObjective"}, ""]}]},
        )

        self.template.has_condition(
            "CompressionTypeProvided",
            {"Fn::Not": [{"Fn::Equals": [{"Ref": "CompressionType"}, ""]}]},
        )

        self.template.has_condition(
            "KMSProvided",
            {"Fn::Not": [{"Fn::Equals": [{"Ref": "KmsKeyArn"}, ""]}]},
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
                            "Resource": {
                                "Fn::If": [
                                    "KMSProvided",
                                    {"Ref": "KmsKeyArn"},
                                    {"Ref": "AWS::NoValue"},
                                ]
                            },
                        }
                    ],
                    "Version": "2012-10-17",
                },
                "PolicyName": Match.string_like_regexp("AutopilotKmsPolicy*"),
                "Roles": [
                    {"Ref": Match.string_like_regexp("createautopilotsagemakerrole*")}
                ],
            },
        )

        self.template.has_resource("AWS::IAM::Policy", {"Condition": "KMSProvided"})

    def test_autopilot_lambda(self):
        """Tests for Autopilot Lambda function"""
        self.template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Code": {
                    "S3Bucket": {"Ref": "BlueprintBucket"},
                    "S3Key": "blueprints/lambdas/create_sagemaker_autopilot_job.zip",
                },
                "Role": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("autopilotjoblambdarole*"),
                        "Arn",
                    ]
                },
                "Environment": {
                    "Variables": {
                        "JOB_NAME": {"Ref": "JobName"},
                        "ROLE_ARN": {
                            "Fn::GetAtt": [
                                Match.string_like_regexp(
                                    "createautopilotsagemakerrole*"
                                ),
                                "Arn",
                            ]
                        },
                        "ASSETS_BUCKET": {"Ref": "AssetsBucket"},
                        "TRAINING_DATA_KEY": {"Ref": "TrainingData"},
                        "JOB_OUTPUT_LOCATION": {"Ref": "JobOutputLocation"},
                        "TARGET_ATTRIBUTE_NAME": {"Ref": "TargetAttribute"},
                        "KMS_KEY_ARN": {
                            "Fn::If": [
                                "KMSProvided",
                                {"Ref": "KmsKeyArn"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "PROBLEM_TYPE": {
                            "Fn::If": [
                                "ProblemTypeProvided",
                                {"Ref": "ProblemType"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "JOB_OBJECTIVE": {
                            "Fn::If": [
                                "JobObjectiveProvided",
                                {"Ref": "AutopilotJobObjective"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "COMPRESSION_TYPE": {
                            "Fn::If": [
                                "CompressionTypeProvided",
                                {"Ref": "CompressionType"},
                                {"Ref": "AWS::NoValue"},
                            ]
                        },
                        "MAX_CANDIDATES": {"Ref": "AutopilotMaxCandidates"},
                        "ENCRYPT_INTER_CONTAINER_TRAFFIC": {
                            "Ref": "EncryptInnerTraffic"
                        },
                        "MAX_RUNTIME_PER_JOB": {"Ref": "MaxRuntimePerJob"},
                        "TOTAL_JOB_RUNTIME": {"Ref": "AutopilotTotalRuntime"},
                        "GENERATE_CANDIDATE_DEFINITIONS_ONLY": {
                            "Ref": "GenerateDefinitionsOnly"
                        },
                        "LOG_LEVEL": "INFO",
                    }
                },
                "Handler": "main.handler",
                "Layers": [{"Ref": Match.string_like_regexp("sagemakerlayer*")}],
                "Runtime": "python3.10",
                "Timeout": 600,
            },
        )

        self.template.has_resource(
            "AWS::Lambda::Function",
            {
                "DependsOn": [
                    Match.string_like_regexp("autopilotjoblambdaroleDefaultPolicy*"),
                    Match.string_like_regexp("autopilotjoblambdarole*"),
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
                        Match.string_like_regexp("InvokeAutopilotLambdaServiceRole*"),
                        "Arn",
                    ]
                },
                "Handler": "index.handler",
                "Runtime": "python3.10",
                "Timeout": 300,
            },
        )
        self.template.has_resource(
            "AWS::Lambda::Function",
            {
                "DependsOn": [
                    Match.string_like_regexp(
                        "InvokeAutopilotLambdaServiceRoleDefaultPolicy*"
                    ),
                    Match.string_like_regexp("InvokeAutopilotLambdaServiceRole*"),
                ]
            },
        )

    def test_custom_resource_invoke_lambda(self):
        """Tests for Custom resource to invoke Lambda function"""
        self.template.has_resource_properties(
            "Custom::InvokeLambda",
            {
                "ServiceToken": {
                    "Fn::GetAtt": [
                        Match.string_like_regexp("InvokeAutopilotLambda*"),
                        "Arn",
                    ]
                },
                "function_name": {"Ref": Match.string_like_regexp("AutopilotLambda*")},
                "message": {
                    "Fn::Join": [
                        "",
                        [
                            "Invoking lambda function: ",
                            {"Ref": Match.string_like_regexp("AutopilotLambda*")},
                        ],
                    ]
                },
                "Resource": "InvokeLambda",
                "assets_bucket": {"Ref": "AssetsBucket"},
                "kms_key_arn": {"Ref": "KmsKeyArn"},
                "job_name": {"Ref": "JobName"},
                "training_data": {"Ref": "TrainingData"},
                "target_attribute_name": {"Ref": "TargetAttribute"},
                "job_output_location": {"Ref": "JobOutputLocation"},
                "problem_type": {"Ref": "ProblemType"},
                "objective_type": {"Ref": "AutopilotJobObjective"},
                "compression_type": {"Ref": "CompressionType"},
                "max_candidates": {"Ref": "AutopilotMaxCandidates"},
                "total_runtime": {"Ref": "AutopilotTotalRuntime"},
                "generate_candidate_definitions_only": {
                    "Ref": "GenerateDefinitionsOnly"
                },
            },
        )

        self.template.has_resource(
            "Custom::InvokeLambda",
            {
                "DependsOn": [Match.string_like_regexp("AutopilotLambda*")],
                "UpdateReplacePolicy": "Delete",
                "DeletionPolicy": "Delete",
            },
        )

    def test_events_rule(self):
        """Tests for Events Rule"""
        self.template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Description": "EventBridge rule to notify the admin on the status change of the hyperparameter job used by the autopilot job",
                "EventPattern": {
                    "detail": {
                        "HyperParameterTuningJobName": [{"prefix": {"Ref": "JobName"}}],
                        "HyperParameterTuningJobStatus": [
                            "Completed",
                            "Failed",
                            "Stopped",
                        ],
                    },
                    "detail-type": ["SageMaker HyperParameter Tuning Job State Change"],
                    "source": ["aws.sagemaker"],
                },
                "State": "ENABLED",
                "Targets": [
                    {
                        "Arn": {"Ref": "NotificationsSNSTopicArn"},
                        "Id": "Target0",
                        "InputTransformer": {
                            "InputPathsMap": {
                                "detail-HyperParameterTuningJobName": "$.detail.HyperParameterTuningJobName",
                                "detail-HyperParameterTuningJobStatus": "$.detail.HyperParameterTuningJobStatus",
                            },
                            "InputTemplate": {
                                "Fn::Join": [
                                    "",
                                    [
                                        '"The hyperparameter training job <detail-HyperParameterTuningJobName> (used by the Autopilot job: ',
                                        {"Ref": "JobName"},
                                        ') status is: <detail-HyperParameterTuningJobStatus>."',
                                    ],
                                ]
                            },
                        },
                    }
                ],
            },
        )

        self.template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Description": "EventBridge rule to notify the admin on the status change of the last two processing jobs used the autopilot job",
                "EventPattern": {
                    "detail": {
                        "ProcessingJobName": [
                            {
                                "prefix": {
                                    "Fn::Join": ["", [{"Ref": "JobName"}, "-dpp"]]
                                }
                            },
                            {
                                "prefix": {
                                    "Fn::Join": [
                                        "",
                                        [{"Ref": "JobName"}, "-documentation"],
                                    ]
                                }
                            },
                        ],
                        "ProcessingJobStatus": ["Completed", "Failed", "Stopped"],
                    },
                    "detail-type": ["SageMaker Processing Job State Change"],
                    "source": ["aws.sagemaker"],
                },
                "State": "ENABLED",
                "Targets": [
                    {
                        "Arn": {"Ref": "NotificationsSNSTopicArn"},
                        "Id": "Target0",
                        "InputTransformer": {
                            "InputPathsMap": {
                                "detail-ProcessingJobName": "$.detail.ProcessingJobName",
                                "detail-ProcessingJobStatus": "$.detail.ProcessingJobStatus",
                            },
                            "InputTemplate": {
                                "Fn::Join": [
                                    "",
                                    [
                                        '"The processing job <detail-ProcessingJobName> (used by the Autopilot job: ',
                                        {"Ref": "JobName"},
                                        ') status is: <detail-ProcessingJobStatus>."',
                                    ],
                                ]
                            },
                        },
                    }
                ],
            },
        )

        self.template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Description": "EventBridge rule to notify the admin on the status change of the intermidate processing jobs used the autopilot job",
                "EventPattern": {
                    "detail": {
                        "ProcessingJobName": [
                            {"prefix": {"Fn::Join": ["", [{"Ref": "JobName"}, "-dp"]]}},
                            {"prefix": {"Fn::Join": ["", [{"Ref": "JobName"}, "-pr"]]}},
                        ],
                        "ProcessingJobStatus": ["Failed", "Stopped"],
                    },
                    "detail-type": ["SageMaker Processing Job State Change"],
                    "source": ["aws.sagemaker"],
                },
                "State": "ENABLED",
                "Targets": [
                    {
                        "Arn": {"Ref": "NotificationsSNSTopicArn"},
                        "Id": "Target0",
                        "InputTransformer": {
                            "InputPathsMap": {
                                "detail-ProcessingJobName": "$.detail.ProcessingJobName",
                                "detail-ProcessingJobStatus": "$.detail.ProcessingJobStatus",
                            },
                            "InputTemplate": {
                                "Fn::Join": [
                                    "",
                                    [
                                        '"The processing job <detail-ProcessingJobName> (used by the Autopilot job: ',
                                        {"Ref": "JobName"},
                                        ') status is: <detail-ProcessingJobStatus>."',
                                    ],
                                ]
                            },
                        },
                    }
                ],
            },
        )

        self.template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Description": "EventBridge rule to notify the admin on the status change of the intermidate training jobs used the autopilot job",
                "EventPattern": {
                    "detail": {
                        "TrainingJobName": [
                            {"prefix": {"Fn::Join": ["", [{"Ref": "JobName"}, "-dpp"]]}}
                        ],
                        "TrainingJobStatus": ["Failed", "Stopped"],
                    },
                    "detail-type": ["SageMaker Training Job State Change"],
                    "source": ["aws.sagemaker"],
                },
                "State": "ENABLED",
                "Targets": [
                    {
                        "Arn": {"Ref": "NotificationsSNSTopicArn"},
                        "Id": "Target0",
                        "InputTransformer": {
                            "InputPathsMap": {
                                "detail-TrainingJobName": "$.detail.TrainingJobName",
                                "detail-TrainingJobStatus": "$.detail.TrainingJobStatus",
                            },
                            "InputTemplate": {
                                "Fn::Join": [
                                    "",
                                    [
                                        '"The training job <detail-TrainingJobName> (used by the Autopilot job: ',
                                        {"Ref": "JobName"},
                                        ') status is: <detail-TrainingJobStatus>."',
                                    ],
                                ]
                            },
                        },
                    }
                ],
            },
        )

        self.template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Description": "EventBridge rule to notify the admin on the status change of the intermidate transform jobs used the autopilot job",
                "EventPattern": {
                    "detail": {
                        "TransformJobName": [
                            {"prefix": {"Fn::Join": ["", [{"Ref": "JobName"}, "-dpp"]]}}
                        ],
                        "TransformJobStatus": ["Failed", "Stopped"],
                    },
                    "detail-type": ["SageMaker Transform Job State Change"],
                    "source": ["aws.sagemaker"],
                },
                "State": "ENABLED",
                "Targets": [
                    {
                        "Arn": {"Ref": "NotificationsSNSTopicArn"},
                        "Id": "Target0",
                        "InputTransformer": {
                            "InputPathsMap": {
                                "detail-TransformJobName": "$.detail.TransformJobName",
                                "detail-TransformJobStatus": "$.detail.TransformJobStatus",
                            },
                            "InputTemplate": {
                                "Fn::Join": [
                                    "",
                                    [
                                        '"The transform job <detail-TransformJobName> (used by the Autopilot job: ',
                                        {"Ref": "JobName"},
                                        ') status is: <detail-TransformJobStatus>."',
                                    ],
                                ]
                            },
                        },
                    }
                ],
            },
        )

    def test_template_outputs(self):
        """Tests for templates outputs"""
        self.template.has_output(
            "AutopilotJobName",
            {
                "Description": "The autopilot training job's name",
                "Value": {"Ref": "JobName"},
            },
        )

        self.template.has_output(
            "AutopilotJobOutputLocation",
            {
                "Description": "Output location of the autopilot training job",
                "Value": {
                    "Fn::Join": [
                        "",
                        [
                            "https://s3.console.aws.amazon.com/s3/buckets/",
                            {"Ref": "AssetsBucket"},
                            "/",
                            {"Ref": "JobOutputLocation"},
                            "/",
                        ],
                    ]
                },
            },
        )

        self.template.has_output(
            "TrainingDataLocation",
            {
                "Description": "Training data used by the autopilot training job",
                "Value": {
                    "Fn::Join": [
                        "",
                        [
                            "https://s3.console.aws.amazon.com/s3/buckets/",
                            {"Ref": "AssetsBucket"},
                            "/",
                            {"Ref": "TrainingData"},
                        ],
                    ]
                },
            },
        )
