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
from model_training_helper import TrainingType, SolutionModelTraining
from tests.fixtures.training_fixtures import (
    mocked_common_env_vars,
    mocked_training_job_env_vars,
    mocked_tuning_job_env_vars,
    mocked_estimator_config,
    mocked_hyperparameters,
    mocked_data_channels,
    mocked_tuner_config,
    mocked_job_name,
    mocked_raw_search_grid,
    mocked_hyperparameter_ranges,
    mocked_sagemaker_session,
)


def test_create_estimator(
    mocked_estimator_config,
    mocked_hyperparameters,
    mocked_data_channels,
    mocked_job_name,
):
    job = SolutionModelTraining(
        job_name=mocked_job_name,
        estimator_config=mocked_estimator_config,
        hyperparameters=mocked_hyperparameters,
        data_channels=mocked_data_channels,
    )

    # create the estimator
    estimator = job._create_estimator()

    # assert some of the properties
    assert estimator.image_uri == mocked_estimator_config["image_uri"]
    assert estimator.role == mocked_estimator_config["role"]
    assert estimator.instance_type == mocked_estimator_config["instance_type"]
    assert estimator.output_path == mocked_estimator_config["output_path"]


def test_create_hyperparameter_tuner(
    mocked_estimator_config,
    mocked_hyperparameters,
    mocked_data_channels,
    mocked_tuner_config,
    mocked_job_name,
    mocked_hyperparameter_ranges,
):
    job = SolutionModelTraining(
        job_name=mocked_job_name,
        estimator_config=mocked_estimator_config,
        hyperparameters=mocked_hyperparameters,
        data_channels=mocked_data_channels,
        job_type=TrainingType.HyperparameterTuningJob,
        hyperparameter_tuner_config=mocked_tuner_config,
        hyperparameter_ranges=mocked_hyperparameter_ranges,
    )
    # create the Hyperparameters tuner
    tuner = job._create_hyperparameter_tuner()
    # assert some of the properties
    assert tuner.max_parallel_jobs == 2
    assert tuner.max_jobs == 10
    assert tuner.strategy == "Bayesian"
    assert tuner.objective_type == "Maximize"
    TestCase().assertDictEqual(
        tuner._hyperparameter_ranges, mocked_hyperparameter_ranges
    )


def test_format_search_grid(mocked_raw_search_grid):
    formeated_grid = SolutionModelTraining.format_search_grid(mocked_raw_search_grid)
    # assert a Continuous parameter
    TestCase().assertListEqual(
        mocked_raw_search_grid["eta"][1],
        [formeated_grid["eta"].min_value, formeated_grid["eta"].max_value],
    )
    # assert an Integer parameter
    TestCase().assertListEqual(
        mocked_raw_search_grid["max_depth"][1],
        [formeated_grid["max_depth"].min_value, formeated_grid["max_depth"].max_value],
    )
    # assert a Categorical parameter
    TestCase().assertListEqual(
        mocked_raw_search_grid["optimizer"][1], formeated_grid["optimizer"].values
    )


@patch("model_training_helper.SolutionModelTraining._create_hyperparameter_tuner")
@patch("model_training_helper.SolutionModelTraining._create_estimator")
def test_create_training_job(
    mocked_create_estimator,
    mocked_create_tuner,
    mocked_estimator_config,
    mocked_hyperparameters,
    mocked_data_channels,
    mocked_tuner_config,
    mocked_job_name,
    mocked_hyperparameter_ranges,
):
    # assert the SolutionModelTraining._create_estimator is called for a training job
    training_job = SolutionModelTraining(
        job_name=mocked_job_name,
        estimator_config=mocked_estimator_config,
        hyperparameters=mocked_hyperparameters,
        data_channels=mocked_data_channels,
    )

    training_job.create_training_job()
    mocked_create_estimator.assert_called()

    # assert the SolutionModelTraining._create_hyperparameter_tuner is called for a tuning job
    tuner_job = SolutionModelTraining(
        job_name=mocked_job_name,
        estimator_config=mocked_estimator_config,
        hyperparameters=mocked_hyperparameters,
        data_channels=mocked_data_channels,
        job_type=TrainingType.HyperparameterTuningJob,
        hyperparameter_tuner_config=mocked_tuner_config,
        hyperparameter_ranges=mocked_hyperparameter_ranges,
    )
    tuner_job.create_training_job()
    mocked_create_tuner.assert_called()


@patch("model_training_helper.SolutionModelTraining._create_estimator")
@patch("main.Session")
@patch("main.get_client")
def test_handler_training_job(
    mocked_client, mocked_session, mocked_create_estimator, mocked_training_job_env_vars
):
    mocked_client.boto_region_name = "us-east-1"
    from main import handler

    handler(None, None)
    mocked_create_estimator.assert_called()
