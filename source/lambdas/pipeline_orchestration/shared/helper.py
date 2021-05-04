# #####################################################################################################################
#  Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                       #
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
import boto3
import json
import os
from botocore.config import Config
from shared.logger import get_logger

logger = get_logger(__name__)
_helpers_service_clients = dict()


# Set Boto3 configuration to track the solution's usage
CLIENT_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "standard"},
    **json.loads(os.environ.get("AWS_SDK_USER_AGENT", '{"user_agent_extra": null}')),
)


def get_client(service_name, config=CLIENT_CONFIG):
    global _helpers_service_clients
    if service_name not in _helpers_service_clients:
        logger.debug(f"Initializing global boto3 client for {service_name}")
        _helpers_service_clients[service_name] = boto3.client(service_name, config=config)
    return _helpers_service_clients[service_name]


def reset_client():
    global _helpers_service_clients
    _helpers_service_clients = dict()


# Currently, retriving the sagemaker-model-monitor-analyzer image url is not supported by sagemaker.image_uris.retrieve
# For the latest images per region, see https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-pre-built-container.html
# These are SageMaker service account numbers for the built-in SageMaker containers.
def get_built_in_model_monitor_container_uri(region):
    regions_to_accounts = {
        "us-east-1": "156813124566",
        "us-east-2": "777275614652",
        "us-west-1": "890145073186",
        "us-west-2": "159807026194",
        "af-south-1": "875698925577",
        "ap-east-1": "001633400207",
        "ap-northeast-1": "574779866223",
        "ap-northeast-2": "709848358524",
        "ap-south-1": "126357580389",
        "ap-southeast-1": "245545462676",
        "ap-southeast-2": "563025443158",
        "ca-central-1": "536280801234",
        "cn-north-1": "453000072557",
        "cn-northwest-1": "453252182341",
        "eu-central-1": "048819808253",
        "eu-north-1": "895015795356",
        "eu-south-1": "933208885752",
        "eu-west-1": "468650794304",
        "eu-west-2": "749857270468",
        "eu-west-3": "680080141114",
        "me-south-1": "607024016150",
        "sa-east-1": "539772159869",
        "us-gov-west-1": "362178532790",
    }

    container_uri = (
        f"{regions_to_accounts[region]}.dkr.ecr.{region}.amazonaws.com/sagemaker-model-monitor-analyzer:latest"
    )

    return container_uri
