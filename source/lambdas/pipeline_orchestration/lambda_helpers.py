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
from shared.wrappers import BadRequest
from shared.helper import get_built_in_model_monitor_container_uri
from shared.logger import get_logger


logger = get_logger(__name__)


def template_url(pipeline_type):
    """
    template_url is a helper function that determines the cloudformation stack's file name based on
    inputs

    :pipeline_type: type of pipeline. Supported values:
    "byom_realtime_builtin"|"byom_realtime_custom"|"byom_batch_builtin"|"byom_batch_custom"|
    "byom_model_monitor"|"byom_image_builder"|"single_account_codepipeline"|
    "multi_account_codepipeline"

    :return: returns a link to the appropriate coudformation template files which can be one of these values:
    byom_realtime_inference_pipeline.yaml
    byom_batch_pipeline.yaml
    byom_model_monitor.yaml
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
        "byom_model_monitor": "blueprints/byom/byom_model_monitor.yaml",
        "byom_image_builder": f"{url}/byom_custom_algorithm_image_builder.yaml",
        "single_account_codepipeline": f"{url}/single_account_codepipeline.yaml",
        "multi_account_codepipeline": f"{url}/multi_account_codepipeline.yaml",
    }

    if pipeline_type in list(templates_map.keys()):
        return templates_map[pipeline_type]

    else:
        raise BadRequest(f"Bad request. Pipeline type: {pipeline_type} is not supported.")


def get_stage_param(event, api_key, stage):
    api_key_value = event.get(api_key, "")
    if isinstance(api_key_value, dict) and stage in list(api_key_value.keys()):
        api_key_value = api_key_value[stage]

    return api_key_value


def get_stack_name(event):
    pipeline_type = event.get("pipeline_type")
    pipeline_stack_name = os.environ["PIPELINE_STACK_NAME"]
    model_name = event.get("model_name", "").lower().strip()
    if pipeline_type in [
        "byom_realtime_builtin",
        "byom_realtime_custom",
        "byom_batch_builtin",
        "byom_batch_custom",
    ]:

        postfix = {
            "byom_realtime_builtin": "BYOMPipelineRealtimeBuiltIn",
            "byom_realtime_custom": "BYOMPipelineRealtimeCustom",
            "byom_batch_builtin": "BYOMPipelineBatchBuiltIn",
            "byom_batch_custom": "BYOMPipelineBatchCustom",
        }
        # name of stack
        provisioned_pipeline_stack_name = f"{pipeline_stack_name}-{model_name}-{postfix[pipeline_type]}"

    elif pipeline_type == "byom_model_monitor":
        provisioned_pipeline_stack_name = f"{pipeline_stack_name}-{model_name}-BYOMModelMonitor"

    elif pipeline_type == "byom_image_builder":
        image_tag = event.get("image_tag")
        provisioned_pipeline_stack_name = f"{pipeline_stack_name}-{image_tag}-BYOMPipelineImageBuilder"

    return provisioned_pipeline_stack_name.lower()


def get_template_parameters(event, is_multi_account, stage=None):
    pipeline_type = event.get("pipeline_type")
    region = os.environ["REGION"]

    kms_key_arn = get_stage_param(event, "kms_key_arn", stage)
    common_params = [
        ("ASSETSBUCKET", os.environ["ASSETS_BUCKET"]),
        ("KMSKEYARN", kms_key_arn),
        ("BLUEPRINTBUCKET", os.environ["BLUEPRINT_BUCKET"]),
    ]
    if pipeline_type in [
        "byom_realtime_builtin",
        "byom_realtime_custom",
        "byom_batch_builtin",
        "byom_batch_custom",
    ]:

        common_params.extend(get_common_realtime_batch_params(event, region, stage))

        # add realtime specfic parameters
        if pipeline_type in ["byom_realtime_builtin", "byom_realtime_custom"]:
            common_params.extend(get_realtime_specific_params(event, stage))
        # else add batch params
        else:
            common_params.extend(get_bacth_specific_params(event, stage))

        return common_params

    elif pipeline_type == "byom_model_monitor":
        common_params.extend(get_model_monitor_params(event, region, stage))
        return common_params

    elif pipeline_type == "byom_image_builder":
        return get_image_builder_params(event)

    else:
        raise BadRequest("Bad request format. Please provide a supported pipeline")


def get_codepipeline_params(is_multi_account, stack_name, template_zip_name, template_file_name):

    single_account_params = [
        ("NOTIFICATIONEMAIL", os.environ["NOTIFICATION_EMAIL"]),
        ("TEMPLATEZIPNAME", template_zip_name),
        ("TEMPLATEFILENAME", template_file_name),
        ("ASSETSBUCKET", os.environ["ASSETS_BUCKET"]),
        ("STACKNAME", stack_name),
    ]
    if is_multi_account == "False":
        single_account_params.extend([("TEMPLATEPARAMSNAME", "template_params.json")])
        return single_account_params

    else:
        single_account_params.extend(
            [
                ("DEVPARAMSNAME", "dev_template_params.json"),
                ("STAGINGPARAMSNAME", "staging_template_params.json"),
                ("PRODPARAMSNAME", "prod_template_params.json"),
                ("DEVACCOUNTID", os.environ["DEV_ACCOUNT_ID"]),
                ("DEVORGID", os.environ["DEV_ORG_ID"]),
                ("STAGINGACCOUNTID", os.environ["STAGING_ACCOUNT_ID"]),
                ("STAGINGORGID", os.environ["STAGING_ORG_ID"]),
                ("PRODACCOUNTID", os.environ["PROD_ACCOUNT_ID"]),
                ("PRODORGID", os.environ["PROD_ORG_ID"]),
                ("BLUEPRINTBUCKET", os.environ["BLUEPRINT_BUCKET"]),
            ]
        )

        return single_account_params


def get_common_realtime_batch_params(event, region, stage):
    inference_instance = get_stage_param(event, "inference_instance", stage)
    return [
        ("MODELNAME", event.get("model_name")),
        ("MODELARTIFACTLOCATION", event.get("model_artifact_location")),
        ("INFERENCEINSTANCE", inference_instance),
        ("CUSTOMALGORITHMSECRREPOARN", os.environ["ECR_REPO_ARN"]),
        ("IMAGEURI", get_image_uri(event.get("pipeline_type"), event, region)),
    ]


def clean_param(param):
    if param.endswith("/"):
        return param[:-1]
    else:
        return param


def get_realtime_specific_params(event, stage):
    data_capture_location = clean_param(get_stage_param(event, "data_capture_location", stage))
    return [("DATACAPTURELOCATION", data_capture_location)]


def get_bacth_specific_params(event, stage):
    batch_inference_data = get_stage_param(event, "batch_inference_data", stage)
    batch_job_output_location = clean_param(get_stage_param(event, "batch_job_output_location", stage))
    return [
        ("BATCHINPUTBUCKET", batch_inference_data.split("/")[0]),
        ("BATCHINFERENCEDATA", batch_inference_data),
        ("BATCHOUTPUTLOCATION", batch_job_output_location),
    ]


def get_model_monitor_params(event, region, stage):
    endpoint_name = get_stage_param(event, "endpoint_name", stage).lower().strip()
    monitoring_type = event.get("monitoring_type", "dataquality")

    # generate jobs names
    baseline_job_name = f"{endpoint_name}-baseline-job-{str(uuid.uuid4())[:4]}"
    monitoring_schedule_name = f"{endpoint_name}-monitor-{str(uuid.uuid4())[:4]}"

    baseline_job_output_location = clean_param(get_stage_param(event, "baseline_job_output_location", stage))
    data_capture_location = clean_param(get_stage_param(event, "baseline_job_output_location", stage))
    instance_type = get_stage_param(event, "instance_type", stage)
    instance_volume_size = get_stage_param(event, "instance_volume_size", stage)
    max_runtime_seconds = get_stage_param(event, "max_runtime_seconds", stage)
    monitoring_output_location = clean_param(get_stage_param(event, "monitoring_output_location", stage))
    schedule_expression = get_stage_param(event, "schedule_expression", stage)

    return [
        ("BASELINEJOBNAME", baseline_job_name),
        ("BASELINEOUTPUTBUCKET", baseline_job_output_location.split("/")[0]),
        ("BASELINEJOBOUTPUTLOCATION", baseline_job_output_location),
        ("DATACAPTUREBUCKET", data_capture_location.split("/")[0]),
        ("DATACAPTURELOCATION", data_capture_location),
        ("ENDPOINTNAME", endpoint_name),
        ("IMAGEURI", get_built_in_model_monitor_container_uri(region)),
        ("INSTANCETYPE", instance_type),
        ("INSTANCEVOLUMESIZE", instance_volume_size),
        ("MAXRUNTIMESECONDS", max_runtime_seconds),
        ("MONITORINGOUTPUTLOCATION", monitoring_output_location),
        ("MONITORINGSCHEDULENAME", monitoring_schedule_name),
        ("MONITORINGTYPE", monitoring_type),
        ("SCHEDULEEXPRESSION", schedule_expression),
        ("TRAININGDATA", event.get("training_data")),
    ]


def get_image_builder_params(event):
    return [
        ("NOTIFICATIONEMAIL", os.environ["NOTIFICATION_EMAIL"]),
        ("ASSETSBUCKET", os.environ["ASSETS_BUCKET"]),
        ("CUSTOMCONTAINER", event.get("custom_algorithm_docker")),
        ("ECRREPONAME", event.get("ecr_repo_name")),
        ("IMAGETAG", event.get("image_tag")),
    ]


def format_template_parameters(key_value_list, is_multi_account):
    if is_multi_account == "True":
        # for the multi-account option, the StackSet action, used by multi-account codepipeline,
        # requires this parameters format
        return [{"ParameterKey": param[0], "ParameterValue": param[1]} for param in key_value_list]
    else:
        # for single account option, the CloudFormation action, used by single-account codepipeline,
        # requires this parameters format
        return {"Parameters": {param[0]: param[1] for param in key_value_list}}


def write_params_to_json(params, file_path):
    with open(file_path, "w") as fp:
        json.dump(params, fp, indent=4)


def upload_file_to_s3(local_file_path, s3_bucket_name, s3_file_key, s3_client):
    s3_client.upload_file(local_file_path, s3_bucket_name, s3_file_key)


def download_file_from_s3(s3_bucket_name, file_key, local_file_path, s3_client):
    s3_client.download_file(s3_bucket_name, file_key, local_file_path)


def create_template_zip_file(
    event, blueprint_bucket, assets_bucket, template_url, template_zip_name, is_multi_account, s3_client
):
    zip_output_filename = "template"

    # create a tmpdir for the zip file to downlaod
    local_directory = tempfile.mkdtemp()
    local_file_path = os.path.join(local_directory, template_url.split("/")[-1])

    # downloawd the template from the blueprints bucket
    download_file_from_s3(blueprint_bucket, template_url, local_file_path, s3_client)

    # create tmpdir to zip clodformation and stages parameters
    zip_local_directory = tempfile.mkdtemp()
    zip_file_path = os.path.join(zip_local_directory, zip_output_filename)

    # downloawd the template from the blueprints bucket
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

    # uploda file
    upload_file_to_s3(
        f"{zip_file_path}.zip",
        assets_bucket,
        f"{template_zip_name}",
        s3_client,
    )


def get_image_uri(pipeline_type, event, region):
    if pipeline_type in ["byom_realtime_custom", "byom_batch_custom"]:
        return event.get("custom_image_uri")
    elif pipeline_type in ["byom_realtime_builtin", "byom_batch_builtin"]:
        return sagemaker.image_uris.retrieve(
            framework=event.get("model_framework"), region=region, version=event.get("model_framework_version")
        )
    else:
        raise Exception("Unsupported pipeline by get_image_uri function")


def get_required_keys(pipeline_type):
    # Realtime/batch pipelines
    if pipeline_type in [
        "byom_realtime_builtin",
        "byom_realtime_custom",
        "byom_batch_builtin",
        "byom_batch_custom",
    ]:
        common_keys = [
            "pipeline_type",
            "model_name",
            "model_artifact_location",
            "inference_instance",
        ]
        builtin_model_keys = [
            "model_framework",
            "model_framework_version",
        ]
        custom_model_keys = ["custom_image_uri"]
        realtime_specific_keys = ["data_capture_location"]
        batch_specific_keys = ["batch_inference_data", "batch_job_output_location"]

        keys_map = {
            "byom_realtime_builtin": common_keys + builtin_model_keys + realtime_specific_keys,
            "byom_realtime_custom": common_keys + custom_model_keys + realtime_specific_keys,
            "byom_batch_builtin": common_keys + builtin_model_keys + batch_specific_keys,
            "byom_batch_custom": common_keys + custom_model_keys + batch_specific_keys,
        }

        return keys_map[pipeline_type]

    # Model Monitor pipeline
    elif pipeline_type == "byom_model_monitor":
        return [
            "pipeline_type",
            "model_name",
            "endpoint_name",
            "training_data",
            "baseline_job_output_location",
            "data_capture_location",
            "monitoring_output_location",
            "schedule_expression",
            "instance_type",
            "instance_volume_size",
        ]
    # Image Builder pipeline
    elif pipeline_type == "byom_image_builder":
        return [
            "pipeline_type",
            "custom_algorithm_docker",
            "ecr_repo_name",
            "image_tag",
        ]

    else:
        raise BadRequest(
            "Bad request format. Pipeline type not supported. Check documentation for API & config formats"
        )


def validate(event):
    """
    validate is a helper function that checks if all required input parameters are present in the handler's event object

    :event: Lambda function's event object

    :return: returns the event back if it passes the validation othewise it raises a bad request exception
    :raises: BadRequest Exception
    """
    # get the required keys to validate the event
    required_keys = get_required_keys(event.get("pipeline_type", ""))
    for key in required_keys:
        if key not in event:
            logger.error(f"Request event did not have parameter: {key}")
            raise BadRequest(f"Bad request. API body does not have the necessary parameter: {key}")

    return event
