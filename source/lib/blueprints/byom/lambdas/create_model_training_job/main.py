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
from sagemaker import Session
from sagemaker.inputs import TrainingInput
from model_training_helper import TrainingType, SolutionModelTraining
from shared.wrappers import exception_handler
from shared.logger import get_logger
from shared.helper import get_client

logger = get_logger(__name__)


# get the environment variables
assets_bucket = os.environ["ASSETS_BUCKET"]
job_name = os.environ["JOB_NAME"]
type_map = dict(TrainingJob=1, HyperparameterTuningJob=2)
job_type_str = os.environ.get("JOB_TYPE", "TrainingJob")
job_type = TrainingType(type_map[job_type_str])
# get the estimator config
role_arn = os.environ["ROLE_ARN"]
s3_output_location = os.environ["JOB_OUTPUT_LOCATION"]
image_uri = os.environ["IMAGE_URI"]
instance_type = os.environ["INSTANCE_TYPE"]
instance_count = int(os.environ.get("INSTANCE_COUNT", "1"))
instance_volume_size = int(os.environ.get("INSTANCE_VOLUME_SIZE", "20"))
kms_key_arn = os.environ.get("KMS_KEY_ARN")
# max time in seconds the training job is allowed to run
max_run = int(os.environ.get("JOB_MAX_RUN_SECONDS", "7200"))
# use spot instances for training
use_spot_instances_str = os.environ.get("USE_SPOT_INSTANCES", "True")
use_spot_instances = False if use_spot_instances_str == "False" else True
# encrypt inter container traffic
encrypt_inter_container_traffic_str = os.environ.get("ENCRYPT_INTER_CONTAINER_TRAFFIC", "True")
encrypt_inter_container_traffic = False if encrypt_inter_container_traffic_str == "False" else True
# max wait time for Spot instances (required if use_spot_instances = True). Must be greater than max_run
max_wait = int(os.environ.get("MAX_WAIT_SECONDS", str(2 * max_run))) if use_spot_instances else None
# define checkpoint_s3_uri if use_spot_instances = True
checkpoint_s3_uri = f"s3://{assets_bucket}/{s3_output_location}/{job_name}/checkpoint" if use_spot_instances else None

# get the training data config
training_dataset_key = os.environ["TRAINING_DATA_KEY"]
validation_dataset_key = os.environ.get("VALIDATION_DATA_KEY")
# create data config
data_config = dict(
    content_type=os.environ.get("CONTENT_TYPE", "csv"),  # MIME type of the input data
    distribution=os.environ.get(
        "DATA_DISTRIBUTION", "FullyReplicated"
    ),  # valid values ‘FullyReplicated’, ‘ShardedByS3Key’
    compression=os.environ.get("COMPRESSION_TYPE"),  # valid values: ‘Gzip’, None. This is used only in Pipe input mode.
    record_wrapping=os.environ.get("DATA_RECORD_WRAPPING"),  # valid values: 'RecordIO', None
    s3_data_type=os.environ.get(
        "S3_DATA_TYPE", "S3Prefix"
    ),  # valid values: ‘S3Prefix’, ‘ManifestFile’, ‘AugmentedManifestFile’
    input_mode=os.environ.get("DATA_INPUT_MODE"),  # valid values 'File', 'Pipe', 'FastFile', None
)

# A list of one or more attribute names to use that are found in a
# specified AugmentedManifestFile (if s3_data_type="AugmentedManifestFile")
attribute_names = os.environ.get("ATTRIBUTE_NAMES")

# add it to data_config
data_config["attribute_names"] = json.loads(attribute_names) if attribute_names else attribute_names

# get training algorithm's hyperparameters
hyperparameters = json.loads(os.environ["HYPERPARAMETERS"])

# create training inputs
training_input = TrainingInput(s3_data=f"s3://{assets_bucket}/{training_dataset_key}", **data_config)

# create data channels
data_channels = {"train": training_input}

# add validation data if provided
if validation_dataset_key:
    validation_input = TrainingInput(s3_data=f"s3://{assets_bucket}/{validation_dataset_key}", **data_config)
    data_channels["validation"] = validation_input


# get hyperparameter tuner config (if job_type="HyperparameterTuningJob")
tuner_config_str = os.environ.get("TUNER_CONFIG")
hyperparameter_tuner_config = json.loads(tuner_config_str) if job_type_str == "HyperparameterTuningJob" else None

# get hyperparameter ranges
hyperparameter_ranges_dict = os.environ.get("HYPERPARAMETER_RANGES")
hyperparameter_ranges = (
    SolutionModelTraining.format_search_grid(json.loads(hyperparameter_ranges_dict))
    if job_type_str == "HyperparameterTuningJob"
    else None
)

tags = json.loads(os.environ.get("TAGS")) if os.environ.get("TAGS") else None


@exception_handler
def handler(event, context):
    # create sagemaker boto3 client, to be passed to SageMaker session
    sm_client = get_client("sagemaker")

    # create estimator config
    estimator_config = dict(
        image_uri=image_uri,
        role=role_arn,
        instance_count=instance_count,
        instance_type=instance_type,
        volume_size=instance_volume_size,
        output_path=f"s3://{assets_bucket}/{s3_output_location}",
        volume_kms_key=kms_key_arn,
        output_kms_key=kms_key_arn,
        use_spot_instances=use_spot_instances,
        max_run=max_run,
        max_wait=max_wait,
        checkpoint_s3_uri=checkpoint_s3_uri,
        encrypt_inter_container_traffic=encrypt_inter_container_traffic,
        sagemaker_session=Session(sagemaker_client=sm_client),
        tags=tags,
    )

    # create the training job
    logger.info("Creating the training job")
    job = SolutionModelTraining(
        job_name=job_name,
        estimator_config=estimator_config,
        hyperparameters=hyperparameters,
        data_channels=data_channels,
        job_type=job_type,
        hyperparameter_tuner_config=hyperparameter_tuner_config,
        hyperparameter_ranges=hyperparameter_ranges,
    )

    # start the training job
    job.create_training_job()
    logger.info(f"Training job {job_name} started")
