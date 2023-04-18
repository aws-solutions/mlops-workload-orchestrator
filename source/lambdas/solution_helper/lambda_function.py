######################################################################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

import logging, uuid, requests
from copy import copy
from crhelper import CfnResource
from datetime import datetime

logger = logging.getLogger(__name__)
helper = CfnResource(json_logging=True, log_level="INFO")

# requests.post timeout in seconds
REQUST_TIMEOUT = 60


def _sanitize_data(resource_properties):
    # Define allowed keys. You need to update this list with new metrics
    main_keys = [
        "bucketSelected",
        "gitSelected",
        "Region",
        "IsMultiAccount",
        "UseModelRegistry",
        "Version",
    ]
    optional_keys = ["IsDelegatedAccount"]
    allowed_keys = main_keys + optional_keys

    # Remove ServiceToken (lambda arn) to avoid sending AccountId
    resource_properties.pop("ServiceToken", None)
    resource_properties.pop("Resource", None)

    # Solution ID and unique ID are sent separately
    resource_properties.pop("SolutionId", None)
    resource_properties.pop("UUID", None)

    # send only allowed metrics
    sanitized_data = {
        key: resource_properties[key]
        for key in allowed_keys
        if key in resource_properties
    }

    return sanitized_data


def _send_anonymous_metrics(request_type, resource_properties):
    try:
        metrics_data = _sanitize_data(copy(resource_properties))
        metrics_data["RequestType"] = request_type

        headers = {"Content-Type": "application/json"}

        # create the payload
        payload = {
            "Solution": resource_properties["SolutionId"],
            "UUID": resource_properties["UUID"],
            "TimeStamp": datetime.utcnow().isoformat(),
            "Data": metrics_data,
        }

        logger.info(f"Sending payload: {payload}")
        response = requests.post(
            "https://metrics.awssolutionsbuilder.com/generic",
            json=payload,
            headers=headers,
            timeout=REQUST_TIMEOUT,
        )
        # log the response
        logger.info(
            f"Response from the metrics endpoint: {response.status_code} {response.reason}"
        )
        # raise error if response is an 404, 503, 500, 403 etc.
        response.raise_for_status()
        return response
    except Exception as e:
        logger.exception(f"Error when trying to send anonymous_metrics: {str(e)}")
        return None


@helper.create
@helper.update
@helper.delete
def custom_resource(event, _):
    request_type = event["RequestType"]
    resource_properties = event["ResourceProperties"]
    resource = resource_properties["Resource"]

    if resource == "UUID" and (request_type == "Create" or request_type == "Update"):
        random_id = str(uuid.uuid4())
        helper.Data.update({"UUID": random_id})
    elif resource == "AnonymousMetric":
        # send Anonymous Metrics to AWS
        _send_anonymous_metrics(request_type, resource_properties)


def handler(event, context):
    helper(event, context)
