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
import os
from typing import Any, Callable
import traceback
from functools import wraps
import botocore
from shared.logger import get_logger

logger = get_logger(__name__)
endable_detailed_error_message = os.getenv("ALLOW_DETAILED_ERROR_MESSAGE", "Yes")


class BadRequest(Exception):
    pass


def handle_exception(error_description, error_object, status_code):
    # log the error
    logger.error(f"{error_description}. Error: {str(error_object)}")
    exc_type, exc_value, exc_tb = sys.exc_info()
    logger.error(traceback.format_exception(exc_type, exc_value, exc_tb))
    # update the response body
    body = {"message": error_description}
    if endable_detailed_error_message == "Yes":
        body.update({"detailedMessage": str(error_object)})

    return {
        "statusCode": status_code,
        "isBase64Encoded": False,
        "body": json.dumps(body),
        "headers": {"Content-Type": "plain/text"},
    }


def api_exception_handler(f):
    @wraps(f)
    def wrapper(event, context):
        try:
            return f(event, context)

        except BadRequest as bad_request_error:
            return handle_exception("A BadRequest exception occurred", bad_request_error, 400)

        except botocore.exceptions.ClientError as client_error:
            status_code = client_error.response["ResponseMetadata"]["HTTPStatusCode"]
            return handle_exception("A boto3 ClientError occurred", client_error, status_code)

        except Exception as e:
            return handle_exception("An Unexpected Server side exception occurred", e, 500)

    return wrapper


def exception_handler(func: Callable[..., Any]) -> Any:
    """
    Docorator function to handle exceptions

    Args:
        func (object): function to be decorated

    Returns:
        func's return value

    Raises:
        Exception thrown by the decorated function
    """

    def wrapper_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise e

    return wrapper_function
