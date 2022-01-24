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
import os
import json
import sagemaker
import shutil
import tempfile
import uuid
from typing import Dict, List, Tuple, Union, Any
from botocore.client import BaseClient
from shared.wrappers import BadRequest
from shared.logger import get_logger


logger = get_logger(__name__)


def template_url(pipeline_type: str) -> str:
    """
    template_url is a helper function that determines the cloudformation stack's file name based on
    inputs

    :pipeline_type: type of pipeline. Supported values:
    "byom_realtime_builtin"|"byom_realtime_custom"|"byom_batch_builtin"|"byom_batch_custom"|
    "byom_data_quality_monitor"|"byom_model_quality_monitor"|"byom_image_builder"|"single_account_codepipeline"|
    "multi_account_codepipeline"

    :return: returns a link to the appropriate cloudformation template files which can be one of these values:
    byom_realtime_inference_pipeline.yaml
    byom_batch_pipeline.yaml
    byom_data_quality_monitor.yaml
    byom_model_quality_monitor.yaml
    byom_model_bias_monitor.yaml
    byom_model_expainability_monitor.yaml
    byom_custom_algorithm_image_builder.yaml
    single_account_codepipeline.yaml
    multi_account_codepipeline.yaml
    """
    url = "https://" + os.environ["BLUEPRINT_BUCKET_URL"] + "/blueprints/byom"
    realtime_inference_template = "blueprints/byom/byom_realtime_inference_pipeline.yaml"
    batch_inference_template = "blueprints/byom/byom_batch_pipeline.yaml"

    templates_map = {
        "byom_realtime_builtin": realtime_inference_template,
        "byom_realtime_custom": realtime_inference_template,
        "byom_batch_builtin": batch_inference_template,
        "byom_batch_custom": batch_inference_template,
        "byom_data_quality_monitor": "blueprints/byom/byom_data_quality_monitor.yaml",
        "byom_model_quality_monitor": "blueprints/byom/byom_model_quality_monitor.yaml",
        "byom_model_bias_monitor": "blueprints/byom/byom_model_bias_monitor.yaml",
        "byom_model_explainability_monitor": "blueprints/byom/byom_model_explainability_monitor.yaml",
        "byom_image_builder": f"{url}/byom_custom_algorithm_image_builder.yaml",
        "single_account_codepipeline": f"{url}/single_account_codepipeline.yaml",
        "multi_account_codepipeline": f"{url}/multi_account_codepipeline.yaml",
    }

    if pipeline_type in list(templates_map.keys()):
        return templates_map[pipeline_type]

    else:
        raise BadRequest(f"Bad request. Pipeline type: {pipeline_type} is not supported.")


def get_stage_param(event: Dict[str, Any], api_key: str, stage: str) -> str:
    api_key_value = event.get(api_key, "")
    if isinstance(api_key_value, dict) and stage in list(api_key_value.keys()):
        api_key_value = api_key_value[stage]

    return api_key_value


def get_stack_name(event: Dict[str, Any]) -> str:
    pipeline_type = event.get("pipeline_type")
    pipeline_stack_name = os.environ["PIPELINE_STACK_NAME"]
    model_name = event.get("model_name", "").lower().strip()

    # create pipeline_type -> postfix map
    postfix = {
        "byom_realtime_builtin": "BYOMPipelineRealtimeBuiltIn",
        "byom_realtime_custom": "BYOMPipelineRealtimeCustom",
        "byom_batch_builtin": "BYOMPipelineBatchBuiltIn",
        "byom_batch_custom": "BYOMPipelineBatchCustom",
        "byom_data_quality_monitor": "BYOMDataQualityMonitor",
        "byom_model_quality_monitor": "BYOMModelQualityMonitor",
        "byom_model_bias_monitor": "BYOMModelBiasMonitor",
        "byom_model_explainability_monitor": "BYOMModelExplainabilityMonitor",
        "byom_image_builder": "BYOMPipelineImageBuilder",
    }

    # stack name's infix
    infix = event.get("image_tag") if pipeline_type == "byom_image_builder" else model_name

    # name of stack
    provisioned_pipeline_stack_name = f"{pipeline_stack_name}-{infix}-{postfix[pipeline_type]}"

    return provisioned_pipeline_stack_name.lower()


def get_template_parameters(event: Dict[str, Any], is_multi_account: bool, stage: str = None) -> List[Tuple[str, str]]:
    pipeline_type = event.get("pipeline_type")
    region = os.environ["REGION"]

    kms_key_arn = get_stage_param(event, "kms_key_arn", stage)
    common_params = [
        ("AssetsBucket", os.environ["ASSETS_BUCKET"]),
        ("KmsKeyArn", kms_key_arn),
        ("BlueprintBucket", os.environ["BLUEPRINT_BUCKET"]),
    ]

    # realtime params
    realtime_params = (
        [
            *common_params,
            *get_common_realtime_batch_params(event, region, stage),
            *get_realtime_specific_params(event, stage),
        ]
        if pipeline_type in ["byom_realtime_builtin", "byom_realtime_custom"]
        else None
    )
    # batch params
    batch_params = (
        [
            *common_params,
            *get_common_realtime_batch_params(event, region, stage),
            *get_batch_specific_params(event, stage),
        ]
        if pipeline_type in ["byom_batch_builtin", "byom_batch_custom"]
        else None
    )

    # create pipeline_type -> parameters map
    pipelines_params = {
        "byom_realtime_builtin": realtime_params,
        "byom_realtime_custom": realtime_params,
        "byom_batch_builtin": batch_params,
        "byom_batch_custom": batch_params,
        "byom_data_quality_monitor": [*common_params, *get_model_monitor_params(event, region, stage)]
        if pipeline_type == "byom_data_quality_monitor"
        else None,
        "byom_model_quality_monitor": [
            *common_params,
            *get_model_monitor_params(event, region, stage, monitoring_type="ModelQuality"),
        ]
        if pipeline_type == "byom_model_quality_monitor"
        else None,
        "byom_model_bias_monitor": [
            *common_params,
            *get_model_monitor_params(event, region, stage, monitoring_type="ModelBias"),
        ]
        if pipeline_type == "byom_model_bias_monitor"
        else None,
        "byom_model_explainability_monitor": [
            *common_params,
            *get_model_monitor_params(event, region, stage, monitoring_type="ModelExplainability"),
        ]
        if pipeline_type == "byom_model_explainability_monitor"
        else None,
        "byom_image_builder": [*get_image_builder_params(event)] if pipeline_type == "byom_image_builder" else None,
    }

    # get the pipeline's paramaters
    pipeline_params = pipelines_params.get(pipeline_type)

    # return the params if not NOne, otherwise throw a BadRequest exception
    if pipeline_params:
        return pipeline_params
    else:
        raise BadRequest("Bad request format. Please provide a supported pipeline")


def get_codepipeline_params(
    is_multi_account: str, stack_name: str, template_zip_name: str, template_file_name: str
) -> List[Tuple[str, str]]:

    single_account_params = [
        ("NotificationEmail", os.environ["NOTIFICATION_EMAIL"]),
        ("TemplateZipFileName", template_zip_name),
        ("TemplateFileName", template_file_name),
        ("AssetsBucket", os.environ["ASSETS_BUCKET"]),
        ("StackName", stack_name),
    ]
    if is_multi_account == "False":
        single_account_params.extend([("TemplateParamsName", "template_params.json")])
        return single_account_params

    else:
        single_account_params.extend(
            [
                ("DevParamsName", "dev_template_params.json"),
                ("StagingParamsName", "staging_template_params.json"),
                ("ProdParamsName", "prod_template_params.json"),
                ("DevAccountId", os.environ["DEV_ACCOUNT_ID"]),
                ("DevOrgId", os.environ["DEV_ORG_ID"]),
                ("StagingAccountId", os.environ["STAGING_ACCOUNT_ID"]),
                ("StagingOrgId", os.environ["STAGING_ORG_ID"]),
                ("ProdAccountId", os.environ["PROD_ACCOUNT_ID"]),
                ("ProdOrgId", os.environ["PROD_ORG_ID"]),
                ("BlueprintBucket", os.environ["BLUEPRINT_BUCKET"]),
                ("DelegatedAdminAccount", os.environ["IS_DELEGATED_ADMIN"]),
            ]
        )

        return single_account_params


def get_common_realtime_batch_params(event: Dict[str, Any], region: str, stage: str) -> List[Tuple[str, str]]:
    inference_instance = get_stage_param(event, "inference_instance", stage)
    image_uri = (
        get_image_uri(event.get("pipeline_type"), event, region) if os.environ["USE_MODEL_REGISTRY"] == "No" else ""
    )
    model_package_group_name = (
        # model_package_name example: arn:aws:sagemaker:us-east-1:<ACCOUNT_ID>:model-package/xgboost/1
        # the model_package_group_name in this case is "xgboost"
        event.get("model_package_name").split("/")[1]
        if os.environ["USE_MODEL_REGISTRY"] == "Yes"
        else ""
    )
    return [
        ("ModelName", event.get("model_name")),
        ("ModelArtifactLocation", event.get("model_artifact_location", "")),
        ("InferenceInstance", inference_instance),
        ("CustomAlgorithmsECRRepoArn", os.environ["ECR_REPO_ARN"]),
        ("ImageUri", image_uri),
        ("ModelPackageGroupName", model_package_group_name),
        ("ModelPackageName", event.get("model_package_name", "")),
    ]


def clean_param(param: str) -> str:
    # if the paramter's value ends with '/', remove it
    if param.endswith("/"):
        return param[:-1]
    else:
        return param


def get_realtime_specific_params(event: Dict[str, Any], stage: str) -> List[Tuple[str, str]]:
    data_capture_location = clean_param(get_stage_param(event, "data_capture_location", stage))
    endpoint_name = get_stage_param(event, "endpoint_name", stage).lower().strip()
    return [("DataCaptureLocation", data_capture_location), ("EndpointName", endpoint_name)]


def get_batch_specific_params(event: Dict[str, Any], stage: str) -> List[Tuple[str, str]]:
    batch_inference_data = get_stage_param(event, "batch_inference_data", stage)
    batch_job_output_location = clean_param(get_stage_param(event, "batch_job_output_location", stage))
    return [
        ("BatchInputBucket", batch_inference_data.split("/")[0]),
        ("BatchInferenceData", batch_inference_data),
        ("BatchOutputLocation", batch_job_output_location),
    ]


def get_built_in_model_monitor_image_uri(region, framework):
    model_monitor_image_uri = sagemaker.image_uris.retrieve(
        framework=framework,
        region=region,
    )

    return model_monitor_image_uri


def get_model_monitor_params(
    event: Dict[str, Any], region: str, stage: str, monitoring_type: str = "DataQuality"
) -> List[Tuple[str, str]]:
    endpoint_name = get_stage_param(event, "endpoint_name", stage).lower().strip()

    # generate jobs names
    # make sure baseline_job_name and monitoring_schedule_name are <= 63 characters long, especially
    # if endpoint_name was dynamically generated by AWS CDK.
    baseline_job_name = f"{endpoint_name}-{monitoring_type.lower()}-{str(uuid.uuid4())[:4]}"
    monitoring_schedule_name = f"{endpoint_name}-{monitoring_type.lower()}-{str(uuid.uuid4())[:4]}"

    baseline_job_output_location = clean_param(get_stage_param(event, "baseline_job_output_location", stage))
    data_capture_location = clean_param(get_stage_param(event, "data_capture_location", stage))
    instance_type = get_stage_param(event, "instance_type", stage)
    instance_volume_size = get_stage_param(event, "instance_volume_size", stage)
    baseline_max_runtime_seconds = get_stage_param(event, "baseline_max_runtime_seconds", stage)
    monitor_max_runtime_seconds = get_stage_param(event, "monitor_max_runtime_seconds", stage)
    monitoring_output_location = clean_param(get_stage_param(event, "monitoring_output_location", stage))
    schedule_expression = get_stage_param(event, "schedule_expression", stage)
    monitor_ground_truth_input = get_stage_param(event, "monitor_ground_truth_input", stage)

    # set the framework based on the monitoring type
    # DataQuality/ModelQuality -> framework="model-monitor"
    # ModelBias/ModelExplanability -> framework="clarify"
    monitor_framework = "model-monitor" if monitoring_type in ["DataQuality", "ModelQuality"] else "clarify"
    monitor_params = [
        ("BaselineJobName", baseline_job_name),
        ("BaselineOutputBucket", baseline_job_output_location.split("/")[0]),
        ("BaselineJobOutputLocation", f"{baseline_job_output_location}/{baseline_job_name}"),
        ("DataCaptureBucket", data_capture_location.split("/")[0]),
        ("DataCaptureLocation", data_capture_location),
        ("EndpointName", endpoint_name),
        ("ImageUri", get_built_in_model_monitor_image_uri(region, framework=monitor_framework)),
        ("InstanceType", instance_type),
        ("InstanceVolumeSize", instance_volume_size),
        ("BaselineMaxRuntimeSeconds", baseline_max_runtime_seconds),
        ("MonitorMaxRuntimeSeconds", monitor_max_runtime_seconds),
        ("MonitoringOutputLocation", monitoring_output_location),
        ("MonitoringScheduleName", monitoring_schedule_name),
        ("ScheduleExpression", schedule_expression),
        ("BaselineData", event.get("baseline_data")),
    ]

    # add ModelQuality specific params
    if monitoring_type == "ModelQuality":
        monitor_params.extend(
            [
                ("BaselineInferenceAttribute", event.get("baseline_inference_attribute", "").strip()),
                ("BaselineProbabilityAttribute", event.get("baseline_probability_attribute", "").strip()),
                ("BaselineGroundTruthAttribute", event.get("baseline_ground_truth_attribute", "").strip()),
            ]
        )
    # add ModelQuality parameters, also used by ModelBias/Model
    if monitoring_type in ["ModelQuality", "ModelBias", "ModelExplainability"]:
        monitor_params.extend(
            [
                ("ProblemType", event.get("problem_type", "").strip()),
                ("MonitorInferenceAttribute", event.get("monitor_inference_attribute", "").strip()),
                ("MonitorProbabilityAttribute", event.get("monitor_probability_attribute", "").strip()),
                ("ProbabilityThresholdAttribute", event.get("probability_threshold_attribute", "").strip()),
            ]
        )

    # only add MonitorGroundTruthInput if ModelQuality|ModelBias
    if monitoring_type in ["ModelQuality", "ModelBias"]:
        monitor_params.append(("GroundTruthBucket", monitor_ground_truth_input.split("/")[0]))
        monitor_params.append(("MonitorGroundTruthInput", monitor_ground_truth_input))

    # add ModelBias specific params
    if monitoring_type == "ModelBias":
        model_predicted_label_config = event.get("model_predicted_label_config")
        monitor_params.extend(
            [
                (
                    "ModelPredictedLabelConfig",
                    json.dumps(model_predicted_label_config) if model_predicted_label_config else "",
                ),
                ("BiasConfig", json.dumps(event.get("bias_config"))),
            ]
        )

    # add ModelExplainability specific params
    if monitoring_type == "ModelExplainability":
        shap_config = event.get("shap_config")
        model_scores = event.get("model_scores")
        monitor_params.extend(
            [
                ("SHAPConfig", json.dumps(shap_config) if shap_config else ""),
                ("ExplainabilityModelScores", json.dumps(model_scores) if model_scores else ""),
            ]
        )

    # add common params for ModelBias/ModelExplainability
    if monitoring_type in ["ModelBias", "ModelExplainability"]:

        monitor_params.extend(
            [
                ("FeaturesAttribute", event.get("features_attribute", "").strip()),
            ]
        )

    return monitor_params


def get_image_builder_params(event: Dict[str, Any]) -> List[Tuple[str, str]]:
    return [
        ("NotificationEmail", os.environ["NOTIFICATION_EMAIL"]),
        ("AssetsBucket", os.environ["ASSETS_BUCKET"]),
        ("CustomImage", event.get("custom_algorithm_docker")),
        ("ECRRepoName", event.get("ecr_repo_name")),
        ("ImageTag", event.get("image_tag")),
    ]


def format_template_parameters(
    key_value_list: List[str], is_multi_account: str
) -> Union[List[Dict[str, str]], Dict[str, Dict[str, str]]]:
    if is_multi_account == "True":
        # for the multi-account option, the StackSet action, used by multi-account codepipeline,
        # requires this parameters format
        return [{"ParameterKey": param[0], "ParameterValue": param[1]} for param in key_value_list]
    else:
        # for single account option, the CloudFormation action, used by single-account codepipeline,
        # requires this parameters format
        return {"Parameters": {param[0]: param[1] for param in key_value_list}}


def write_params_to_json(params: Union[List[Dict[str, str]], Dict[str, Dict[str, str]]], file_path: str) -> None:
    with open(file_path, "w") as fp:
        json.dump(params, fp, indent=4)


def upload_file_to_s3(local_file_path: str, s3_bucket_name: str, s3_file_key: str, s3_client: BaseClient) -> None:
    s3_client.upload_file(local_file_path, s3_bucket_name, s3_file_key)


def download_file_from_s3(s3_bucket_name: str, file_key: str, local_file_path: str, s3_client: BaseClient) -> None:
    s3_client.download_file(s3_bucket_name, file_key, local_file_path)


def create_template_zip_file(
    event: Dict[str, Any],
    blueprint_bucket: str,
    assets_bucket: str,
    template_url: str,
    template_zip_name: str,
    is_multi_account: str,
    s3_client: BaseClient,
) -> None:
    zip_output_filename = "template"

    # create a tmpdir for the zip file to download
    local_directory = tempfile.mkdtemp()
    local_file_path = os.path.join(local_directory, template_url.split("/")[-1])

    # download the template from the blueprints bucket
    download_file_from_s3(blueprint_bucket, template_url, local_file_path, s3_client)

    # create tmpdir to zip clodformation and stages parameters
    zip_local_directory = tempfile.mkdtemp()
    zip_file_path = os.path.join(zip_local_directory, zip_output_filename)

    # download the template from the blueprints bucket
    download_file_from_s3(blueprint_bucket, template_url, f"{local_directory}/{template_url.split('/')[-1]}", s3_client)

    # write the params to json file(s)
    if is_multi_account == "True":
        for stage in ["dev", "staging", "prod"]:
            # format the template params
            stage_params_list = get_template_parameters(event, is_multi_account, stage)
            params_formated = format_template_parameters(stage_params_list, is_multi_account)
            write_params_to_json(params_formated, f"{local_directory}/{stage}_template_params.json")
    else:
        stage_params_list = get_template_parameters(event, is_multi_account)
        params_formated = format_template_parameters(stage_params_list, is_multi_account)
        write_params_to_json(params_formated, f"{local_directory}/template_params.json")

    # make the zip file
    shutil.make_archive(
        zip_file_path,
        "zip",
        local_directory,
    )

    # upload file
    upload_file_to_s3(
        f"{zip_file_path}.zip",
        assets_bucket,
        f"{template_zip_name}",
        s3_client,
    )


def get_image_uri(pipeline_type: str, event: Dict[str, Any], region: str) -> str:
    if pipeline_type in ["byom_realtime_custom", "byom_batch_custom"]:
        return event.get("custom_image_uri")
    elif pipeline_type in ["byom_realtime_builtin", "byom_batch_builtin"]:
        return sagemaker.image_uris.retrieve(
            framework=event.get("model_framework"), region=region, version=event.get("model_framework_version")
        )
    else:
        raise ValueError("Unsupported pipeline by get_image_uri function")


def get_required_keys(pipeline_type: str, use_model_registry: str, problem_type: str = None) -> List[str]:

    common_keys = ["pipeline_type", "model_name", "inference_instance"]
    model_location = ["model_artifact_location"]
    builtin_model_keys = ["model_framework", "model_framework_version"] + model_location
    custom_model_keys = ["custom_image_uri"] + model_location
    # if model registry is used
    if use_model_registry == "Yes":
        builtin_model_keys = custom_model_keys = ["model_package_name"]

    realtime_specific_keys = ["data_capture_location"]
    batch_specific_keys = ["batch_inference_data", "batch_job_output_location"]

    # model monitor keys
    monitors = ["byom_model_quality_monitor", "byom_model_bias_monitor", "byom_model_explainability_monitor"]
    if pipeline_type in monitors and problem_type not in [
        "Regression",
        "MulticlassClassification",
        "BinaryClassification",
    ]:
        raise BadRequest("Bad request format. Unsupported problem_type in byom_model_quality_monitor pipeline")

    # common required keys between model monitor types
    common_monitor_keys = [
        "pipeline_type",
        "model_name",
        "endpoint_name",
        "baseline_data",
        "baseline_job_output_location",
        "data_capture_location",
        "monitoring_output_location",
        "schedule_expression",
        "monitor_max_runtime_seconds",
        "instance_type",
        "instance_volume_size",
    ]

    # ModelQuality specific keys
    model_quality_keys = ["baseline_inference_attribute", "baseline_ground_truth_attribute"]
    # common model related monitors
    common_model_keys = ["problem_type"]
    # add required keys based on problem type
    if problem_type in ["Regression", "MulticlassClassification"]:
        common_model_keys.append("monitor_inference_attribute")
    # problem_type == "BinaryClassification". Note: depending on the model output,
    # monitor_inference_attribute, monitor_probability_attribute, and probability_threshold_attribute
    # can be passed all together, or in pairs
    elif pipeline_type == "byom_model_quality_monitor":
        model_quality_keys.append("baseline_probability_attribute")

    # shared_model_quality_bias keys
    shared_model_quality_bias_keys = ["monitor_ground_truth_input"]

    # add model_predicted_label_config if "byom_model_bias_monitor" and
    # the problem is "BinaryClassification" or "MulticlassClassification"
    extra_bias_keys = []
    if pipeline_type == "byom_model_bias_monitor" and problem_type in [
        "BinaryClassification",
        "MulticlassClassification",
    ]:
        extra_bias_keys.append("model_predicted_label_config")

    # create pipeline_type -> required_keys map
    pipeline_keys_map = {
        "byom_realtime_builtin": [*common_keys, *builtin_model_keys, *realtime_specific_keys],
        "byom_realtime_custom": [*common_keys, *custom_model_keys, *realtime_specific_keys],
        "byom_batch_builtin": [*common_keys, *builtin_model_keys, *batch_specific_keys],
        "byom_batch_custom": [*common_keys, *custom_model_keys, *batch_specific_keys],
        "byom_data_quality_monitor": common_monitor_keys,
        "byom_model_quality_monitor": [
            *common_monitor_keys,
            *model_quality_keys,
            *common_model_keys,
            *shared_model_quality_bias_keys,
        ],
        "byom_model_bias_monitor": [
            *common_monitor_keys,
            *common_model_keys,
            *shared_model_quality_bias_keys,
            *extra_bias_keys,
            "bias_config",
        ],
        "byom_model_explainability_monitor": [
            *common_monitor_keys,
            *common_model_keys,
            "shap_config",
        ],
        "byom_image_builder": ["pipeline_type", "custom_algorithm_docker", "ecr_repo_name", "image_tag"],
    }

    # get the required keys based on the pipeline_type
    required_keys = pipeline_keys_map.get(pipeline_type)

    # return required_keys if not None. Otherwise, raise BadRequest exception
    if required_keys:
        return required_keys
    else:
        raise BadRequest(
            "Bad request format. Pipeline type not supported. Check documentation for API & config formats"
        )


def validate(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    validate is a helper function that checks if all required input parameters are present in the handler's event object

    :event: Lambda function's event object

    :return: returns the event back if it passes the validation otherwise it raises a bad request exception
    :raises: BadRequest Exception
    """
    # get the required keys to validate the event
    required_keys = get_required_keys(
        event.get("pipeline_type", "").strip(), os.environ["USE_MODEL_REGISTRY"], event.get("problem_type", "").strip()
    )
    for key in required_keys:
        if key not in event:
            logger.error(f"Request event did not have parameter: {key}")
            raise BadRequest(f"Bad request. API body does not have the necessary parameter: {key}")

    return event
