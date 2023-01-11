# #####################################################################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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
import boto3
from shared.wrappers import api_exception_handler
from shared.logger import get_logger
from shared.helper import get_client

logger = get_logger(__name__)
sagemaker_client = get_client("sagemaker-runtime")


@api_exception_handler
def handler(event, context):
    event_body = json.loads(event["body"])
    endpoint_name = os.environ["SAGEMAKER_ENDPOINT_NAME"]
    return invoke(event_body, endpoint_name)


def invoke(event_body, endpoint_name, sm_client=sagemaker_client):
    # convert the payload to a string if it not a string (to support JSON input)
    payload = event_body["payload"] if isinstance(event_body["payload"], str) else json.dumps(event_body["payload"])
    response = sm_client.invoke_endpoint(
        EndpointName=endpoint_name, Body=payload, ContentType=event_body["content_type"]
    )
    logger.info(response)
    predictions = response["Body"].read().decode()
    logger.info(predictions)
    return {
        "statusCode": 200,
        "isBase64Encoded": False,
        "body": predictions,
        "headers": {"Content-Type": "plain/text"},
    }
