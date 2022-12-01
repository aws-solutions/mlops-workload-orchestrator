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
import boto3
import json
import os
import datetime
from json import JSONEncoder
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


# subclass JSONEncoder to be able to convert pipeline status to json
class DateTimeEncoder(JSONEncoder):
    # Override the default method
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()