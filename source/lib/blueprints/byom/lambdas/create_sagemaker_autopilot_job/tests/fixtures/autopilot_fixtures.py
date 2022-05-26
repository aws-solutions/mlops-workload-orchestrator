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


@pytest.fixture()
def mocked_autopilot_env_vars(monkeypatch):
    autopilot_env_vars = {
        "ASSETS_BUCKET": "testbucket",
        "JOB_NAME": "test-training-job",
        "ROLE_ARN": "test-role",
        "JOB_OUTPUT_LOCATION": "job_output",
        "PROBLEM_TYPE": "BinaryClassification",
        "JOB_OBJECTIVE": "auc",
        "TRAINING_DATA_KEY": "data/train/training-dataset.csv",
        "TARGET_ATTRIBUTE_NAME": "COLUMN_NAME",
        "MAX_CANDIDATES": "20",
        "TAGS": json.dumps([{"Key": "job-type", "Value": "autopilot"}]),
    }

    monkeypatch.setattr(os, "environ", autopilot_env_vars)


@pytest.fixture()
def mocked_automl_config(mocked_autopilot_env_vars):
    return dict(
        role=os.environ["ROLE_ARN"],
        target_attribute_name=os.environ["TARGET_ATTRIBUTE_NAME"],
        output_path=f"s3://{os.environ['ASSETS_BUCKET']}/{os.environ['JOB_OUTPUT_LOCATION']}",
        problem_type=os.environ["PROBLEM_TYPE"],
        max_candidates=int(os.environ["MAX_CANDIDATES"]),
        encrypt_inter_container_traffic=True,
        max_runtime_per_training_job_in_seconds=None,
        total_job_runtime_in_seconds=None,
        job_objective=os.environ["JOB_OBJECTIVE"],
        generate_candidate_definitions_only=False,
        sagemaker_session=Mock(),
        tags=json.loads(os.environ["TAGS"]),
    )


@pytest.fixture()
def mocked_job_name():
    return "test-autopilot-job"
