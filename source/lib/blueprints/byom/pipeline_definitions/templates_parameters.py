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
from aws_cdk import core


class ParameteresFactory:
    @staticmethod
    def create_notification_email_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "NotificationEmail",
            type="String",
            description="email for pipeline outcome notifications",
            allowed_pattern="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            constraint_description="Please enter an email address with correct format (example@example.com)",
            min_length=5,
            max_length=320,
        )

    @staticmethod
    def create_git_address_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "CodeCommitRepoAddress",
            type="String",
            description="AWS CodeCommit repository clone URL to connect to the framework.",
            allowed_pattern=(
                "^(((https:\/\/|ssh:\/\/)(git\-codecommit)\.[a-zA-Z0-9_.+-]+(amazonaws\.com\/)[a-zA-Z0-9-.]"
                "+(\/)[a-zA-Z0-9-.]+(\/)[a-zA-Z0-9-.]+$)|^$)"
            ),
            min_length=0,
            max_length=320,
            constraint_description=(
                "CodeCommit address must follow the pattern: ssh or "
                "https://git-codecommit.REGION.amazonaws.com/version/repos/REPONAME"
            ),
        )

    @staticmethod
    def create_existing_bucket_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "ExistingS3Bucket",
            type="String",
            description="Name of existing S3 bucket to be used for ML assets. S3 Bucket must be in the same region as the deployed stack, and has versioning enabled. If not provided, a new S3 bucket will be created.",
            allowed_pattern="((?=^.{3,63}$)(?!^(\d+\.)+\d+$)(^(([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])\.)*([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])$)|^$)",
            min_length=0,
            max_length=63,
        )

    @staticmethod
    def create_existing_ecr_repo_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "ExistingECRRepo",
            type="String",
            description="Name of existing Amazon ECR repository for custom algorithms. If not provided, a new ECR repo will be created.",
            allowed_pattern="((?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*|^$)",
            min_length=0,
            max_length=63,
        )

    @staticmethod
    def create_account_id_parameter(scope: core.Construct, id: str, account_type: str) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            id,
            type="String",
            description=f"AWS {account_type} account number where the CF template will be deployed",
            allowed_pattern="^\d{12}$",
        )

    @staticmethod
    def create_org_id_parameter(scope: core.Construct, id: str, account_type: str) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            id,
            type="String",
            description=f"AWS {account_type} organizational unit id where the CF template will be deployed",
            allowed_pattern="^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$",
        )

    @staticmethod
    def create_blueprint_bucket_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "BlueprintBucket",
            type="String",
            description="Bucket name for blueprints of different types of ML Pipelines.",
            min_length=3,
        )

    @staticmethod
    def create_data_capture_bucket_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "DataCaptureBucket",
            type="String",
            description="Bucket name where the data captured from SageMaker endpoint will be stored.",
            min_length=3,
        )

    @staticmethod
    def create_baseline_output_bucket_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "BaselineOutputBucket",
            type="String",
            description="Bucket name where the output of the baseline job will be stored.",
            min_length=3,
        )

    @staticmethod
    def create_batch_input_bucket_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "BatchInputBucket",
            type="String",
            description="Bucket name where the data input of the bact transform is stored.",
            min_length=3,
        )

    @staticmethod
    def create_assets_bucket_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "AssetsBucket",
            type="String",
            description="Bucket name where the model and baselines data are stored.",
            min_length=3,
        )

    @staticmethod
    def create_ground_truth_bucket_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "GroundTruthBucket",
            type="String",
            description="Bucket name where the ground truth data will be stored.",
            min_length=3,
        )

    @staticmethod
    def create_custom_algorithms_ecr_repo_arn_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "CustomAlgorithmsECRRepoArn",
            type="String",
            description="The arn of the Amazon ECR repository where custom algorithm image is stored (optional)",
            allowed_pattern="(^arn:aws:ecr:(us(-gov)?|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\\d:\\d{12}:repository/.+|^$)",
            constraint_description="Please enter valid ECR repo ARN",
            min_length=0,
            max_length=2048,
        )

    @staticmethod
    def create_kms_key_arn_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "KmsKeyArn",
            type="String",
            description="The KMS ARN to encrypt the output of the batch transform job and instance volume (optional).",
            allowed_pattern="(^arn:aws:kms:(us(-gov)?|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\d:\d{12}:key/.+|^$)",
            constraint_description="Please enter kmsKey ARN",
            min_length=0,
            max_length=2048,
        )

    @staticmethod
    def create_algorithm_image_uri_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "ImageUri",
            type="String",
            description="The algorithm image uri (build-in or custom)",
        )

    @staticmethod
    def create_model_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope, "ModelName", type="String", description="An arbitrary name for the model.", min_length=1
        )

    @staticmethod
    def create_stack_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope, "StackName", type="String", description="The name to assign to the deployed CF stack.", min_length=1
        )

    @staticmethod
    def create_endpoint_name_parameter(scope: core.Construct, optional=False) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "EndpointName",
            type="String",
            description="The name of the AWS SageMaker's endpoint",
            min_length=0 if optional else 1,
        )

    @staticmethod
    def create_model_artifact_location_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "ModelArtifactLocation",
            type="String",
            description="Path to model artifact inside assets bucket.",
        )

    @staticmethod
    def create_inference_instance_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "InferenceInstance",
            type="String",
            description="Inference instance that inference requests will be running on. E.g., ml.m5.large",
            allowed_pattern="^[a-zA-Z0-9_.+-]+\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            min_length=7,
        )

    @staticmethod
    def create_batch_inference_data_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "BatchInferenceData",
            type="String",
            description="S3 bucket path (including bucket name) to batch inference data file.",
        )

    @staticmethod
    def create_batch_job_output_location_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "BatchOutputLocation",
            type="String",
            description="S3 path (including bucket name) to store the results of the batch job.",
        )

    @staticmethod
    def create_data_capture_location_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "DataCaptureLocation",
            type="String",
            description="S3 path (including bucket name) to store captured data from the Sagemaker endpoint.",
            min_length=3,
        )

    @staticmethod
    def create_baseline_job_output_location_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "BaselineJobOutputLocation",
            type="String",
            description="S3 path (including bucket name) to store the Data Baseline Job's output.",
            min_length=3,
        )

    @staticmethod
    def create_monitoring_output_location_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "MonitoringOutputLocation",
            type="String",
            description="S3 path (including bucket name) to store the output of the Monitoring Schedule.",
            min_length=3,
        )

    @staticmethod
    def create_schedule_expression_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "ScheduleExpression",
            type="String",
            description="cron expression to run the monitoring schedule. E.g., cron(0 * ? * * *), cron(0 0 ? * * *), etc.",
            allowed_pattern="^cron(\\S+\\s){5}\\S+$",
        )

    @staticmethod
    def create_baseline_data_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "BaselineData",
            type="String",
            description="Location of the Baseline data in Assets S3 Bucket.",
        )

    @staticmethod
    def create_instance_type_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "InstanceType",
            type="String",
            description="EC2 instance type that model monitoring jobs will be running on. E.g., ml.m5.large",
            allowed_pattern="^[a-zA-Z0-9_.+-]+\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            min_length=7,
        )

    @staticmethod
    def create_instance_volume_size_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "InstanceVolumeSize",
            type="Number",
            description="Instance volume size used in model monitoring jobs. E.g., 20",
        )

    @staticmethod
    def create_baseline_max_runtime_seconds_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "BaselineMaxRuntimeSeconds",
            type="String",
            default="",
            description="Optional Maximum runtime in seconds the baseline job is allowed to run. E.g., 3600",
        )

    @staticmethod
    def create_monitor_max_runtime_seconds_parameter(scope: core.Construct, monitoring_type: str) -> core.CfnParameter:
        max_default = "1800" if monitoring_type in ["ModelQuality", "ModelBias"] else "3600"
        return core.CfnParameter(
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
    def create_baseline_job_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "BaselineJobName",
            type="String",
            description="Unique name of the data baseline job",
            min_length=3,
            max_length=63,
        )

    @staticmethod
    def create_monitoring_schedule_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "MonitoringScheduleName",
            type="String",
            description="Unique name of the monitoring schedule job",
            min_length=3,
            max_length=63,
        )

    @staticmethod
    def create_template_zip_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "TemplateZipFileName",
            type="String",
            allowed_pattern="^.*\.zip$",
            description="The zip file's name containing the CloudFormation template and its parameters files",
        )

    @staticmethod
    def create_template_file_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "TemplateFileName",
            type="String",
            allowed_pattern="^.*\.yaml$",
            description="CloudFormation template's file name",
        )

    @staticmethod
    def create_stage_params_file_name_parameter(scope: core.Construct, id: str, stage_type: str) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            id,
            type="String",
            allowed_pattern="^.*\.json$",
            description=f"parameters json file's name for the {stage_type} stage",
        )

    @staticmethod
    def create_custom_container_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
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
    def create_ecr_repo_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "ECRRepoName",
            type="String",
            description="Name of the Amazon ECR repository. This repo will be used to store custom algorithms images.",
            allowed_pattern="(?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*",
            min_length=1,
        )

    @staticmethod
    def create_image_tag_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope, "ImageTag", type="String", description="Docker image tag for the custom algorithm", min_length=1
        )

    @staticmethod
    def create_delegated_admin_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "DelegatedAdminAccount",
            type="String",
            allowed_values=["Yes", "No"],
            default="Yes",
            description="Is a delegated administrator account used to deploy accross account",
        )

    @staticmethod
    def create_detailed_error_message_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "AllowDetailedErrorMessage",
            type="String",
            allowed_values=["Yes", "No"],
            default="Yes",
            description="Allow including a detailed message of any server-side errors in the API call's response",
        )

    @staticmethod
    def create_use_model_registry_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "UseModelRegistry",
            type="String",
            allowed_values=["Yes", "No"],
            default="No",
            description="Will Amazon SageMaker's Model Registry be used to provision models?",
        )

    @staticmethod
    def create_model_registry_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "CreateModelRegistry",
            type="String",
            allowed_values=["Yes", "No"],
            default="No",
            description="Do you want the solution to create the SageMaker Model Package Group Name (i.e., Model Registry)",
        )

    @staticmethod
    def create_model_package_group_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "ModelPackageGroupName",
            type="String",
            description="SageMaker model package group name",
            min_length=0,
        )

    @staticmethod
    def create_model_package_name_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "ModelPackageName",
            allowed_pattern="(^arn:aws[a-z\-]*:sagemaker:[a-z0-9\-]*:[0-9]{12}:model-package/.*|^$)",
            type="String",
            description="The model name (version arn) in SageMaker's model package name group",
        )

    @staticmethod
    def create_instance_count_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "MonitoringJobInstanceCount",
            type="Number",
            default="1",
            description="Instance count used by model monitoring job. For example, 1",
        )

    @staticmethod
    def create_ground_truth_s3_uri_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "MonitorGroundTruthInput",
            type="String",
            description="Amazon S3 prefix that contains the ground truth data",
            min_length=3,
        )

    @staticmethod
    def create_problem_type_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "ProblemType",
            type="String",
            allowed_values=["Regression", "BinaryClassification", "MulticlassClassification"],
            description="Problem type. Possible values: Regression | BinaryClassification | MulticlassClassification",
        )

    @staticmethod
    def create_inference_attribute_parameter(scope: core.Construct, job_type: str) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            f"{job_type}InferenceAttribute",
            type="String",
            description="Index or JSONpath to locate predicted label(s)",
        )

    @staticmethod
    def create_probability_attribute_parameter(scope: core.Construct, job_type: str) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            f"{job_type}ProbabilityAttribute",
            type="String",
            description="Index or JSONpath to locate probabilities.",
        )

    @staticmethod
    def create_ground_truth_attribute_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "BaselineGroundTruthAttribute",
            type="String",
            description="Index or JSONpath to locate ground truth label.",
        )

    @staticmethod
    def create_probability_threshold_attribute_parameter(scope: core.Construct) -> core.CfnParameter:
        return core.CfnParameter(
            scope,
            "ProbabilityThresholdAttribute",
            type="String",
            description="Threshold to convert probabilities to binaries",
        )

    @staticmethod
    def create_model_predicted_label_config_parameter(scope):
        return core.CfnParameter(
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
        return core.CfnParameter(
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
        return core.CfnParameter(
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
        return core.CfnParameter(
            scope,
            "ExplainabilityModelScores",
            type="String",
            description=(
                "A Python int/str provided as a string (e.g., using json.dumps(5)) "
                "Index or JSONPath location in the model output for the predicted "
                "scores to be explained. This is not required if the model output is a single score."
            ),
        )

    @staticmethod
    def create_features_attribute_parameter(scope):
        return core.CfnParameter(
            scope,
            "FeaturesAttribute",
            type="String",
            description="Index or JSONpath to locate features",
        )


class ConditionsFactory:
    @staticmethod
    def create_custom_algorithms_ecr_repo_arn_provided_condition(
        scope: core.Construct, custom_algorithms_ecr_repo_arn: core.CfnParameter
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "CustomECRRepoProvided",
            expression=core.Fn.condition_not(
                core.Fn.condition_equals(custom_algorithms_ecr_repo_arn.value_as_string, "")
            ),
        )

    @staticmethod
    def create_kms_key_arn_provided_condition(
        scope: core.Construct, kms_key_arn: core.CfnParameter
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "KmsKeyProvided",
            expression=core.Fn.condition_not(core.Fn.condition_equals(kms_key_arn.value_as_string, "")),
        )

    @staticmethod
    def create_git_address_provided_condition(
        scope: core.Construct, git_address: core.CfnParameter
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "GitAddressProvided",
            expression=core.Fn.condition_not(core.Fn.condition_equals(git_address.value_as_string, "")),
        )

    @staticmethod
    def create_existing_bucket_provided_condition(
        scope: core.Construct, existing_bucket: core.CfnParameter
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "S3BucketProvided",
            expression=core.Fn.condition_not(core.Fn.condition_equals(existing_bucket.value_as_string, "")),
        )

    @staticmethod
    def create_existing_ecr_provided_condition(
        scope: core.Construct, existing_ecr_repo: core.CfnParameter
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "ECRProvided",
            expression=core.Fn.condition_not(core.Fn.condition_equals(existing_ecr_repo.value_as_string, "")),
        )

    @staticmethod
    def create_new_bucket_condition(scope: core.Construct, existing_bucket: core.CfnParameter) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "CreateS3Bucket",
            expression=core.Fn.condition_equals(existing_bucket.value_as_string, ""),
        )

    @staticmethod
    def create_new_ecr_repo_condition(scope: core.Construct, existing_ecr_repo: core.CfnParameter) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "CreateECRRepo",
            expression=core.Fn.condition_equals(existing_ecr_repo.value_as_string, ""),
        )

    @staticmethod
    def create_delegated_admin_condition(
        scope: core.Construct, delegated_admin_parameter: core.CfnParameter
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "UseDelegatedAdmin",
            expression=core.Fn.condition_equals(delegated_admin_parameter.value_as_string, "Yes"),
        )

    @staticmethod
    def create_model_registry_condition(
        scope: core.Construct, create_model_registry: core.CfnParameter
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "CreateModelRegistryCondition",
            expression=core.Fn.condition_equals(create_model_registry.value_as_string, "Yes"),
        )

    @staticmethod
    def create_model_registry_provided_condition(
        scope: core.Construct, model_package_name: core.CfnParameter
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "ModelRegistryProvided",
            expression=core.Fn.condition_not(core.Fn.condition_equals(model_package_name.value_as_string, "")),
        )

    @staticmethod
    def create_endpoint_name_provided_condition(
        scope: core.Construct, endpoint_name: core.CfnParameter
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "EndpointNameProvided",
            expression=core.Fn.condition_not(core.Fn.condition_equals(endpoint_name.value_as_string, "")),
        )

    @staticmethod
    def create_problem_type_binary_classification_attribute_provided_condition(
        scope: core.Construct, problem_type: core.CfnParameter, attribute: core.CfnParameter, attribute_name: str
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            f"ProblemTypeBinaryClassification{attribute_name}Provided",
            expression=core.Fn.condition_and(
                core.Fn.condition_equals(problem_type.value_as_string, "BinaryClassification"),
                core.Fn.condition_not(core.Fn.condition_equals(attribute.value_as_string, "")),
            ),
        )

    @staticmethod
    def create_problem_type_binary_classification_condition(
        scope: core.Construct, problem_type: core.CfnParameter
    ) -> core.CfnCondition:
        return core.CfnCondition(
            scope,
            "ProblemTypeBinaryClassification",
            expression=core.Fn.condition_equals(problem_type.value_as_string, "BinaryClassification"),
        )

    @staticmethod
    def create_attribute_provided_condition(scope, logical_id, attribute):
        return core.CfnCondition(
            scope,
            logical_id,
            expression=core.Fn.condition_not(core.Fn.condition_equals(attribute, "")),
        )
