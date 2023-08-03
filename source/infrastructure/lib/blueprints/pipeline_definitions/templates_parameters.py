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
from constructs import Construct
from aws_cdk import CfnParameter, CfnCondition, Fn


class ParameteresFactory:
    @staticmethod
    def create_notification_email_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "NotificationEmail",
            type="String",
            description="email for pipeline outcome notifications",
            allowed_pattern="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
            constraint_description="Please enter an email address with correct format (example@example.com)",
            min_length=5,
            max_length=320,
        )

    @staticmethod
    def create_git_address_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "CodeCommitRepoAddress",
            type="String",
            description="AWS CodeCommit repository clone URL to connect to the framework.",
            allowed_pattern=(
                "^(((https:\\/\\/|ssh:\\/\\/)(git\\-codecommit)\\.[a-zA-Z0-9_.+-]+(amazonaws\\.com\\/)[a-zA-Z0-9-.]"
                "+(\\/)[a-zA-Z0-9-.]+(\\/)[a-zA-Z0-9-.]+$)|^$)"
            ),
            min_length=0,
            max_length=320,
            constraint_description=(
                "CodeCommit address must follow the pattern: ssh or "
                "https://git-codecommit.REGION.amazonaws.com/version/repos/REPONAME"
            ),
        )

    @staticmethod
    def create_existing_bucket_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "ExistingS3Bucket",
            type="String",
            description="Name of existing S3 bucket to be used for ML assets. S3 Bucket must be in the same region as the deployed stack, and has versioning enabled. If not provided, a new S3 bucket will be created.",
            allowed_pattern="((?=^.{3,63}$)(?!^(\\d+\\.)+\\d+$)(^(([a-z0-9]|[a-z0-9][a-z0-9\\-]*[a-z0-9])\\.)*([a-z0-9]|[a-z0-9][a-z0-9\\-]*[a-z0-9])$)|^$)",
            min_length=0,
            max_length=63,
        )

    @staticmethod
    def create_existing_ecr_repo_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "ExistingECRRepo",
            type="String",
            description="Name of existing Amazon ECR repository for custom algorithms. If not provided, a new ECR repo will be created.",
            allowed_pattern="((?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*|^$)",
            min_length=0,
            max_length=63,
        )

    @staticmethod
    def create_account_id_parameter(
        scope: Construct, id: str, account_type: str
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            id,
            type="String",
            description=f"AWS {account_type} account number where the CF template will be deployed",
            allowed_pattern="^\\d{12}$",
        )

    @staticmethod
    def create_org_id_parameter(
        scope: Construct, id: str, account_type: str
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            id,
            type="String",
            description=f"AWS {account_type} organizational unit id where the CF template will be deployed",
            allowed_pattern="^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$",
        )

    @staticmethod
    def create_blueprint_bucket_name_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "BlueprintBucket",
            type="String",
            description="Bucket name for blueprints of different types of ML Pipelines.",
            min_length=3,
        )

    @staticmethod
    def create_data_capture_bucket_name_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "DataCaptureBucket",
            type="String",
            description="Bucket name where the data captured from SageMaker endpoint will be stored.",
            min_length=3,
        )

    @staticmethod
    def create_baseline_output_bucket_name_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "BaselineOutputBucket",
            type="String",
            description="Bucket name where the output of the baseline job will be stored.",
            min_length=3,
        )

    @staticmethod
    def create_batch_input_bucket_name_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "BatchInputBucket",
            type="String",
            description="Bucket name where the data input of the bact transform is stored.",
            min_length=3,
        )

    @staticmethod
    def create_assets_bucket_name_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "AssetsBucket",
            type="String",
            description="Bucket name where the model and baselines data are stored.",
            min_length=3,
        )

    @staticmethod
    def create_ground_truth_bucket_name_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "GroundTruthBucket",
            type="String",
            description="Bucket name where the ground truth data will be stored.",
            min_length=3,
        )

    @staticmethod
    def create_custom_algorithms_ecr_repo_arn_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "CustomAlgorithmsECRRepoArn",
            type="String",
            description="The arn of the Amazon ECR repository where custom algorithm image is stored (optional)",
            allowed_pattern="(^arn:(aws|aws-cn|aws-us-gov):ecr:(us(-gov)?|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\\d:\\d{12}:repository/.+|^$)",
            constraint_description="Please enter valid ECR repo ARN",
            min_length=0,
            max_length=2048,
        )

    @staticmethod
    def create_kms_key_arn_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "KmsKeyArn",
            type="String",
            description="The KMS ARN to encrypt the output of the batch transform job and instance volume (optional).",
            allowed_pattern="(^arn:(aws|aws-cn|aws-us-gov):kms:(us(-gov)?|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\\d:\\d{12}:key/.+|^$)",
            constraint_description="Please enter kmsKey ARN",
            min_length=0,
            max_length=2048,
        )

    @staticmethod
    def create_algorithm_image_uri_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "ImageUri",
            type="String",
            description="The algorithm image uri (build-in or custom)",
        )

    @staticmethod
    def create_model_name_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "ModelName",
            type="String",
            description="An arbitrary name for the model.",
            min_length=1,
        )

    @staticmethod
    def create_stack_name_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "StackName",
            type="String",
            description="The name to assign to the deployed CF stack.",
            min_length=1,
        )

    @staticmethod
    def create_endpoint_name_parameter(
        scope: Construct, optional=False
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "EndpointName",
            type="String",
            description="The name of the AWS SageMaker's endpoint",
            min_length=0 if optional else 1,
        )

    @staticmethod
    def create_model_artifact_location_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "ModelArtifactLocation",
            type="String",
            description="Path to model artifact inside assets bucket.",
        )

    @staticmethod
    def create_inference_instance_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "InferenceInstance",
            type="String",
            description="Inference instance that inference requests will be running on. E.g., ml.m5.large",
            allowed_pattern="^[a-zA-Z0-9_.+-]+\\.[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
            min_length=7,
        )

    @staticmethod
    def create_batch_inference_data_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "BatchInferenceData",
            type="String",
            description="S3 bucket path (including bucket name) to batch inference data file.",
        )

    @staticmethod
    def create_batch_job_output_location_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "BatchOutputLocation",
            type="String",
            description="S3 path (including bucket name) to store the results of the batch job.",
        )

    @staticmethod
    def create_data_capture_location_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "DataCaptureLocation",
            type="String",
            description="S3 path (including bucket name) to store captured data from the Sagemaker endpoint.",
            min_length=3,
        )

    @staticmethod
    def create_baseline_job_output_location_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "BaselineJobOutputLocation",
            type="String",
            description="S3 path (including bucket name) to store the Data Baseline Job's output.",
            min_length=3,
        )

    @staticmethod
    def create_monitoring_output_location_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "MonitoringOutputLocation",
            type="String",
            description="S3 path (including bucket name) to store the output of the Monitoring Schedule.",
            min_length=3,
        )

    @staticmethod
    def create_schedule_expression_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "ScheduleExpression",
            type="String",
            description="cron expression to run the monitoring schedule. E.g., cron(0 * ? * * *), cron(0 0 ? * * *), etc.",
            allowed_pattern="^cron(\\S+\\s){5}\\S+$",
        )

    @staticmethod
    def create_baseline_data_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "BaselineData",
            type="String",
            description="Location of the Baseline data in Assets S3 Bucket.",
        )

    @staticmethod
    def create_instance_type_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "InstanceType",
            type="String",
            description="EC2 instance type that model monitoring jobs will be running on. E.g., ml.m5.large",
            allowed_pattern="^[a-zA-Z0-9_.+-]+\\.[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
            min_length=7,
        )

    @staticmethod
    def create_instance_volume_size_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "InstanceVolumeSize",
            type="Number",
            description="Instance volume size used by the job. E.g., 20",
        )

    @staticmethod
    def create_baseline_max_runtime_seconds_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "BaselineMaxRuntimeSeconds",
            type="String",
            default="",
            description="Optional Maximum runtime in seconds the baseline job is allowed to run. E.g., 3600",
        )

    @staticmethod
    def create_monitor_max_runtime_seconds_parameter(
        scope: Construct, monitoring_type: str
    ) -> CfnParameter:
        max_default = (
            "1800" if monitoring_type in ["ModelQuality", "ModelBias"] else "3600"
        )
        return CfnParameter(
            scope,
            "MonitorMaxRuntimeSeconds",
            type="Number",
            default=max_default,
            description=(
                f" Required Maximum runtime in seconds the job is allowed to run the {monitoring_type} baseline job. "
                + "For data quality and model explainability, this can be up to 3600 seconds for an hourly schedule. "
                + "For model bias and model quality hourly schedules, this can be up to 1800 seconds."
            ),
            min_value=1,
            max_value=86400,
        )

    @staticmethod
    def create_baseline_job_name_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "BaselineJobName",
            type="String",
            description="Unique name of the data baseline job",
            min_length=3,
            max_length=63,
        )

    @staticmethod
    def create_monitoring_schedule_name_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "MonitoringScheduleName",
            type="String",
            description="Unique name of the monitoring schedule job",
            min_length=3,
            max_length=63,
        )

    @staticmethod
    def create_template_zip_name_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "TemplateZipFileName",
            type="String",
            allowed_pattern="^.*\\.zip$",
            description="The zip file's name containing the CloudFormation template and its parameters files",
        )

    @staticmethod
    def create_sns_topic_arn_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "NotificationsSNSTopicArn",
            type="String",
            allowed_pattern="^arn:\\S+:sns:\\S+:\\d{12}:\\S+$",
            description="AWS SNS Topics arn used by the MLOps Workload Orchestrator to notify the administrator.",
        )

    @staticmethod
    def create_template_file_name_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "TemplateFileName",
            type="String",
            allowed_pattern="^.*\\.yaml$",
            description="CloudFormation template's file name",
        )

    @staticmethod
    def create_stage_params_file_name_parameter(
        scope: Construct, id: str, stage_type: str
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            id,
            type="String",
            allowed_pattern="^.*\\.json$",
            description=f"parameters json file's name for the {stage_type} stage",
        )

    @staticmethod
    def create_custom_container_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "CustomImage",
            default="",
            type="String",
            description=(
                "Should point to a zip file containing dockerfile and assets for building a custom model. "
                "If empty it will be using containers from SageMaker Registry"
            ),
        )

    @staticmethod
    def create_ecr_repo_name_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "ECRRepoName",
            type="String",
            description="Name of the Amazon ECR repository. This repo will be used to store custom algorithms images.",
            allowed_pattern="(?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*",
            min_length=1,
        )

    @staticmethod
    def create_image_tag_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "ImageTag",
            type="String",
            description="Docker image tag for the custom algorithm",
            min_length=1,
        )

    @staticmethod
    def create_autopilot_job_name_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "JobName",
            type="String",
            allowed_pattern="^[a-zA-Z0-9](-*[a-zA-Z0-9]){0,62}",
            description="Unique name of the training job",
            min_length=1,
            max_length=63,
        )

    @staticmethod
    def create_delegated_admin_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "DelegatedAdminAccount",
            type="String",
            allowed_values=["Yes", "No"],
            default="Yes",
            description="Is a delegated administrator account used to deploy across account",
        )

    @staticmethod
    def create_detailed_error_message_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "AllowDetailedErrorMessage",
            type="String",
            allowed_values=["Yes", "No"],
            default="Yes",
            description="Allow including a detailed message of any server-side errors in the API call's response",
        )

    @staticmethod
    def create_use_model_registry_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "UseModelRegistry",
            type="String",
            allowed_values=["Yes", "No"],
            default="No",
            description="Will Amazon SageMaker's Model Registry be used to provision models?",
        )

    @staticmethod
    def create_model_registry_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "CreateModelRegistry",
            type="String",
            allowed_values=["Yes", "No"],
            default="No",
            description="Do you want the solution to create the SageMaker Model Package Group Name (i.e., Model Registry)",
        )

    @staticmethod
    def create_model_package_group_name_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "ModelPackageGroupName",
            type="String",
            description="SageMaker model package group name",
            min_length=0,
        )

    @staticmethod
    def create_model_package_name_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "ModelPackageName",
            allowed_pattern="(^arn:aws[a-z\\-]*:sagemaker:[a-z0-9\\-]*:[0-9]{12}:model-package/.*|^$)",
            type="String",
            description="The model name (version arn) in SageMaker's model package name group",
        )

    @staticmethod
    def create_instance_count_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "JobInstanceCount",
            type="Number",
            default="1",
            description="Instance count used by the job. For example, 1",
        )

    @staticmethod
    def create_ground_truth_s3_uri_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "MonitorGroundTruthInput",
            type="String",
            description="Amazon S3 prefix that contains the ground truth data",
            min_length=3,
        )

    @staticmethod
    def create_problem_type_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "ProblemType",
            type="String",
            allowed_values=[
                "Regression",
                "BinaryClassification",
                "MulticlassClassification",
            ],
            description="Problem type. Possible values: Regression | BinaryClassification | MulticlassClassification",
        )

    @staticmethod
    def create_autopilot_problem_type_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "ProblemType",
            type="String",
            default="",
            allowed_values=[
                "",
                "Regression",
                "BinaryClassification",
                "MulticlassClassification",
            ],
            description=(
                "Optional Problem type. Possible values: Regression | BinaryClassification | MulticlassClassification. "
                "If not provided, the Autopilot will infere the probelm type from the target attribute. "
                "Note: if ProblemType is provided, the AutopilotJobObjective must be provided too."
            ),
        )

    @staticmethod
    def create_inference_attribute_parameter(
        scope: Construct, job_type: str
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            f"{job_type}InferenceAttribute",
            type="String",
            description="Index or JSONpath to locate predicted label(s)",
        )

    @staticmethod
    def create_job_objective_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "AutopilotJobObjective",
            type="String",
            default="",
            allowed_values=["", "Accuracy", "MSE", "F1", "F1macro", "AUC"],
            description=(
                "Optional metric to optimize. If not provided, F1: used or binary classification, "
                "Accuracy: used for multiclass classification, and MSE: used for regression. "
                "Note: if AutopilotJobObjective is provided, the ProblemType must be provided too."
            ),
        )

    @staticmethod
    def create_max_runtime_per_job_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "MaxRuntimePerJob",
            type="Number",
            default=86400,
            description="Max runtime (in seconds) allowed per training job ",
            min_value=600,
            max_value=259200,
        )

    @staticmethod
    def create_total_job_runtime_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "AutopilotTotalRuntime",
            type="Number",
            default=2592000,
            description="Autopilot total runtime (in seconds) allowed for the job",
            min_value=3600,
            max_value=2592000,
        )

    @staticmethod
    def create_training_data_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "TrainingData",
            type="String",
            description="Training data key (located in the Assets bucket)",
            allowed_pattern=".*",
            min_length=1,
            max_length=128,
        )

    @staticmethod
    def create_validation_data_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "ValidationData",
            type="String",
            description="Optional Validation data S3 key (located in the Assets bucket)",
            allowed_pattern=".*",
            min_length=0,
            max_length=128,
        )

    @staticmethod
    def create_content_type_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "ContentType",
            type="String",
            default="csv",
            allowed_pattern=".*",
            description="The MIME type of the training data.",
            max_length=256,
        )

    @staticmethod
    def create_s3_data_type_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "S3DataType",
            type="String",
            default="S3Prefix",
            allowed_values=["S3Prefix", "ManifestFile", "AugmentedManifestFile"],
            description="Training S3 data type. S3Prefix | ManifestFile | AugmentedManifestFile.",
        )

    @staticmethod
    def create_data_distribution_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "DataDistribution",
            type="String",
            default="FullyReplicated",
            allowed_values=["FullyReplicated", "ShardedByS3Key"],
            description="Data distribution. FullyReplicated | ShardedByS3Key.",
        )

    @staticmethod
    def create_data_input_mode_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "DataInputMode",
            type="String",
            default="File",
            allowed_values=["File", "Pipe", "FastFile"],
            description="Training data input mode. File | Pipe | FastFile.",
        )

    @staticmethod
    def create_data_record_wrapping_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "DataRecordWrapping",
            type="String",
            default="",
            allowed_values=["", "RecordIO"],
            description="Optional training data record wrapping: RecordIO. ",
        )

    @staticmethod
    def create_target_attribute_name_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "TargetAttribute",
            type="String",
            description="Target attribute name in the training data",
            allowed_pattern=".*",
            min_length=1,
            max_length=128,
        )

    @staticmethod
    def create_max_wait_time_for_spot_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "MaxWaitTimeForSpotInstances",
            type="Number",
            default=172800,
            description=(
                "Max wait time (in seconds) for Spot instances (required if use_spot_instances = True). "
                "Must be greater than MaxRuntimePerJob."
            ),
            min_value=1,
            max_value=259200,
        )

    @staticmethod
    def create_job_output_location_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "JobOutputLocation",
            type="String",
            description="S3 output prefix (located in the Assets bucket)",
            allowed_pattern=".*",
            min_length=1,
            max_length=128,
        )

    @staticmethod
    def create_encrypt_inner_traffic_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "EncryptInnerTraffic",
            type="String",
            default="True",
            allowed_values=["True", "False"],
            description="Encrypt inner-container traffic for the job",
        )

    @staticmethod
    def create_generate_definitions_only_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "GenerateDefinitionsOnly",
            type="String",
            default="False",
            allowed_values=["True", "False"],
            description="generate candidate definitions only by the autopilot job",
        )

    @staticmethod
    def create_compression_type_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "CompressionType",
            type="String",
            default="",
            allowed_values=["", "Gzip"],
            description="Optional compression type for the training data",
        )

    @staticmethod
    def create_max_candidates_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "AutopilotMaxCandidates",
            default=10,
            type="Number",
            description="Max number of candidates to be tried by teh autopilot job",
            min_value=1,
        )

    @staticmethod
    def create_use_spot_instances_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "UseSpotInstances",
            type="String",
            default="True",
            allowed_values=["True", "False"],
            description="Use managed spot instances with the training job.",
        )

    @staticmethod
    def create_hyperparameters_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "AlgoHyperparameteres",
            type="String",
            description="Algorithm hyperparameters provided as a json object",
            allowed_pattern="^\\{(.*:.*)+\\}$",
        )

    @staticmethod
    def create_attribute_names_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "AttributeNames",
            type="String",
            description=(
                "Optional list of one or more attribute names to use that are found in "
                "a specified AugmentedManifestFile (if S3DataType='AugmentedManifestFile')"
            ),
            allowed_pattern="(^\\[.*\\]$|^$)",
        )

    @staticmethod
    def create_tuner_config_parameter(scope: Construct) -> CfnParameter:
        return CfnParameter(
            scope,
            "HyperparametersTunerConfig",
            type="String",
            description=(
                "sagemaker.tuner.HyperparameterTuner configs (objective_metric_name, metric_definitions, strategy, "
                "objective_type, max_jobs, max_parallel_jobs, base_tuning_job_name=None, early_stopping_type) "
                "provided as a json object. Note: some has default values and are not required to be specified. "
                "Example: {'early_stopping_type' = 'Auto', 'objective_metric_name' = 'validation:auc', 'max_jobs' = 10, 'max_parallel_jobs' = 2}"
            ),
            allowed_pattern="^\\{(.*:.*)+\\}$",
        )

    @staticmethod
    def create_hyperparameters_range_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "AlgoHyperparameteresRange",
            type="String",
            description=(
                "Algorithm hyperparameters range used by the Hyperparameters job provided as a json object, "
                "where the key is hyperparameter name, and the value is list with the first item the type "
                "('continuous'|'integer'|'categorical')  and the second item is a list of [min_value, max_value] for "
                "'continuous'|'integer' and a list of values for 'categorical'. "
                'Example: {"min_child_weight": ["continuous",[0, 120]], "max_depth": ["integer",[1, 15]], "optimizer": '
                '["categorical", ["sgd", "Adam"]])}'
            ),
            allowed_pattern='^\\{.*:\\s*\\[\\s*("continuous"|"integer"|"categorical")\\s*,\\s*\\[.*\\]\\s*\\]+\\s*\\}$',
        )

    @staticmethod
    def create_probability_attribute_parameter(
        scope: Construct, job_type: str
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            f"{job_type}ProbabilityAttribute",
            type="String",
            description="Index or JSONpath to locate probabilities.",
        )

    @staticmethod
    def create_ground_truth_attribute_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "BaselineGroundTruthAttribute",
            type="String",
            description="Index or JSONpath to locate ground truth label.",
        )

    @staticmethod
    def create_probability_threshold_attribute_parameter(
        scope: Construct,
    ) -> CfnParameter:
        return CfnParameter(
            scope,
            "ProbabilityThresholdAttribute",
            type="String",
            description="Threshold to convert probabilities to binaries",
        )

    @staticmethod
    def create_model_predicted_label_config_parameter(scope):
        return CfnParameter(
            scope,
            "ModelPredictedLabelConfig",
            type="String",
            description=(
                "Dictionary provided as a json of the"
                " sagemaker.clarify.ModelPredictedLabelConfig attributes ({'label':...,}). "
                "Optional for a regression problem."
            ),
        )

    @staticmethod
    def create_bias_config_parameter(scope):
        return CfnParameter(
            scope,
            "BiasConfig",
            type="String",
            description=(
                "Dictionary provided as a json using "
                "of the sagemaker.clarify.BiasConfig attributes ({'label_values_or_threshold':...,})."
            ),
            min_length=3,
        )

    @staticmethod
    def create_shap_config_parameter(scope):
        return CfnParameter(
            scope,
            "SHAPConfig",
            type="String",
            description=(
                "Dictionary provided as a json "
                "of the sagemaker.clarify.SHAPConfig attributes "
                "({'baseline':...,})."
            ),
            min_length=3,
        )

    @staticmethod
    def create_model_scores_parameter(scope):
        return CfnParameter(
            scope,
            "ExplainabilityModelScores",
            type="String",
            description=(
                "A Python int/str provided as a string (e.g., using json.dumps(5)) "
                "Index or JSONPath location in the model output for the predicted "
                "scores to be explained. This is not required if the model output is a single s"
            ),
        )

    @staticmethod
    def create_features_attribute_parameter(scope):
        return CfnParameter(
            scope,
            "FeaturesAttribute",
            type="String",
            description="Index or JSONpath to locate features",
        )


class ConditionsFactory:
    @staticmethod
    def create_custom_algorithms_ecr_repo_arn_provided_condition(
        scope: Construct, custom_algorithms_ecr_repo_arn: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "CustomECRRepoProvided",
            expression=Fn.condition_not(
                Fn.condition_equals(custom_algorithms_ecr_repo_arn.value_as_string, "")
            ),
        )

    @staticmethod
    def create_kms_key_arn_provided_condition(
        scope: Construct, kms_key_arn: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "KmsKeyProvided",
            expression=Fn.condition_not(
                Fn.condition_equals(kms_key_arn.value_as_string, "")
            ),
        )

    @staticmethod
    def create_git_address_provided_condition(
        scope: Construct, git_address: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "GitAddressProvided",
            expression=Fn.condition_not(
                Fn.condition_equals(git_address.value_as_string, "")
            ),
        )

    @staticmethod
    def create_existing_bucket_provided_condition(
        scope: Construct, existing_bucket: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "S3BucketProvided",
            expression=Fn.condition_not(
                Fn.condition_equals(existing_bucket.value_as_string, "")
            ),
        )

    @staticmethod
    def create_existing_ecr_provided_condition(
        scope: Construct, existing_ecr_repo: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "ECRProvided",
            expression=Fn.condition_not(
                Fn.condition_equals(existing_ecr_repo.value_as_string, "")
            ),
        )

    @staticmethod
    def create_new_bucket_condition(
        scope: Construct, existing_bucket: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "CreateS3Bucket",
            expression=Fn.condition_equals(existing_bucket.value_as_string, ""),
        )

    @staticmethod
    def create_new_ecr_repo_condition(
        scope: Construct, existing_ecr_repo: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "CreateECRRepo",
            expression=Fn.condition_equals(existing_ecr_repo.value_as_string, ""),
        )

    @staticmethod
    def create_delegated_admin_condition(
        scope: Construct, delegated_admin_parameter: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "UseDelegatedAdmin",
            expression=Fn.condition_equals(
                delegated_admin_parameter.value_as_string, "Yes"
            ),
        )

    @staticmethod
    def create_model_registry_condition(
        scope: Construct, create_model_registry: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "CreateModelRegistryCondition",
            expression=Fn.condition_equals(
                create_model_registry.value_as_string, "Yes"
            ),
        )

    @staticmethod
    def create_model_registry_provided_condition(
        scope: Construct, model_package_name: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "ModelRegistryProvided",
            expression=Fn.condition_not(
                Fn.condition_equals(model_package_name.value_as_string, "")
            ),
        )

    @staticmethod
    def create_endpoint_name_provided_condition(
        scope: Construct, endpoint_name: CfnParameter
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            "EndpointNameProvided",
            expression=Fn.condition_not(
                Fn.condition_equals(endpoint_name.value_as_string, "")
            ),
        )

    @staticmethod
    def create_problem_type_binary_classification_attribute_provided_condition(
        scope: Construct,
        problem_type: CfnParameter,
        attribute: CfnParameter,
        attribute_name: str,
    ) -> CfnCondition:
        return CfnCondition(
            scope,
            f"ProblemTypeBinaryClassification{attribute_name}Provided",
            expression=Fn.condition_and(
                Fn.condition_equals(
                    problem_type.value_as_string, "BinaryClassification"
                ),
                Fn.condition_not(Fn.condition_equals(attribute.value_as_string, "")),
            ),
        )

    @staticmethod
    def create_attribute_provided_condition(scope, logical_id, attribute):
        return CfnCondition(
            scope,
            logical_id,
            expression=Fn.condition_not(Fn.condition_equals(attribute, "")),
        )
