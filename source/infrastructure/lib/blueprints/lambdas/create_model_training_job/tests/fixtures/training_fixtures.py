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
from unittest.mock import Mock
from sagemaker.inputs import TrainingInput
from sagemaker.tuner import ContinuousParameter, IntegerParameter, CategoricalParameter
from model_training_helper import SolutionModelTraining


@pytest.fixture()
def mocked_common_env_vars():
    common_env_vars = {
        "ASSETS_BUCKET": "testbucket",
        "JOB_NAME": "test-training-job",
        "ROLE_ARN": "test-role",
        "JOB_OUTPUT_LOCATION": "job_output",
        "IMAGE_URI": "test-image",
        "INSTANCE_TYPE": "ml.m4.xlarge",
        "INSTANCE_COUNT": "1",
        "INSTANCE_VOLUME_SIZE": "20",
        "TRAINING_DATA_KEY": "data/train/training-dataset.csv",
        "VALIDATION_DATA_KEY": "data/validation/validation-dataset.csv",
        "CONTENT_TYPE": "csv",
        "USE_SPOT_INSTANCES": "True",
        "HYPERPARAMETERS": json.dumps(
            dict(
                eval_metric="auc",
                objective="binary:logistic",
                num_round=400,
                rate_drop=0.3,
            )
        ),
        "TAGS": json.dumps([{"pipeline": "training"}]),
    }

    return common_env_vars


@pytest.fixture()
def mocked_training_job_env_vars(monkeypatch, mocked_common_env_vars):
    training_job_env_vars = mocked_common_env_vars.copy()
    training_job_env_vars.update({"JOB_TYPE": "TrainingJob"})
    monkeypatch.setattr(os, "environ", training_job_env_vars)


@pytest.fixture()
def mocked_tuning_job_env_vars(monkeypatch, mocked_common_env_vars):
    tuning_job_env_vars = mocked_common_env_vars.copy()
    tuning_job_env_vars.update(
        {
            "JOB_TYPE": "HyperparameterTuningJob",
            "TUNER_CONFIG": json.dumps(
                dict(
                    early_stopping_type="Auto",
                    objective_metric_name="validation:auc",
                    strategy="Bayesian",
                    objective_type="Maximize",
                    max_jobs=10,
                    max_parallel_jobs=2,
                )
            ),
            "HYPERPARAMETER_RANGES": json.dumps(
                {
                    "eta": ["continuous", [0.1, 0.5]],
                    "gamma": ["continuous", [0, 5]],
                    "min_child_weight": ["continuous", [0, 120]],
                    "max_depth": ["integer", [1, 15]],
                    "optimizer": ["categorical", ["sgd", "Adam"]],
                }
            ),
        }
    )

    monkeypatch.setattr(os, "environ", tuning_job_env_vars)


@pytest.fixture()
def mocked_hyperparameters(mocked_training_job_env_vars):
    return json.loads(os.environ["HYPERPARAMETERS"])


@pytest.fixture()
def mocked_sagemaker_session():
    region = "us-east-1"
    boto_mock = Mock(name="boto_session", region_name=region)
    sms = Mock(
        name="sagemaker_session",
        boto_session=boto_mock,
        boto_region_name=region,
        config=None,
        local_mode=False,
        s3_resource=None,
        s3_client=None,
    )
    sms.sagemaker_config = {}
    return sms


@pytest.fixture()
def mocked_estimator_config(mocked_training_job_env_vars, mocked_sagemaker_session):
    return dict(
        image_uri=os.environ["IMAGE_URI"],
        role=os.environ["ROLE_ARN"],
        instance_count=int(os.environ["INSTANCE_COUNT"]),
        instance_type=os.environ["INSTANCE_TYPE"],
        volume_size=int(os.environ["INSTANCE_VOLUME_SIZE"]),
        output_path=f"s3://{os.environ['ASSETS_BUCKET']}/{os.environ['JOB_OUTPUT_LOCATION']}",
        sagemaker_session=mocked_sagemaker_session,
    )


@pytest.fixture()
def mocked_data_channels(mocked_training_job_env_vars):
    train_input = TrainingInput(
        f"s3://{os.environ['ASSETS_BUCKET']}/{os.environ['TRAINING_DATA_KEY']}",
        content_type=os.environ["CONTENT_TYPE"],
    )
    validation_input = TrainingInput(
        f"s3://{os.environ['ASSETS_BUCKET']}/{os.environ['TRAINING_DATA_KEY']}",
        content_type=os.environ["CONTENT_TYPE"],
    )

    data_channels = {"train": train_input, "validation": validation_input}
    return data_channels


@pytest.fixture()
def mocked_tuner_config(mocked_tuning_job_env_vars):
    return json.loads(os.environ["TUNER_CONFIG"])


@pytest.fixture()
def mocked_job_name():
    return "test-training-job"


@pytest.fixture()
def mocked_raw_search_grid(mocked_tuning_job_env_vars):
    return json.loads(os.environ["HYPERPARAMETER_RANGES"])


@pytest.fixture()
def mocked_hyperparameter_ranges(mocked_raw_search_grid):
    return SolutionModelTraining.format_search_grid(mocked_raw_search_grid)
