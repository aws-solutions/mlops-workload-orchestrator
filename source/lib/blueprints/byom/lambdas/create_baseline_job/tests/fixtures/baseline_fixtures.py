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
import pytest
from baselines_helper import SolutionSageMakerBaselines
from sagemaker.model_monitor.dataset_format import DatasetFormat
import sagemaker

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
        "INSTANCE_TYPE": "ml.m5.4xlarge",
        "INSTANCE_VOLUME_SIZE": "20",
        "ROLE_ARN": "arn:aws:iam::account:role/myrole",
        "STACK_NAME": "test_stack",
        "LOG_LEVEL": "INFO",
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
def mocked_sagemaker_baseline_attributes(
    monkeypatch,
    mock_basic_data_quality_env,
    mock_data_quality_env_with_optional_vars,
    mock_model_quality_env_with_optional_vars,
):
    def _mocked_sagemaker_baseline_attributes(monitoring_type, with_optional=False):
        # set the env variables based on monitoring_type, with_optional
        if monitoring_type == "DataQuality":
            if with_optional:
                envs = mock_data_quality_env_with_optional_vars
            else:
                envs = mock_basic_data_quality_env
        else:
            envs = mock_model_quality_env_with_optional_vars

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
            "tags": [{"Key": "stack_name", "Value": os.environ["STACK_NAME"]}],
        }

    return _mocked_sagemaker_baseline_attributes


@pytest.fixture
def mocked_sagemaker_baselines_instance(mocked_sagemaker_baseline_attributes):
    def _mocked_sagemaker_baselines_instance(monitoring_type, with_optional=True):
        return SolutionSageMakerBaselines(**mocked_sagemaker_baseline_attributes(monitoring_type, with_optional))

    return _mocked_sagemaker_baselines_instance


@pytest.fixture
def mocked_expected_baseline_args(mocked_sagemaker_baselines_instance):
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
                dataset_format=DatasetFormat.csv(header=True),
                baseline_dataset=sagemaker_baselines_instance.baseline_dataset,
                output_s3_uri=sagemaker_baselines_instance.output_s3_uri,
            ),
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
        return baseline_args

    return _mocked_expected_baseline_args


@pytest.fixture()
def event():
    return {
        "message": "Start data baseline job",
    }
