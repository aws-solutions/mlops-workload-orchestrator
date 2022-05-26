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
from sagemaker.clarify import (
    DataConfig,
    BiasConfig,
    ModelConfig,
    ModelPredictedLabelConfig,
    SHAPConfig,
)

from shared.logger import get_logger
from shared.helper import get_client
from shared.wrappers import exception_handler
from baselines_helper import SolutionSageMakerBaselines


logger = get_logger(__name__)
s3_client = get_client("s3")
sm_client = get_client("sagemaker")
sagemaker_session = sagemaker.session.Session(sagemaker_client=sm_client)


@exception_handler
def handler(event, context):
    # get some environment variables
    assets_bucket = os.environ["ASSETS_BUCKET"]
    monitoring_type = os.environ.get("MONITORING_TYPE")
    baseline_job_name = os.environ["BASELINE_JOB_NAME"]
    instance_type = os.environ.get("INSTANCE_TYPE", "ml.m5.large")
    instance_count = int(os.environ.get("INSTANCE_COUNT", "1"))
    max_runtime_seconds = os.environ.get("MAX_RUNTIME_SECONDS")
    baseline_dataset_file_key = os.environ["BASELINE_DATA_LOCATION"]
    baseline_data_s3_uri = f"s3://{assets_bucket}/{baseline_dataset_file_key}"
    baseline_output_s3_uri = f"s3://{os.environ['BASELINE_JOB_OUTPUT_LOCATION']}"
    endpoint_name = os.getenv("ENDPOINT_NAME")
    # used only for ModelBias/Explanability
    # model_predicted_label_config is optional for regression
    raw_model_predicted_label_config = os.getenv("MODEL_PREDICTED_LABEL_CONFIG")
    model_predicted_label_config = (
        json.loads(raw_model_predicted_label_config)
        if raw_model_predicted_label_config
        # set default for regression problem
        else dict(label=None, probability=None, probability_threshold=None, label_headers=None)
    )
    # bias_config required for ModelBias
    bias_config = json.loads(os.getenv("BIAS_CONFIG", "{}"))
    # shap_config required for ModelExplainability
    shap_config = json.loads(os.getenv("SHAP_CONFIG", "{}"))

    # check if the baseline is a string (a file key is provided not a list of lists to calculate the baseline)
    # the baseline file is expected to be in the Assets Bucket
    baseline = shap_config.get("baseline")
    # add assets bucket if a file key is provided
    if isinstance(baseline, str):
        shap_config["baseline"] = f"s3://{assets_bucket}/{baseline}"

    # use model scores if provided
    model_scores = json.loads(os.getenv("MODEL_SCORES")) if os.getenv("MODEL_SCORES") else None

    logger.info(f"Creating {monitoring_type} baseline processing job {baseline_job_name} ...")

    # get config file contents if the baseline to be created is ModelBias|ModelExplainability
    # the config file should be uploaded to the Solution's Assets S3 bucket
    # details on the contents for expected ModelBias|ModelExplainability config files are provided in the
    # SolutionSageMakerBaselines.get_baseline_config_file function's docs
    header = None
    if monitoring_type in ["ModelBias", "ModelExplainability"]:
        header = SolutionSageMakerBaselines.get_baseline_dataset_header(
            bucket_name=assets_bucket, file_key=baseline_dataset_file_key, s3_client=s3_client
        )

    # create a SageMakerBaselines instance
    sagemaker_baseline = SolutionSageMakerBaselines(
        monitoring_type=os.environ.get("MONITORING_TYPE"),
        instance_type=instance_type,
        instance_count=instance_count,
        instance_volume_size=int(os.environ.get("INSTANCE_VOLUME_SIZE", "30")),
        role_arn=os.environ["ROLE_ARN"],
        baseline_job_name=os.environ["BASELINE_JOB_NAME"],
        baseline_dataset=baseline_data_s3_uri,
        output_s3_uri=baseline_output_s3_uri,
        max_runtime_in_seconds=int(max_runtime_seconds) if max_runtime_seconds else None,
        kms_key_arn=os.environ.get("KMS_KEY_ARN"),
        problem_type=os.environ.get("PROBLEM_TYPE"),
        ground_truth_attribute=os.environ.get("GROUND_TRUTH_ATTRIBUTE"),
        inference_attribute=os.environ.get("INFERENCE_ATTRIBUTE"),
        probability_attribute=os.environ.get("PROBABILITY_ATTRIBUTE"),
        probability_threshold_attribute=os.environ.get("PROBABILITY_THRESHOLD_ATTRIBUTE"),
        sagemaker_session=sagemaker_session,
        data_config=DataConfig(
            s3_data_input_path=baseline_data_s3_uri,
            s3_output_path=baseline_output_s3_uri,
            label=header[0],  # the label is expected to be the first column in the baseline dataset
            headers=header,
            dataset_type="text/csv",
        )
        if monitoring_type in ["ModelBias", "ModelExplainability"]
        else None,
        bias_config=BiasConfig(**bias_config) if monitoring_type == "ModelBias" else None,
        model_config=ModelConfig(
            model_name=SolutionSageMakerBaselines.get_model_name(endpoint_name, sm_client),
            instance_type=instance_type,
            instance_count=instance_count,
            accept_type="text/csv",
        )
        if monitoring_type in ["ModelBias", "ModelExplainability"]
        else None,
        model_predicted_label_config=ModelPredictedLabelConfig(**model_predicted_label_config)
        if monitoring_type == "ModelBias"
        else None,
        explainability_config=SHAPConfig(**shap_config) if monitoring_type == "ModelExplainability" else None,
        model_scores=model_scores if monitoring_type == "ModelExplainability" else None,
        tags=[{"Key": "stack_name", "Value": os.environ["STACK_NAME"]}],
    )

    # create the SageMaker Baseline Job
    baseline_job = sagemaker_baseline.create_baseline_job()

    logger.info(f"Started {monitoring_type} baseline processing job. Job info: {baseline_job.describe()}")
