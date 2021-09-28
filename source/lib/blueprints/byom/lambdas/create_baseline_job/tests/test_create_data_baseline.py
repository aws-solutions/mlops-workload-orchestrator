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
from unittest.mock import patch
from unittest import TestCase
import pytest
import os
from main import handler
from tests.fixtures.baseline_fixtures import (
    mock_basic_data_quality_env,
    mock_data_quality_env_with_optional_vars,
    mock_model_quality_env_with_optional_vars,
    mocked_sagemaker_baseline_attributes,
    mocked_sagemaker_baselines_instance,
    mocked_expected_baseline_args,
    event,
)
from baselines_helper import SolutionSageMakerBaselines


def test_init(mocked_sagemaker_baseline_attributes):
    # test object creation based on MonitoringType and env variables
    # test DataQuality with Optional parameters (max_run_time and kms_key_arn) are not provided
    baselines = SolutionSageMakerBaselines(**mocked_sagemaker_baseline_attributes("DataQuality"))
    assert baselines.monitoring_type == os.environ["MONITORING_TYPE"]
    assert baselines.problem_type is None
    assert baselines.ground_truth_attribute is None
    assert baselines.inference_attribute is None
    assert baselines.probability_attribute is None
    assert baselines.probability_threshold_attribute is None
    assert baselines.max_runtime_in_seconds is None
    assert baselines.kms_key_arn is None

    # test DataQuality with Optional parameters are provided
    baselines = SolutionSageMakerBaselines(**mocked_sagemaker_baseline_attributes("DataQuality", with_optional=True))
    assert baselines.monitoring_type == os.environ["MONITORING_TYPE"]
    assert baselines.max_runtime_in_seconds == int(os.environ["MAX_RUNTIME_SECONDS"])
    assert baselines.kms_key_arn == os.environ["KMS_KEY_ARN"]

    # test ModelQuality with Optional parameters (max_run_time and kms_key_arn) are not provided
    baselines = SolutionSageMakerBaselines(**mocked_sagemaker_baseline_attributes("ModelQuality"))
    assert baselines.monitoring_type == os.environ["MONITORING_TYPE"]
    assert baselines.problem_type == os.environ["PROBLEM_TYPE"]
    assert baselines.ground_truth_attribute == os.environ["GROUND_TRUTH_ATTRIBUTE"]
    assert baselines.inference_attribute == os.environ["INFERENCE_ATTRIBUTE"]
    assert baselines.probability_attribute == os.environ["PROBABILITY_ATTRIBUTE"]
    assert baselines.probability_threshold_attribute == os.environ["PROBABILITY_THRESHOLD_ATTRIBUTE"]

    # test exception if non-supported monitoring type is passed
    with pytest.raises(ValueError) as error:
        SolutionSageMakerBaselines(**mocked_sagemaker_baseline_attributes("NotSupported"))
    assert str(error.value) == (
        "The provided monitoring type: NotSupported is not valid. It must be 'DataQuality'|'ModelQuality'"
    )


def test_get_baseline_job_args(
    mocked_sagemaker_baselines_instance, mocked_expected_baseline_args, mocked_sagemaker_baseline_attributes
):
    sagemaker_baselines = mocked_sagemaker_baselines_instance("DataQuality")
    # assert the returned baseline args for DataQuality baseline
    TestCase().assertDictEqual(
        sagemaker_baselines._get_baseline_job_args(), mocked_expected_baseline_args("DataQuality")
    )

    # assert the returned baseline args for ModelQuality baseline
    sagemaker_baselines = mocked_sagemaker_baselines_instance("ModelQuality")
    TestCase().assertDictEqual(
        sagemaker_baselines._get_baseline_job_args(), mocked_expected_baseline_args("ModelQuality")
    )

    # test BinaryClassification with only inference_attribute provided
    baseline_attributes = mocked_sagemaker_baseline_attributes("ModelQuality")
    baseline_attributes["probability_attribute"] = ""
    baseline_attributes["probability_threshold_attribute"] = None
    baseline_instance = SolutionSageMakerBaselines(**baseline_attributes)
    baseline_args = baseline_instance._get_baseline_job_args()
    assert baseline_args["suggest_args"]["problem_type"] == "BinaryClassification"
    assert baseline_args["suggest_args"]["inference_attribute"] == baseline_attributes["inference_attribute"]
    assert baseline_args["suggest_args"].get("probability_attribute") is None
    assert baseline_args["suggest_args"].get("probability_threshold_attribute") is None

    # test problem_type = "Regression"|"MulticlassClassification"
    baseline_attributes = mocked_sagemaker_baseline_attributes("ModelQuality")
    baseline_attributes["problem_type"] = "Regression"
    baseline_instance = SolutionSageMakerBaselines(**baseline_attributes)
    baseline_args = baseline_instance._get_baseline_job_args()
    assert baseline_args["suggest_args"]["problem_type"] == "Regression"
    assert baseline_args["suggest_args"]["inference_attribute"] == baseline_attributes["inference_attribute"]
    assert baseline_args["suggest_args"].get("probability_attribute") is None
    assert baseline_args["suggest_args"].get("probability_threshold_attribute") is None


def test_get_baseline_job_args_exceptions(mocked_sagemaker_baseline_attributes):
    # test exception if baseline_dataset is not provided
    baseline_attributes = mocked_sagemaker_baseline_attributes("ModelQuality")
    # provide an empty baseline_dataset
    baseline_attributes["baseline_dataset"] = ""
    with pytest.raises(ValueError) as error:
        baseline = SolutionSageMakerBaselines(**baseline_attributes)
        baseline._get_baseline_job_args()
    assert str(error.value) == "BaselineDataset S3Uri must be provided to create the ModelQuality baseline job"
    # reset value
    baseline_attributes["baseline_dataset"] = os.environ["BASELINE_DATA_LOCATION"]

    # test exception for unsupported problem_type
    baseline_attributes["problem_type"] = "Unsupported"
    with pytest.raises(ValueError) as error:
        baseline = SolutionSageMakerBaselines(**baseline_attributes)
        baseline._get_baseline_job_args()
    assert str(error.value) == (
        "The Unsupported is not valid. ProblemType must be "
        + "['Regression'|'BinaryClassification'|'MulticlassClassification']"
    )

    # test exception if inference_attribute not provided
    baseline_attributes["problem_type"] = "Regression"
    baseline_attributes["inference_attribute"] = ""
    with pytest.raises(ValueError) as error:
        baseline = SolutionSageMakerBaselines(**baseline_attributes)
        baseline._get_baseline_job_args()
    assert str(error.value) == (
        "InferenceAttribute must not be provided for ProblemType: Regression or MulticlassClassification"
    )

    # test exception if none of inference_attribute, probability_attribute and probability_threshold_attribute
    # in not provided for BinaryClassification problem
    baseline_attributes["problem_type"] = "BinaryClassification"
    baseline_attributes["inference_attribute"] = ""
    baseline_attributes["probability_attribute"] = ""
    baseline_attributes["probability_threshold_attribute"] = None
    with pytest.raises(ValueError) as error:
        baseline = SolutionSageMakerBaselines(**baseline_attributes)
        baseline._get_baseline_job_args()
    assert str(error.value) == (
        "InferenceAttribute or (ProbabilityAttribute/ProbabilityThresholdAttribute) must be provided "
        + "for ProblemType: BinaryClassification"
    )
    # reset values
    baseline_attributes["inference_attribute"] = os.environ["INFERENCE_ATTRIBUTE"]
    baseline_attributes["probability_attribute"] = os.environ["PROBABILITY_ATTRIBUTE"]
    baseline_attributes["probability_threshold_attribute"] = os.environ["PROBABILITY_THRESHOLD_ATTRIBUTE"]

    # test exception if ground_truth_attribute is not provides
    baseline_attributes["ground_truth_attribute"] = ""
    with pytest.raises(ValueError) as error:
        baseline = SolutionSageMakerBaselines(**baseline_attributes)
        baseline._get_baseline_job_args()
    assert str(error.value) == "GroundTruthAttribute must be provided"


@patch("baselines_helper.SolutionSageMakerBaselines._create_model_quality_baseline")
@patch("baselines_helper.SolutionSageMakerBaselines._create_data_quality_baseline")
def test_create_baseline_job(
    mocked_create_data_quality_baseline, mocked_create_model_quality_baseline, mocked_sagemaker_baselines_instance
):
    sagemaker_baselines = mocked_sagemaker_baselines_instance("DataQuality")
    sagemaker_baselines.create_baseline_job()
    baseline_args = sagemaker_baselines._get_baseline_job_args()
    mocked_create_data_quality_baseline.assert_called_with(baseline_args)


@patch("baselines_helper.DefaultModelMonitor.suggest_baseline")
def test_create_data_quality_baseline(mocked_default_monitor_suggest_baseline, mocked_sagemaker_baselines_instance):
    sagemaker_baselines = mocked_sagemaker_baselines_instance("DataQuality")
    expected_baseline_args = sagemaker_baselines._get_baseline_job_args()
    sagemaker_baselines._create_data_quality_baseline(expected_baseline_args)
    mocked_default_monitor_suggest_baseline.assert_called_with(**expected_baseline_args["suggest_args"])


@patch("baselines_helper.ModelQualityMonitor.suggest_baseline")
def test_create_model_quality_baseline(mocked_model_monitor_suggest_baseline, mocked_sagemaker_baselines_instance):
    sagemaker_baselines = mocked_sagemaker_baselines_instance("ModelQuality")
    expected_baseline_args = sagemaker_baselines._get_baseline_job_args()
    sagemaker_baselines._create_model_quality_baseline(expected_baseline_args)
    mocked_model_monitor_suggest_baseline.assert_called_with(**expected_baseline_args["suggest_args"])


@patch("baselines_helper.SolutionSageMakerBaselines.create_baseline_job")
def test_handler(mocked_create_baseline_job, event, mocked_sagemaker_baseline_attributes):
    # set the environment variables
    mocked_sagemaker_baseline_attributes("ModelQuality")
    # calling the handler function should create the SolutionSageMakerBaselines object
    # and call the create_baseline_job function
    handler(event, {})
    mocked_create_baseline_job.assert_called()
