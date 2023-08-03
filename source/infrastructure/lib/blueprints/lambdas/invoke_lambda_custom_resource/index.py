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
import logging
import uuid
import json
from crhelper import CfnResource
from shared.helper import get_client

logger = logging.getLogger(__name__)

lambda_client = get_client("lambda")
helper = CfnResource(json_logging=True, log_level="INFO")


def handler(event, context):
    helper(event, context)


@helper.update
@helper.create
def invoke_lambda(event, _, lm_client=lambda_client):
    try:
        logger.info(f"Event received: {event}")
        resource_properties = event["ResourceProperties"]
        resource = resource_properties["Resource"]
        if resource == "InvokeLambda":
            logger.info("Invoking lambda function is initiated...")
            resource_id = str(uuid.uuid4())
            lm_client.invoke(
                FunctionName=resource_properties["function_name"],
                InvocationType="Event",
                Payload=json.dumps({"message": resource_properties["message"]}),
            )
            helper.Data.update({"ResourceId": resource_id})

            return resource_id

        else:
            raise ValueError(f"The Resource {resource} is unsupported by the Invoke Lambda custom resource.")

    except Exception as e:
        logger.error(f"Custom resource failed: {str(e)}")
        raise e


@helper.delete
def no_op(_, __):
    pass  # No action is required when stack is deleted
