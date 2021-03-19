#######################################################################################################################
#  Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                       #
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
import pytest
import uuid


@pytest.fixture(autouse=True)
def mock_env_variables():
    os.environ["BLUEPRINT_BUCKET_URL"] = "testurl"
    os.environ["NOTIFICATION_EMAIL"] = "test@example.com"
    os.environ["ASSETS_BUCKET"] = "testassetsbucket"
    os.environ["BLUEPRINT_BUCKET"] = "testbucket"
    os.environ["PIPELINE_STACK_NAME"] = "teststack"
    os.environ["CFN_ROLE_ARN"] = "arn:aws:role:region:account:action"


@pytest.fixture
def api_byom_event():
    def _api_byom_event(inference_type, model_framework):
        event = {
            "pipeline_type": "byom",
            "model_name": "testmodel",
            "model_artifact_location": "model.tar.gz",
            "inference_instance": "ml.m5.large",
        }

        event["inference_type"] = inference_type
        if inference_type == "batch" and model_framework != "":
            event["batch_inference_data"] = "inference/data.csv"
            event["model_framework"] = "xgboost"
            event["model_framework_version"] = "0.90-1"
        elif inference_type == "realtime" and model_framework != "":
            event["model_framework"] = "xgboost"
            event["model_framework_version"] = "0.90-1"

        elif inference_type == "batch" and model_framework == "":
            event["custom_model_container"] = "my_custom_image.zip"
            event["batch_inference_data"] = "inference/data.csv"
        elif inference_type == "realtime" and model_framework == "":
            event["custom_model_container"] = "my_custom_image.zip"
        return event

    return _api_byom_event


@pytest.fixture
def required_api_byom_realtime_builtin():
    return [
        "pipeline_type",
        "model_name",
        "model_artifact_location",
        "inference_instance",
        "inference_type",
        "model_framework",
        "model_framework_version",
    ]


@pytest.fixture
def required_api_byom_batch_builtin():
    return [
        "pipeline_type",
        "model_name",
        "model_artifact_location",
        "inference_instance",
        "inference_type",
        "model_framework",
        "model_framework_version",
        "batch_inference_data",
    ]


@pytest.fixture
def required_api_byom_realtime_custom():
    return [
        "pipeline_type",
        "model_name",
        "model_artifact_location",
        "inference_instance",
        "inference_type",
        "custom_model_container",
    ]


@pytest.fixture
def required_api_byom_batch_custom():
    return [
        "pipeline_type",
        "model_name",
        "model_artifact_location",
        "inference_instance",
        "inference_type",
        "custom_model_container",
        "batch_inference_data",
    ]


@pytest.fixture
def api_model_monitor_event():
    def _api_model_monitor_event(monitoring_type=""):
        monitor_event = {
            "pipeline_type": "model_monitor",
            "endpoint_name": "xgb-churn-prediction-endpoint",
            "training_data": "model_monitor/training-dataset-with-header.csv",
            "baseline_job_output_location": "baseline_job_output",
            "monitoring_output_location": "monitoring_output",
            "schedule_expression": "cron(0 * ? * * *)",
            "instance_type": "ml.m5.large",
            "instance_volume_size": "20",
        }
        if monitoring_type.lower() != "" and monitoring_type.lower() in [
            "modelquality",
            "modelbias",
            "modelexplainability",
        ]:
            monitor_event["monitoring_type"] = monitoring_type.lower()
        return monitor_event

    return _api_model_monitor_event


@pytest.fixture
def required_api_keys_model_monitor():
    def _required_api_keys_model_monitor(default=True):
        default_keys = [
            "pipeline_type",
            "endpoint_name",
            "baseline_job_output_location",
            "monitoring_output_location",
            "schedule_expression",
            "training_data",
            "instance_type",
            "instance_volume_size",
        ]
        if default:
            return default_keys
        else:
            return default_keys + [
                "features_attribute",
                "inference_attribute",
                "probability_attribute",
                "probability_threshold_attribute",
            ]

    return _required_api_keys_model_monitor


@pytest.fixture
def template_parameters_common():
    def _template_parameters_common(event):
        template_parameters = [
            {
                "ParameterKey": "NOTIFICATIONEMAIL",
                "ParameterValue": os.environ["NOTIFICATION_EMAIL"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "BLUEPRINTBUCKET",
                "ParameterValue": os.environ["BLUEPRINT_BUCKET"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "ASSETSBUCKET",
                "ParameterValue": os.environ["ASSETS_BUCKET"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "MODELNAME",
                "ParameterValue": event["model_name"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "MODELARTIFACTLOCATION",
                "ParameterValue": event["model_artifact_location"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "INFERENCEINSTANCE",
                "ParameterValue": event["inference_instance"],
                "UsePreviousValue": True,
            },
        ]
        return template_parameters

    return _template_parameters_common


@pytest.fixture
def template_parameters_realtime_builtin(template_parameters_common):
    def _template_parameters_realtime_builtin(event):
        template_parameters = template_parameters_common(event)
        template_parameters.extend(
            [
                {
                    "ParameterKey": "MODELFRAMEWORK",
                    "ParameterValue": event["model_framework"],
                    "UsePreviousValue": True,
                },
                {
                    "ParameterKey": "MODELFRAMEWORKVERSION",
                    "ParameterValue": event["model_framework_version"],
                    "UsePreviousValue": True,
                },
            ]
        )

        return template_parameters

    return _template_parameters_realtime_builtin


@pytest.fixture
def template_parameters_batch_builtin(template_parameters_realtime_builtin):
    def _template_parameters_batch_builtin(event):
        template_parameters = template_parameters_realtime_builtin(event)
        template_parameters.extend(
            [
                {
                    "ParameterKey": "BATCHINFERENCEDATA",
                    "ParameterValue": event["batch_inference_data"],
                    "UsePreviousValue": True,
                },
            ]
        )

        return template_parameters

    return _template_parameters_batch_builtin


@pytest.fixture
def template_parameters_realtime_custom(template_parameters_common):
    def _template_parameters_realtime_custom(event):
        template_parameters = template_parameters_common(event)
        template_parameters.extend(
            [
                {
                    "ParameterKey": "CUSTOMCONTAINER",
                    "ParameterValue": event["custom_model_container"],
                    "UsePreviousValue": True,
                },
            ]
        )

        return template_parameters

    return _template_parameters_realtime_custom


@pytest.fixture
def template_parameters_batch_custom(template_parameters_realtime_custom):
    def _template_parameters_batch_custom(event):
        template_parameters = template_parameters_realtime_custom(event)
        template_parameters.extend(
            [
                {
                    "ParameterKey": "BATCHINFERENCEDATA",
                    "ParameterValue": event["batch_inference_data"],
                    "UsePreviousValue": True,
                },
            ]
        )

        return template_parameters

    return _template_parameters_batch_custom


@pytest.fixture
def generate_names():
    def _generate_names(endpoint_name, monitoring_type):
        baseline_job_name = f"{endpoint_name}-baseline-job-{str(uuid.uuid4())[:8]}"
        monitoring_schedule_name = f"{endpoint_name}-monitoring-schedule-{monitoring_type}-{str(uuid.uuid4())[:8]}"
        return (baseline_job_name, monitoring_schedule_name)

    return _generate_names


@pytest.fixture
def template_parameters_model_monitor(generate_names):
    def _template_parameters_model_monitor(event):
        baseline_job_name, monitoring_schedule_name = generate_names("test-endpoint", "dataquality")
        template_parameters = [
            {
                "ParameterKey": "NOTIFICATIONEMAIL",
                "ParameterValue": os.environ["NOTIFICATION_EMAIL"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "BLUEPRINTBUCKET",
                "ParameterValue": os.environ["BLUEPRINT_BUCKET"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "ASSETSBUCKET",
                "ParameterValue": os.environ["ASSETS_BUCKET"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "BASELINEJOBOUTPUTLOCATION",
                "ParameterValue": event.get("baseline_job_output_location"),
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "ENDPOINTNAME",
                "ParameterValue": event["endpoint_name"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "BASELINEJOBNAME",
                "ParameterValue": baseline_job_name,
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "MONITORINGSCHEDULENAME",
                "ParameterValue": monitoring_schedule_name,
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "MONITORINGOUTPUTLOCATION",
                "ParameterValue": event["monitoring_output_location"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "SCHEDULEEXPRESSION",
                "ParameterValue": event["schedule_expression"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "TRAININGDATA",
                "ParameterValue": event["training_data"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "INSTANCETYPE",
                "ParameterValue": event["instance_type"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "INSTANCEVOLUMESIZE",
                "ParameterValue": event["instance_volume_size"],
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "MONITORINGTYPE",
                "ParameterValue": event.get("monitoring_type", "dataquality"),
                "UsePreviousValue": True,
            },
            {
                "ParameterKey": "MAXRUNTIMESIZE",
                "ParameterValue": event.get("max_runtime_seconds", "-1"),
                "UsePreviousValue": True,
            },
        ]

        return template_parameters

    return _template_parameters_model_monitor


@pytest.fixture
def get_parameters_keys():
    def _get_parameters_keys(parameters):
        keys = [param["ParameterKey"] for param in parameters]
        return keys

    return _get_parameters_keys


@pytest.fixture
def cf_client_params(api_byom_event, template_parameters_realtime_builtin):
    template_parameters = template_parameters_realtime_builtin(api_byom_event("realtime", "xgboost"))
    cf_params = {
        "Capabilities": ["CAPABILITY_IAM"],
        "OnFailure": "DO_NOTHING",
        "Parameters": template_parameters,
        "RoleARN": "arn:aws:role:region:account:action",
        "StackName": "teststack-testmodel-byompipelinereatimebuiltin",
        "Tags": [{"Key": "stack_name", "Value": "teststack-testmodel-byompipelinereatimebuiltin"}],
        "TemplateURL": "https://testurl/blueprints/byom/byom_realtime_builtin_container.yaml",
    }
    return cf_params
