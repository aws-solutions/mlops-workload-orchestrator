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
import json
import sys
import traceback
from functools import wraps
import boto3
from shared.logger import get_logger
from shared.helper import get_client

logger = get_logger(__name__)


class BadRequest(Exception):
    pass


def code_pipeline_exception_handler(f):
    @wraps(f)
    def wrapper(event, context):
        try:
            return f(event, context)
        except Exception as e:
            codepipeline = get_client("codepipeline")
            exc_type, exc_value, exc_tb = sys.exc_info()
            logger.error(traceback.format_exception(exc_type, exc_value, exc_tb))
            codepipeline.put_job_failure_result(
                jobId=event["CodePipeline.job"]["id"],
                failureDetails={
                    "message": f"Job failed. {str(e)}. Check the logs for more info.",
                    "type": "JobFailed",
                },
            )

    return wrapper


def api_exception_handler(f):
    @wraps(f)
    def wrapper(event, context):
        try:
            return f(event, context)
        except BadRequest as e:
            logger.error(f"A BadRequest exception occurred, exception message: {str(e)}")
            exc_type, exc_value, exc_tb = sys.exc_info()
            logger.error(traceback.format_exception(exc_type, exc_value, exc_tb))
            return {
                "statusCode": 400,
                "isBase64Encoded": False,
                "body": json.dumps({"message": str(e)}),
                "headers": {"Content-Type": "plain/text"},
            }
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            logger.error(traceback.format_exception(exc_type, exc_value, exc_tb))
            return {
                "statusCode": 500,
                "isBase64Encoded": False,
                "body": json.dumps({"message": "Internal server error. See logs for more information."}),
                "headers": {"Content-Type": "plain/text"},
            }

    return wrapper
