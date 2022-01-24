#######################################################################################################################
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
import pytest
from baselines_helper import SolutionSageMakerBaselines
from sagemaker.model_monitor.dataset_format import DatasetFormat
import sagemaker
from sagemaker.clarify import (
    DataConfig,
    BiasConfig,
    ModelConfig,
    ModelPredictedLabelConfig,
    SHAPConfig,
)

# create sagemaker session
sagemaker_session = sagemaker.session.Session()


@pytest.fixture
def mock_basic_data_quality_env():
    data_quality_env = {
        "MONITORING_TYPE": "DataQuality",
        "BASELINE_JOB_NAME": "test-baseline-job",
        "ASSETS_BUCKET": "testbucket",
        "SAGEMAKER_ENDPOINT_NAME": "Sagemaker-test-endpoint",
        "BASELINE_DATA_LOCATION": "baseline_data.csv",
        "BASELINE_JOB_OUTPUT_LOCATION": "s3://testbucket/baseline_output",
        "INSTANCE_TYPE": "ml.m5.large",
        "INSTANCE_VOLUME_SIZE": "20",
        "ROLE_ARN": "arn:aws:iam::account:role/myrole",
        "STACK_NAME": "test_stack",
        "LOG_LEVEL": "INFO",
        "ENDPOINT_NAME": "My-endpoint",
        "MODEL_PREDICTED_LABEL_CONFIG": json.dumps(dict(probability=0)),
        "BIAS_CONFIG": json.dumps(
            dict(
                label_values_or_threshold=[1],
                facet_name="age",
                facet_values_or_threshold=[40],
                group_name="personal_status_sex",
            )
        ),
    }

    return data_quality_env


@pytest.fixture
def mock_data_quality_env_with_optional_vars(mock_basic_data_quality_env):
    data_quality_env = mock_basic_data_quality_env.copy()
    data_quality_env.update(
        {
            "MAX_RUNTIME_SECONDS": "3300",
            "KMS_KEY_ARN": "arn:aws:kms:region:accountid:key/mykey",
        }
    )

    return data_quality_env


@pytest.fixture
def mock_model_quality_env_with_optional_vars(mock_data_quality_env_with_optional_vars):
    model_quality_env = mock_data_quality_env_with_optional_vars.copy()
    model_quality_env.update(
        {
            "MONITORING_TYPE": "ModelQuality",
            "PROBLEM_TYPE": "BinaryClassification",
            "GROUND_TRUTH_ATTRIBUTE": "label",
            "INFERENCE_ATTRIBUTE": "prediction",
            "PROBABILITY_ATTRIBUTE": "probability",
            "PROBABILITY_THRESHOLD_ATTRIBUTE": "0.5",
        }
    )

    return model_quality_env


@pytest.fixture
def mock_model_bias_env_with_optional_vars(mock_data_quality_env_with_optional_vars):
    model_bias_env = mock_data_quality_env_with_optional_vars.copy()
    model_bias_env.update(
        {
            "MONITORING_TYPE": "ModelBias",
            "BIAS_CONFIG": json.dumps(
                {"label_values_or_threshold": [1], "facet_name": "Account Length", "facet_values_or_threshold": [100]}
            ),
        }
    )

    return model_bias_env


@pytest.fixture
def mock_model_explainability_env_with_optional_vars(mock_data_quality_env_with_optional_vars):
    model_explainability_env = mock_data_quality_env_with_optional_vars.copy()
    model_explainability_env.update(
        {
            "MONITORING_TYPE": "ModelExplainability",
            "SHAP_CONFIG": json.dumps(
                {"baseline": "shap-baseline-data.csv", "num_samples": 500, "agg_method": "mean_abs"}
            ),
        }
    )

    return model_explainability_env


@pytest.fixture
def mocked_data_config():
    return DataConfig(s3_data_input_path="s3://test-bucket/data.csv", s3_output_path="s3://test-bucket/baseline_output")


@pytest.fixture
def mocked_model_config(monkeypatch, mock_model_quality_env_with_optional_vars):
    monkeypatch.setattr(os, "environ", mock_model_quality_env_with_optional_vars)
    return ModelConfig(model_name="sagemaker-model-1", instance_count=1, instance_type=os.environ["INSTANCE_TYPE"])


@pytest.fixture
def mocked_bias_config():
    return BiasConfig(label_values_or_threshold=[1], facet_name="age")


@pytest.fixture
def mocked_model_label_config():
    return ModelPredictedLabelConfig(probability_threshold=0.8)


@pytest.fixture
def mocked_baseline_dataset_header(monkeypatch, mock_model_quality_env_with_optional_vars):
    monkeypatch.setattr(os, "environ", mock_model_quality_env_with_optional_vars)
    return ["label", "feature_1", "feature_2", "feature_3", "feature_4"]


@pytest.fixture
def mocked_shap_config():
    return SHAPConfig(
        baseline=[
            [
                0.26124998927116394,
                0.2824999988079071,
                0.06875000149011612,
                0.38749998807907104,
                20.6512508392334,
            ]
        ],
        num_samples=100,
        agg_method="mean_abs",
    )


@pytest.fixture
def mocked_sagemaker_baseline_attributes(
    monkeypatch,
    mock_basic_data_quality_env,
    mock_data_quality_env_with_optional_vars,
    mock_model_quality_env_with_optional_vars,
    mock_model_bias_env_with_optional_vars,
    mock_model_explainability_env_with_optional_vars,
    mocked_data_config,
    mocked_bias_config,
    mocked_model_config,
    mocked_model_label_config,
    mocked_shap_config,
):
    def _mocked_sagemaker_baseline_attributes(monitoring_type, with_optional=False):
        # set the env variables based on monitoring_type, with_optional
        if monitoring_type == "DataQuality":
            if with_optional:
                envs = mock_data_quality_env_with_optional_vars
            else:
                envs = mock_basic_data_quality_env
        elif monitoring_type == "ModelQuality":
            envs = mock_model_quality_env_with_optional_vars
        elif monitoring_type == "ModelBias":
            envs = mock_model_bias_env_with_optional_vars
        else:
            envs = mock_model_explainability_env_with_optional_vars

        monkeypatch.setattr(os, "environ", envs)
        max_runtime_seconds = os.environ.get("MAX_RUNTIME_SECONDS")

        return {
            "monitoring_type": monitoring_type,
            "instance_type": os.environ.get("INSTANCE_TYPE", "ml.m5.large"),
            "instance_count": int(os.environ.get("INSTANCE_COUNT", "1")),
            "instance_volume_size": int(os.environ.get("INSTANCE_VOLUME_SIZE", "30")),
            "role_arn": os.environ["ROLE_ARN"],
            "baseline_job_name": os.environ["BASELINE_JOB_NAME"],
            "baseline_dataset": f"s3://{os.environ['ASSETS_BUCKET']}/{os.environ['BASELINE_DATA_LOCATION']}",
            "output_s3_uri": os.environ["BASELINE_JOB_OUTPUT_LOCATION"],
            "max_runtime_in_seconds": int(max_runtime_seconds) if max_runtime_seconds else None,
            "kms_key_arn": os.environ.get("KMS_KEY_ARN"),
            "problem_type": os.environ.get("PROBLEM_TYPE"),
            "ground_truth_attribute": os.environ.get("GROUND_TRUTH_ATTRIBUTE"),
            "inference_attribute": os.environ.get("INFERENCE_ATTRIBUTE"),
            "probability_attribute": os.environ.get("PROBABILITY_ATTRIBUTE"),
            "probability_threshold_attribute": os.environ.get("PROBABILITY_THRESHOLD_ATTRIBUTE"),
            "sagemaker_session": sagemaker_session,
            "data_config": mocked_data_config if monitoring_type in ["ModelBias", "ModelExplainability"] else None,
            "bias_config": mocked_bias_config if monitoring_type == "ModelBias" else None,
            "model_config": mocked_model_config if monitoring_type in ["ModelBias", "ModelExplainability"] else None,
            "model_predicted_label_config": mocked_model_label_config if monitoring_type == "ModelBias" else None,
            "explainability_config": mocked_shap_config if monitoring_type == "ModelExplainability" else None,
            "model_scores": None,
            "tags": [{"Key": "stack_name", "Value": os.environ["STACK_NAME"]}],
        }

    return _mocked_sagemaker_baseline_attributes


@pytest.fixture
def mocked_sagemaker_baselines_instance(mocked_sagemaker_baseline_attributes):
    def _mocked_sagemaker_baselines_instance(monitoring_type, with_optional=True):
        return SolutionSageMakerBaselines(**mocked_sagemaker_baseline_attributes(monitoring_type, with_optional))

    return _mocked_sagemaker_baselines_instance


@pytest.fixture
def mocked_expected_baseline_args(
    mocked_sagemaker_baselines_instance,
    mocked_data_config,
    mocked_model_config,
    mocked_bias_config,
    mocked_model_label_config,
    mocked_shap_config,
):
    def _mocked_expected_baseline_args(monitoring_type):
        sagemaker_baselines_instance = mocked_sagemaker_baselines_instance(monitoring_type)
        baseline_args = dict(
            # args passed to the Monitor class's construct
            class_args=dict(
                instance_type=sagemaker_baselines_instance.instance_type,
                instance_count=sagemaker_baselines_instance.instance_count,
                volume_size_in_gb=sagemaker_baselines_instance.instance_volume_size,
                role=sagemaker_baselines_instance.role_arn,
                max_runtime_in_seconds=sagemaker_baselines_instance.max_runtime_in_seconds,
                output_kms_key=sagemaker_baselines_instance.kms_key_arn,
                volume_kms_key=sagemaker_baselines_instance.kms_key_arn,
                sagemaker_session=sagemaker_baselines_instance.sagemaker_session,
                tags=sagemaker_baselines_instance.tags,
            ),
            # args passed to the Monitor class's suggest_baseline function
            suggest_args=dict(
                job_name=sagemaker_baselines_instance.baseline_job_name,
            ),
        )
        # add args valid only for DataQuality or ModelQuality
        if monitoring_type in ["DataQuality", "ModelQuality"]:
            baseline_args["suggest_args"].update(
                {
                    "dataset_format": DatasetFormat.csv(header=True),
                    "baseline_dataset": sagemaker_baselines_instance.baseline_dataset,
                    "output_s3_uri": sagemaker_baselines_instance.output_s3_uri,
                }
            )

        # add ModelQuality
        if monitoring_type == "ModelQuality":
            baseline_args["suggest_args"].update({"problem_type": sagemaker_baselines_instance.problem_type})
            if sagemaker_baselines_instance.problem_type in ["Regression", "MulticlassClassification"]:
                baseline_args["suggest_args"].update(
                    {"inference_attribute": sagemaker_baselines_instance.inference_attribute}
                )
            else:
                baseline_args["suggest_args"].update(
                    {"probability_attribute": sagemaker_baselines_instance.probability_attribute}
                )
                baseline_args["suggest_args"].update(
                    {"probability_threshold_attribute": sagemaker_baselines_instance.probability_threshold_attribute}
                )
            baseline_args["suggest_args"].update(
                {"ground_truth_attribute": sagemaker_baselines_instance.ground_truth_attribute}
            )

        # add ModelBias args
        if monitoring_type == "ModelBias":
            baseline_args["suggest_args"].update(
                {
                    "data_config": mocked_data_config,
                    "bias_config": mocked_bias_config,
                    "model_config": mocked_model_config,
                    "model_predicted_label_config": mocked_model_label_config,
                    "kms_key": sagemaker_baselines_instance.kms_key_arn,
                }
            )

        # add ModelBias args
        if monitoring_type == "ModelExplainability":
            baseline_args["suggest_args"].update(
                {
                    "data_config": mocked_data_config,
                    "explainability_config": mocked_shap_config,
                    "model_config": mocked_model_config,
                    "model_scores": None,
                    "kms_key": sagemaker_baselines_instance.kms_key_arn,
                }
            )
        return baseline_args

    return _mocked_expected_baseline_args


@pytest.fixture()
def event():
    return {
        "message": "Start data baseline job",
    }
