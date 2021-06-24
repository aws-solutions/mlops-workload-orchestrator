# #####################################################################################################################
#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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


def create_notification_email_parameter(scope):
    return core.CfnParameter(
        scope,
        "NOTIFICATION_EMAIL",
        type="String",
        description="email for pipeline outcome notifications",
        allowed_pattern="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        constraint_description="Please enter an email address with correct format (example@exmaple.com)",
        min_length=5,
        max_length=320,
    )


def create_git_address_parameter(scope):
    return core.CfnParameter(
        scope,
        "CodeCommit Repo Address",
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


def create_existing_bucket_parameter(scope):
    return core.CfnParameter(
        scope,
        "ExistingS3Bucket",
        type="String",
        description="Name of existing S3 bucket to be used for ML assests. S3 Bucket must be in the same region as the deployed stack, and has versioning enabled. If not provided, a new S3 bucket will be created.",
        allowed_pattern="((?=^.{3,63}$)(?!^(\d+\.)+\d+$)(^(([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])\.)*([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])$)|^$)",
        min_length=0,
        max_length=63,
    )


def create_existing_ecr_repo_parameter(scope):
    return core.CfnParameter(
        scope,
        "ExistingECRRepo",
        type="String",
        description="Name of existing Amazom ECR repository for custom algorithms. If not provided, a new ECR repo will be created.",
        allowed_pattern="((?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*|^$)",
        min_length=0,
        max_length=63,
    )


def create_account_id_parameter(scope, id, account_type):
    return core.CfnParameter(
        scope,
        id,
        type="String",
        description=f"AWS {account_type} account number where the CF template will be deployed",
        allowed_pattern="^\d{12}$",
    )


def create_org_id_parameter(scope, id, account_type):
    return core.CfnParameter(
        scope,
        id,
        type="String",
        description=f"AWS {account_type} organizational unit id where the CF template will be deployed",
        allowed_pattern="^ou-[0-9a-z]{4,32}-[a-z0-9]{8,32}$",
    )


def create_blueprint_bucket_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "BLUEPRINT_BUCKET",
        type="String",
        description="Bucket name for blueprints of different types of ML Pipelines.",
        min_length=3,
    )


def create_data_capture_bucket_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "DATA_CAPTURE_BUCKET",
        type="String",
        description="Bucket name where the data captured from SageMaker endpoint will be stored.",
        min_length=3,
    )


def create_baseline_output_bucket_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "BASELINE_OUTPUT_BUCKET",
        type="String",
        description="Bucket name where the output of the baseline job will be stored.",
        min_length=3,
    )


def create_batch_input_bucket_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "BATCH_INPUT_BUCKET",
        type="String",
        description="Bucket name where the data input of the bact transform is stored.",
        min_length=3,
    )


def create_assets_bucket_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "ASSETS_BUCKET",
        type="String",
        description="Bucket name where the model and training data are stored.",
        min_length=3,
    )


def create_custom_algorithms_ecr_repo_arn_parameter(scope):
    return core.CfnParameter(
        scope,
        "CUSTOM_ALGORITHMS_ECR_REPO_ARN",
        type="String",
        description="The arn of the Amazon ECR repository where custom algorithm image is stored (optional)",
        allowed_pattern="(^arn:aws:ecr:(us(-gov)?|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\\d:\\d{12}:repository/.+|^$)",
        constraint_description="Please enter valid ECR repo ARN",
        min_length=0,
        max_length=2048,
    )


def create_kms_key_arn_parameter(scope):
    return core.CfnParameter(
        scope,
        "KMS_KEY_ARN",
        type="String",
        description="The KMS ARN to encrypt the output of the batch transform job and instance volume (optional).",
        allowed_pattern="(^arn:aws:kms:(us(-gov)?|ap|ca|cn|eu|sa)-(central|(north|south)?(east|west)?)-\d:\d{12}:key/.+|^$)",
        constraint_description="Please enter kmsKey ARN",
        min_length=0,
        max_length=2048,
    )


def create_algorithm_image_uri_parameter(scope):
    return core.CfnParameter(
        scope,
        "IMAGE_URI",
        type="String",
        description="The algorithm image uri (build-in or custom)",
    )


def create_model_name_parameter(scope):
    return core.CfnParameter(
        scope, "MODEL_NAME", type="String", description="An arbitrary name for the model.", min_length=1
    )


def create_stack_name_parameter(scope):
    return core.CfnParameter(
        scope, "STACK_NAME", type="String", description="The name to assign to the deployed CF stack.", min_length=1
    )


def create_endpoint_name_parameter(scope):
    return core.CfnParameter(
        scope, "ENDPOINT_NAME", type="String", description="The name of the ednpoint to monitor", min_length=1
    )


def create_model_artifact_location_parameter(scope):
    return core.CfnParameter(
        scope,
        "MODEL_ARTIFACT_LOCATION",
        type="String",
        description="Path to model artifact inside assets bucket.",
    )


def create_inference_instance_parameter(scope):
    return core.CfnParameter(
        scope,
        "INFERENCE_INSTANCE",
        type="String",
        description="Inference instance that inference requests will be running on. E.g., ml.m5.large",
        allowed_pattern="^[a-zA-Z0-9_.+-]+\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        min_length=7,
    )


def create_batch_inference_data_parameter(scope):
    return core.CfnParameter(
        scope,
        "BATCH_INFERENCE_DATA",
        type="String",
        description="S3 bukcet path (including bucket name) to batch inference data file.",
    )


def create_batch_job_output_location_parameter(scope):
    return core.CfnParameter(
        scope,
        "BATCH_OUTPUT_LOCATION",
        type="String",
        description="S3 path (including bucket name) to store the results of the batch job.",
    )


def create_data_capture_location_parameter(scope):
    return core.CfnParameter(
        scope,
        "DATA_CAPTURE_LOCATION",
        type="String",
        description="S3 path (including bucket name) to store captured data from the Sagemaker endpoint.",
        min_length=3,
    )


def create_baseline_job_output_location_parameter(scope):
    return core.CfnParameter(
        scope,
        "BASELINE_JOB_OUTPUT_LOCATION",
        type="String",
        description="S3 path (including bucket name) to store the Data Baseline Job's output.",
        min_length=3,
    )


def create_monitoring_output_location_parameter(scope):
    return core.CfnParameter(
        scope,
        "MONITORING_OUTPUT_LOCATION",
        type="String",
        description="S3 path (including bucket name) to store the output of the Monitoring Schedule.",
        min_length=3,
    )


def create_schedule_expression_parameter(scope):
    return core.CfnParameter(
        scope,
        "SCHEDULE_EXPRESSION",
        type="String",
        description="cron expression to run the monitoring schedule. E.g., cron(0 * ? * * *), cron(0 0 ? * * *), etc.",
        allowed_pattern="^cron(\\S+\\s){5}\\S+$",
    )


def create_training_data_parameter(scope):
    return core.CfnParameter(
        scope,
        "TRAINING_DATA",
        type="String",
        description="Location of the training data in Assets S3 Bucket.",
    )


def create_instance_type_parameter(scope):
    return core.CfnParameter(
        scope,
        "INSTANCE_TYPE",
        type="String",
        description="EC2 instance type that model moniroing jobs will be running on. E.g., ml.m5.large",
        allowed_pattern="^[a-zA-Z0-9_.+-]+\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        min_length=7,
    )


def create_instance_volume_size_parameter(scope):
    return core.CfnParameter(
        scope,
        "INSTANCE_VOLUME_SIZE",
        type="Number",
        description="Instance volume size used in model moniroing jobs. E.g., 20",
    )


def create_monitoring_type_parameter(scope):
    return core.CfnParameter(
        scope,
        "MONITORING_TYPE",
        type="String",
        allowed_values=["dataquality", "modelquality", "modelbias", "modelexplainability"],
        default="dataquality",
        description="Type of model monitoring. Possible values: DataQuality | ModelQuality | ModelBias | ModelExplainability ",
    )


def create_max_runtime_seconds_parameter(scope):
    return core.CfnParameter(
        scope,
        "MAX_RUNTIME_SECONDS",
        type="Number",
        description="Max runtime in secodns the job is allowed to run. E.g., 3600",
    )


def create_baseline_job_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "BASELINE_JOB_NAME",
        type="String",
        description="Unique name of the data baseline job",
        min_length=3,
        max_length=63,
    )


def create_monitoring_schedule_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "MONITORING_SCHEDULE_NAME",
        type="String",
        description="Unique name of the monitoring schedule job",
        min_length=3,
        max_length=63,
    )


def create_template_zip_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "TEMPLATE_ZIP_NAME",
        type="String",
        allowed_pattern="^.*\.zip$",
        description="The zip file's name containing the CloudFormation template and its parameters files",
    )


def create_template_file_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "TEMPLATE_FILE_NAME",
        type="String",
        allowed_pattern="^.*\.yaml$",
        description="CloudFormation template's file name",
    )


def create_stage_params_file_name_parameter(scope, id, stage_type):
    return core.CfnParameter(
        scope,
        id,
        type="String",
        allowed_pattern="^.*\.json$",
        description=f"parameters json file's name for the {stage_type} stage",
    )


def create_custom_container_parameter(scope):
    return core.CfnParameter(
        scope,
        "CUSTOM_CONTAINER",
        default="",
        type="String",
        description=(
            "Should point to a zip file containing dockerfile and assets for building a custom model. "
            "If empty it will beusing containers from SageMaker Registry"
        ),
    )


def create_ecr_repo_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "ECR_REPO_NAME",
        type="String",
        description="Name of the Amazon ECR repository. This repo will be useed to store custom algorithms images.",
        allowed_pattern="(?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*",
        min_length=1,
    )


def create_image_tag_parameter(scope):
    return core.CfnParameter(
        scope, "IMAGE_TAG", type="String", description="Docker image tag for the custom algorithm", min_length=1
    )


def create_custom_algorithms_ecr_repo_arn_provided_condition(scope, custom_algorithms_ecr_repo_arn):
    return core.CfnCondition(
        scope,
        "CustomECRRepoProvided",
        expression=core.Fn.condition_not(core.Fn.condition_equals(custom_algorithms_ecr_repo_arn, "")),
    )


def create_kms_key_arn_provided_condition(scope, kms_key_arn):
    return core.CfnCondition(
        scope,
        "KMSKeyProvided",
        expression=core.Fn.condition_not(core.Fn.condition_equals(kms_key_arn, "")),
    )


def create_git_address_provided_condition(scope, git_address):
    return core.CfnCondition(
        scope,
        "GitAddressProvided",
        expression=core.Fn.condition_not(core.Fn.condition_equals(git_address, "")),
    )


def create_existing_bucket_provided_condition(scope, existing_bucket):
    return core.CfnCondition(
        scope,
        "S3BucketProvided",
        expression=core.Fn.condition_not(core.Fn.condition_equals(existing_bucket.value_as_string, "")),
    )


def create_existing_ecr_provided_condition(scope, existing_ecr_repo):
    return core.CfnCondition(
        scope,
        "ECRProvided",
        expression=core.Fn.condition_not(core.Fn.condition_equals(existing_ecr_repo.value_as_string, "")),
    )


def create_new_bucket_condition(scope, existing_bucket):
    return core.CfnCondition(
        scope,
        "CreateS3Bucket",
        expression=core.Fn.condition_equals(existing_bucket.value_as_string, ""),
    )


def create_new_ecr_repo_condition(scope, existing_ecr_repo):
    return core.CfnCondition(
        scope,
        "CreateECRRepo",
        expression=core.Fn.condition_equals(existing_ecr_repo.value_as_string, ""),
    )


def create_delegated_admin_parameter(scope):
    return core.CfnParameter(
        scope,
        "DELEGATED_ADMIN_ACCOUNT",
        type="String",
        allowed_values=["Yes", "No"],
        default="Yes",
        description="Is a delegated administrator account used to deploy accross account",
    )


def create_delegated_admin_condition(scope, delegated_admin_parameter):
    return core.CfnCondition(
        scope,
        "UseDelegatedAdmin",
        expression=core.Fn.condition_equals(delegated_admin_parameter.value_as_string, "Yes"),
    )


def create_use_model_registry_parameter(scope):
    return core.CfnParameter(
        scope,
        "USE_MODEL_REGISTRY",
        type="String",
        allowed_values=["Yes", "No"],
        default="No",
        description="Will Amazon SageMaker's Model Registry be used to provision models?",
    )


def create_model_registry_parameter(scope):
    return core.CfnParameter(
        scope,
        "CREATE_MODEL_REGISTRY",
        type="String",
        allowed_values=["Yes", "No"],
        default="No",
        description="Do you want the solution to create the SageMaker Model Package Group Name (i.e., Model Registry)",
    )


def create_model_registry_condition(scope, create_model_registry):
    return core.CfnCondition(
        scope,
        "CreateModelRegistryCondition",
        expression=core.Fn.condition_equals(create_model_registry.value_as_string, "Yes"),
    )


def create_model_package_group_name_parameter(scope):
    return core.CfnParameter(
        scope, "MODEL_PACKAGE_GROUP_NAME", type="String", description="SageMaker model package group name", min_length=0
    )


def create_model_package_name_parameter(scope):
    return core.CfnParameter(
        scope,
        "MODEL_PACKAGE_NAME",
        allowed_pattern="(^arn:aws[a-z\-]*:sagemaker:[a-z0-9\-]*:[0-9]{12}:model-package/.*|^$)",
        type="String",
        description="The model name (version arn) in SageMaker's model package name group",
    )


def create_model_registry_provided_condition(scope, model_package_name):
    return core.CfnCondition(
        scope,
        "ModelRegistryProvided",
        expression=core.Fn.condition_not(core.Fn.condition_equals(model_package_name, "")),
    )