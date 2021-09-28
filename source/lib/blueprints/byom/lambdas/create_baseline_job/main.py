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
import sagemaker
from shared.logger import get_logger
from baselines_helper import SolutionSageMakerBaselines, exception_handler


logger = get_logger(__name__)
sagemaker_session = sagemaker.session.Session()


@exception_handler
def handler(event, context):
    # get some environment variables
    assets_bucket = os.environ["ASSETS_BUCKET"]
    monitoring_type = os.environ.get("MONITORING_TYPE")
    baseline_job_name = os.environ["BASELINE_JOB_NAME"]
    max_runtime_seconds = os.environ.get("MAX_RUNTIME_SECONDS")

    logger.info(f"Creating {monitoring_type} baseline processing job {baseline_job_name} ...")

    # create a SageMakerBaselines instance
    sagemaker_baseline = SolutionSageMakerBaselines(
        monitoring_type=os.environ.get("MONITORING_TYPE"),
        instance_type=os.environ.get("INSTANCE_TYPE", "ml.m5.large"),
        instance_count=int(os.environ.get("INSTANCE_COUNT", "1")),
        instance_volume_size=int(os.environ.get("INSTANCE_VOLUME_SIZE", "30")),
        role_arn=os.environ["ROLE_ARN"],
        baseline_job_name=os.environ["BASELINE_JOB_NAME"],
        baseline_dataset=f"s3://{assets_bucket}/{os.environ['BASELINE_DATA_LOCATION']}",
        output_s3_uri=f"s3://{os.environ['BASELINE_JOB_OUTPUT_LOCATION']}",
        max_runtime_in_seconds=int(max_runtime_seconds) if max_runtime_seconds else None,
        kms_key_arn=os.environ.get("KMS_KEY_ARN"),
        problem_type=os.environ.get("PROBLEM_TYPE"),
        ground_truth_attribute=os.environ.get("GROUND_TRUTH_ATTRIBUTE"),
        inference_attribute=os.environ.get("INFERENCE_ATTRIBUTE"),
        probability_attribute=os.environ.get("PROBABILITY_ATTRIBUTE"),
        probability_threshold_attribute=os.environ.get("PROBABILITY_THRESHOLD_ATTRIBUTE"),
        sagemaker_session=sagemaker_session,
        tags=[{"Key": "stack_name", "Value": os.environ["STACK_NAME"]}],
    )

    # create the SageMaker Baseline Job
    baseline_job = sagemaker_baseline.create_baseline_job()

    logger.info(f"Started {monitoring_type} baseline processing job. Job info: {baseline_job.describe()}")
