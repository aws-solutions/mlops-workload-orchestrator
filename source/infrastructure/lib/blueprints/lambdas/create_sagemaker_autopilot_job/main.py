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
from sagemaker import AutoML
from sagemaker import Session
from shared.wrappers import exception_handler
from shared.logger import get_logger
from shared.helper import get_client

logger = get_logger(__name__)

# get the environment variables
assets_bucket = os.environ["ASSETS_BUCKET"]
job_name = os.environ["JOB_NAME"]

# get the estimator config
role_arn = os.environ["ROLE_ARN"]
job_output_location = os.environ["JOB_OUTPUT_LOCATION"]
output_path = f"s3://{assets_bucket}/{job_output_location}"

# if problem_type is provided, job_objective must be provided and vice versa
problem_type = os.environ.get("PROBLEM_TYPE")
job_objective = {"MetricName": os.environ.get("JOB_OBJECTIVE")} if os.environ.get("JOB_OBJECTIVE") else None

# get the training data config
training_dataset_key = os.environ["TRAINING_DATA_KEY"]
training_data_s3_uri = f"s3://{assets_bucket}/{training_dataset_key}"
compression_type = os.environ.get("COMPRESSION_TYPE")
# target attribute name in the training dataset
target_attribute_name = os.environ.get("TARGET_ATTRIBUTE_NAME")
max_candidates = int(os.environ.get("MAX_CANDIDATES", "10"))
kms_key_arn = os.environ.get("KMS_KEY_ARN")
# encrypt inter container traffic
encrypt_inter_container_traffic_str = os.environ.get("ENCRYPT_INTER_CONTAINER_TRAFFIC", "True")
encrypt_inter_container_traffic = False if encrypt_inter_container_traffic_str == "False" else True
max_runtime_per_training_job_in_seconds = (
    int(os.environ.get("MAX_RUNTIME_PER_JOB")) if os.environ.get("MAX_RUNTIME_PER_JOB") else None
)
total_job_runtime_in_seconds = int(os.environ.get("TOTAL_JOB_RUNTIME")) if os.environ.get("TOTAL_JOB_RUNTIME") else None
generate_candidate_definitions_only_str = os.environ.get("GENERATE_CANDIDATE_DEFINITIONS_ONLY", "False")
generate_candidate_definitions_only = True if generate_candidate_definitions_only_str == "True" else False


tags = json.loads(os.environ.get("TAGS")) if os.environ.get("TAGS") else None


@exception_handler
def handler(event, context):
    # sm client
    sm_client = get_client("sagemaker")

    # create the SageMaker Autopilot job
    autopilot_job = AutoML(
        role=role_arn,
        target_attribute_name=target_attribute_name,
        output_path=output_path,
        problem_type=problem_type,
        max_candidates=max_candidates,
        encrypt_inter_container_traffic=encrypt_inter_container_traffic,
        max_runtime_per_training_job_in_seconds=max_runtime_per_training_job_in_seconds,
        total_job_runtime_in_seconds=total_job_runtime_in_seconds,
        job_objective=job_objective,
        generate_candidate_definitions_only=generate_candidate_definitions_only,
        sagemaker_session=Session(sagemaker_client=sm_client),
        tags=tags,
    )

    # start the autopilot job
    autopilot_job.fit(job_name=job_name, inputs=training_data_s3_uri, wait=False, logs=False)
    logger.info(f"Autopilot job {job_name} started...")
    logger.info(autopilot_job.describe_auto_ml_job(job_name))
