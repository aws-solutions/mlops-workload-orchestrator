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
from lib.blueprints.ml_pipelines.model_training_pipeline import (
    TrainingJobStack,
)
from lib.blueprints.pipeline_definitions.cdk_context_value import (
    get_cdk_context_value,
)
from test.context_helper import get_cdk_context


class TestModelTraining:
    """Tests for model_training_pipeline stack"""

    def setup_class(self):
        """Tests setup"""
        self.app_training_job = cdk.App(
            context=get_cdk_context("././cdk.json")["context"]
        )
        self.app_tuner_job = cdk.App(context=get_cdk_context("././cdk.json")["context"])

        solution_id = get_cdk_context_value(self.app_training_job, "SolutionId")
        version = get_cdk_context_value(self.app_training_job, "Version")

        training_job_stack = TrainingJobStack(
            self.app_training_job,
            "TrainingJobStack",
            training_type="TrainingJob",
            description=(
                f"({solution_id}-training) - Model Training pipeline. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # create training job template
        self.training_job_template = Template.from_stack(training_job_stack)

        tuner_job_stack = TrainingJobStack(
            self.app_tuner_job,
            "HyperparamaterTunningJobStack",
            training_type="HyperparameterTuningJob",
            description=(
                f"({solution_id}-tuner) - Model Hyperparameter Tunning pipeline. Version {version}"
            ),
            synthesizer=cdk.DefaultStackSynthesizer(
                generate_bootstrap_version_rule=False
            ),
        )

        # create hyper-parameters tuner job template
        self.tuner_job_template = Template.from_stack(tuner_job_stack)

        # all templates
        self.templates = [self.training_job_template, self.tuner_job_template]

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
                "JobName",
                {
                    "Type": "String",
                    "AllowedPattern": "^[a-zA-Z0-9](-*[a-zA-Z0-9]){0,62}",
                    "Description": "Unique name of the training job",
                    "MaxLength": 63,
                    "MinLength": 1,
                },
            )

            template.has_parameter(
                "ImageUri",
                {
                    "Type": "String",
                    "Description": "The algorithm image uri (build-in or custom)",
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
                "JobOutputLocation",
                {
                    "Type": "String",
                    "AllowedPattern": ".*",
                    "Description": "S3 output prefix (located in the Assets bucket)",
                    "MaxLength": 128,
                    "MinLength": 1,
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
                "TrainingData",
                {
                    "Type": "String",
                    "AllowedPattern": ".*",
                    "Description": "Training data key (located in the Assets bucket)",
                    "MaxLength": 128,
                    "MinLength": 1,
                },
            )

            template.has_parameter(
                "ValidationData",
                {
                    "Type": "String",
                    "AllowedPattern": ".*",
                    "Description": "Optional Validation data S3 key (located in the Assets bucket)",
                    "MaxLength": 128,
                    "MinLength": 0,
                },
            )

            template.has_parameter(
                "EncryptInnerTraffic",
                {
                    "Type": "String",
                    "Default": "True",
                    "AllowedValues": ["True", "False"],
                    "Description": "Encrypt inner-container traffic for the job",
                },
            )

            template.has_parameter(
                "MaxRuntimePerJob",
                {
                    "Type": "Number",
                    "Default": 86400,
                    "Description": "Max runtime (in seconds) allowed per training job ",
                    "MaxValue": 259200,
                    "MinValue": 600,
                },
            )

            template.has_parameter(
                "UseSpotInstances",
                {
                    "Type": "String",
                    "Default": "True",
                    "AllowedValues": ["True", "False"],
                    "Description": "Use managed spot instances with the training job.",
                },
            )

            template.has_parameter(
                "MaxWaitTimeForSpotInstances",
                {
                    "Type": "Number",
                    "Default": 172800,
                    "Description": "Max wait time (in seconds) for Spot instances (required if use_spot_instances = True). Must be greater than MaxRuntimePerJob.",
                    "MaxValue": 259200,
                    "MinValue": 1,
                },
            )

            template.has_parameter(
                "ContentType",
                {
                    "Type": "String",
                    "Default": "csv",
                    "AllowedPattern": ".*",
                    "Description": "The MIME type of the training data.",
                    "MaxLength": 256,
                },
            )

            template.has_parameter(
                "S3DataType",
                {
                    "Type": "String",
                    "Default": "S3Prefix",
                    "AllowedValues": [
                        "S3Prefix",
                        "ManifestFile",
                        "AugmentedManifestFile",
                    ],
                    "Description": "Training S3 data type. S3Prefix | ManifestFile | AugmentedManifestFile.",
                },
            )

            template.has_parameter(
                "DataDistribution",
                {
                    "Type": "String",
                    "Default": "FullyReplicated",
                    "AllowedValues": ["FullyReplicated", "ShardedByS3Key"],
                    "Description": "Data distribution. FullyReplicated | ShardedByS3Key.",
                },
            )

            template.has_parameter(
                "CompressionType",
                {
                    "Type": "String",
                    "Default": "",
                    "AllowedValues": ["", "Gzip"],
                    "Description": "Optional compression type for the training data",
                },
            )

            template.has_parameter(
                "DataInputMode",
                {
                    "Type": "String",
                    "Default": "File",
                    "AllowedValues": ["File", "Pipe", "FastFile"],
                    "Description": "Training data input mode. File | Pipe | FastFile.",
                },
            )

            template.has_parameter(
                "DataRecordWrapping",
                {
                    "Type": "String",
                    "Default": "",
                    "AllowedValues": ["", "RecordIO"],
                    "Description": "Optional training data record wrapping: RecordIO. ",
                },
            )

            template.has_parameter(
                "AttributeNames",
                {
                    "Type": "String",
                    "AllowedPattern": "(^\\[.*\\]$|^$)",
                    "Description": "Optional list of one or more attribute names to use that are found in a specified AugmentedManifestFile (if S3DataType='AugmentedManifestFile')",
                },
            )

            template.has_parameter(
                "AlgoHyperparameteres",
                {
                    "Type": "String",
                    "AllowedPattern": "^\\{(.*:.*)+\\}$",
                    "Description": "Algorithm hyperparameters provided as a json object",
                },
            )

            template.has_parameter(
                "NotificationsSNSTopicArn",
                {
                    "Type": "String",
                    "AllowedPattern": "^arn:\\S+:sns:\\S+:\\d{12}:\\S+$",
                    "Description": "AWS SNS Topics arn used by the MLOps Workload Orchestrator to notify the administrator.",
                },
            )

        # CF parameters only for hyper-parameters tuner job
        self.tuner_job_template.has_parameter(
            "HyperparametersTunerConfig",
            {
                "Type": "String",
                "AllowedPattern": "^\\{(.*:.*)+\\}$",
                "Description": "sagemaker.tuner.HyperparameterTuner configs (objective_metric_name, metric_definitions, strategy, objective_type, max_jobs, max_parallel_jobs, base_tuning_job_name=None, early_stopping_type) provided as a json object. Note: some has default values and are not required to be specified. Example: {'early_stopping_type' = 'Auto', 'objective_metric_name' = 'validation:auc', 'max_jobs' = 10, 'max_parallel_jobs' = 2}",
            },
        )

        self.tuner_job_template.has_parameter(
            "AlgoHyperparameteresRange",
            {
                "Type": "String",
                "AllowedPattern": '^\\{.*:\\s*\\[\\s*("continuous"|"integer"|"categorical")\\s*,\\s*\\[.*\\]\\s*\\]+\\s*\\}$',
                "Description": 'Algorithm hyperparameters range used by the Hyperparameters job provided as a json object, where the key is hyperparameter name, and the value is list with the first item the type (\'continuous\'|\'integer\'|\'categorical\')  and the second item is a list of [min_value, max_value] for \'continuous\'|\'integer\' and a list of values for \'categorical\'. Example: {"min_child_weight": ["continuous",[0, 120]], "max_depth": ["integer",[1, 15]], "optimizer": ["categorical", ["sgd", "Adam"]])}',
            },
        )

    def test_template_conditions(self):
        """Tests for templates conditions"""
        for template in self.templates:
            template.has_condition(
                "ValidationDataProvided",
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "ValidationData"}, ""]}]},
            )

            template.has_condition(
                "RecordWrappingProvided",
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "DataRecordWrapping"}, ""]}]},
            )

            template.has_condition(
                "RecordWrappingProvided",
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "DataRecordWrapping"}, ""]}]},
            )

            template.has_condition(
                "CompressionTypeProvided",
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "CompressionType"}, ""]}]},
            )

            template.has_condition(
                "KMSProvided",
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "KmsKeyArn"}, ""]}]},
            )

            template.has_condition(
                "AttributeNamesProvided",
                {"Fn::Not": [{"Fn::Equals": [{"Ref": "AttributeNames"}, ""]}]},
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

    def test_training_job_policy(self):
        """Tests for Training Job policy"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::IAM::Policy",
                {
                    "PolicyDocument": {
                        "Statement": Match.array_with(
                            [
                                {
                                    "Action": Match.string_like_regexp(
                                        "(sagemaker:CreateTrainingJob|sagemaker:CreateHyperParameterTuningJob)"
                                    ),
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
                                                Match.string_like_regexp(
                                                    "(:training-job/|:hyper-parameter-tuning-job/)"
                                                ),
                                                {"Ref": "JobName"},
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
                                                {"Ref": "AssetsBucket"},
                                                "/",
                                                {"Ref": "JobOutputLocation"},
                                                "/*",
                                            ],
                                        ]
                                    },
                                },
                                {
                                    "Action": "sts:AssumeRole",
                                    "Effect": "Allow",
                                    "Resource": {
                                        "Fn::GetAtt": [
                                            Match.string_like_regexp(
                                                "createtrainingjobsagemakerrole*"
                                            ),
                                            "Arn",
                                        ]
                                    },
                                },
                            ]
                        ),
                        "Version": "2012-10-17",
                    },
                    "PolicyName": Match.string_like_regexp(
                        "createtrainingjobsagemakerroleDefaultPolicy*"
                    ),
                    "Roles": [
                        {
                            "Ref": Match.string_like_regexp(
                                "createtrainingjobsagemakerrole*"
                            )
                        }
                    ],
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
                                        "KMSProvided",
                                        {"Ref": "KmsKeyArn"},
                                        {"Ref": "AWS::NoValue"},
                                    ]
                                },
                            }
                        ],
                        "Version": "2012-10-17",
                    },
                },
            )

            template.has_resource("AWS::IAM::Policy", {"Condition": "KMSProvided"})

    def test_training_lambda(self):
        """Tests for Training Lambda function"""
        for template in self.templates:
            template.has_resource_properties(
                "AWS::Lambda::Function",
                {
                    "Code": {
                        "S3Bucket": {"Ref": "BlueprintBucket"},
                        "S3Key": "blueprints/lambdas/create_model_training_job.zip",
                    },
                    "Role": {
                        "Fn::GetAtt": [
                            Match.string_like_regexp("trainingjoblambdarole*"),
                            "Arn",
                        ]
                    },
                    "Environment": {
                        "Variables": {
                            "JOB_NAME": {"Ref": "JobName"},
                            "ROLE_ARN": {
                                "Fn::GetAtt": [
                                    Match.string_like_regexp(
                                        "createtrainingjobsagemakerrole*"
                                    ),
                                    "Arn",
                                ]
                            },
                            "ASSETS_BUCKET": {"Ref": "AssetsBucket"},
                            "TRAINING_DATA_KEY": {"Ref": "TrainingData"},
                            "VALIDATION_DATA_KEY": {
                                "Fn::If": [
                                    "ValidationDataProvided",
                                    {"Ref": "ValidationData"},
                                    {"Ref": "AWS::NoValue"},
                                ]
                            },
                            "JOB_OUTPUT_LOCATION": {"Ref": "JobOutputLocation"},
                            "S3_DATA_TYPE": {"Ref": "S3DataType"},
                            "DATA_INPUT_MODE": {"Ref": "DataInputMode"},
                            "CONTENT_TYPE": {"Ref": "ContentType"},
                            "DATA_DISTRIBUTION": {"Ref": "DataDistribution"},
                            "ATTRIBUTE_NAMES": {
                                "Fn::If": [
                                    "AttributeNamesProvided",
                                    {"Ref": "AttributeNames"},
                                    {"Ref": "AWS::NoValue"},
                                ]
                            },
                            "JOB_TYPE": Match.string_like_regexp(
                                "(TrainingJob|HyperparameterTuningJob)"
                            ),
                            "KMS_KEY_ARN": {
                                "Fn::If": [
                                    "KMSProvided",
                                    {"Ref": "KmsKeyArn"},
                                    {"Ref": "AWS::NoValue"},
                                ]
                            },
                            "IMAGE_URI": {"Ref": "ImageUri"},
                            "INSTANCE_TYPE": {"Ref": "InstanceType"},
                            "INSTANCE_COUNT": {"Ref": "JobInstanceCount"},
                            "COMPRESSION_TYPE": {
                                "Fn::If": [
                                    "CompressionTypeProvided",
                                    {"Ref": "CompressionType"},
                                    {"Ref": "AWS::NoValue"},
                                ]
                            },
                            "DATA_RECORD_WRAPPING": {
                                "Fn::If": [
                                    "RecordWrappingProvided",
                                    {"Ref": "DataRecordWrapping"},
                                    {"Ref": "AWS::NoValue"},
                                ]
                            },
                            "INSTANCE_VOLUME_SIZE": {"Ref": "InstanceVolumeSize"},
                            "ENCRYPT_INTER_CONTAINER_TRAFFIC": {
                                "Ref": "EncryptInnerTraffic"
                            },
                            "JOB_MAX_RUN_SECONDS": {"Ref": "MaxRuntimePerJob"},
                            "USE_SPOT_INSTANCES": {"Ref": "UseSpotInstances"},
                            "MAX_WAIT_SECONDS": {"Ref": "MaxWaitTimeForSpotInstances"},
                            "HYPERPARAMETERS": {"Ref": "AlgoHyperparameteres"},
                            "TUNER_CONFIG": Match.any_value(),
                            "HYPERPARAMETER_RANGES": Match.any_value(),
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
                        Match.string_like_regexp("trainingjoblambdaroleDefaultPolicy*"),
                        Match.string_like_regexp("trainingjoblambdarole*"),
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
                                            "ModelTrainingLambda*"
                                        ),
                                        "Arn",
                                    ]
                                },
                            }
                        ],
                        "Version": "2012-10-17",
                    },
                    "PolicyName": Match.string_like_regexp(
                        "InvokeTrainingLambdaServiceRoleDefaultPolicy*"
                    ),
                    "Roles": [
                        {
                            "Ref": Match.string_like_regexp(
                                "InvokeTrainingLambdaServiceRole*"
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
                        "Fn::GetAtt": ["InvokeTrainingLambda77BDAF93", "Arn"]
                    },
                    "function_name": {"Ref": "ModelTrainingLambdaEB62AC60"},
                    "message": {
                        "Fn::Join": [
                            "",
                            [
                                "Invoking lambda function: ",
                                {"Ref": "ModelTrainingLambdaEB62AC60"},
                            ],
                        ]
                    },
                    "Resource": "InvokeLambda",
                    "assets_bucket": {"Ref": "AssetsBucket"},
                    "job_type": Match.string_like_regexp(
                        "(TrainingJob|HyperparameterTuningJob)"
                    ),
                    "job_name": {"Ref": "JobName"},
                    "training_data": {"Ref": "TrainingData"},
                    "validation_data": {
                        "Fn::If": [
                            "ValidationDataProvided",
                            {"Ref": "ValidationData"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    "s3_data_type": {"Ref": "S3DataType"},
                    "content_type": {"Ref": "ContentType"},
                    "data_distribution": {"Ref": "DataDistribution"},
                    "compression_type": {
                        "Fn::If": [
                            "CompressionTypeProvided",
                            {"Ref": "CompressionType"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    "data_input_mode": {"Ref": "DataInputMode"},
                    "data_record_wrapping": {
                        "Fn::If": [
                            "RecordWrappingProvided",
                            {"Ref": "DataRecordWrapping"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    "attribute_names": {
                        "Fn::If": [
                            "AttributeNamesProvided",
                            {"Ref": "AttributeNames"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    "hyperparameters": {"Ref": "AlgoHyperparameteres"},
                    "job_output_location": {"Ref": "JobOutputLocation"},
                    "image_uri": {"Ref": "ImageUri"},
                    "instance_type": {"Ref": "InstanceType"},
                    "instance_count": {"Ref": "JobInstanceCount"},
                    "instance_volume_size": {"Ref": "InstanceVolumeSize"},
                    "kms_key_arn": {
                        "Fn::If": [
                            "KMSProvided",
                            {"Ref": "KmsKeyArn"},
                            {"Ref": "AWS::NoValue"},
                        ]
                    },
                    "encrypt_inter_container_traffic": {"Ref": "EncryptInnerTraffic"},
                    "max_runtime_per_training_job_in_seconds": {
                        "Ref": "MaxRuntimePerJob"
                    },
                    "use_spot_instances": {"Ref": "UseSpotInstances"},
                    "max_wait_time_for_spot": {"Ref": "MaxWaitTimeForSpotInstances"},
                },
            )

            template.has_resource(
                "Custom::InvokeLambda",
                {
                    "DependsOn": [Match.string_like_regexp("ModelTrainingLambda*")],
                    "UpdateReplacePolicy": "Delete",
                    "DeletionPolicy": "Delete",
                },
            )

    def test_events_rule(self):
        """Tests for Events Rule"""
        self.training_job_template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Description": "EventBridge rule to notify the admin on the status change of the job",
                "EventPattern": {
                    "detail": {
                        "TrainingJobName": [{"Ref": "JobName"}],
                        "TrainingJobStatus": ["Completed", "Failed", "Stopped"],
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
                            "InputTemplate": '"The training job <detail-TrainingJobName> status is: <detail-TrainingJobStatus>."',
                        },
                    }
                ],
            },
        )

        self.tuner_job_template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "Description": "EventBridge rule to notify the admin on the status change of the job",
                "EventPattern": {
                    "detail": {
                        "HyperParameterTuningJobName": [{"Ref": "JobName"}],
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
                            "InputTemplate": '"The hyperparameter training job <detail-HyperParameterTuningJobName> status is: <detail-HyperParameterTuningJobStatus>."',
                        },
                    }
                ],
            },
        )

    def test_template_outputs(self):
        """Tests for templates outputs"""
        for template in self.templates:
            template.has_output(
                "TrainingJobName",
                {"Description": "The training job's name", "Value": {"Ref": "JobName"}},
            )

            template.has_output(
                "TrainingJobOutputLocation",
                {
                    "Description": "Output location of the training job",
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

            template.has_output(
                "TrainingDataLocation",
                {
                    "Description": "Training data used by the training job",
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

            template.has_output(
                "ValidationDataLocation",
                {
                    "Description": "Training data used by the training job",
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
