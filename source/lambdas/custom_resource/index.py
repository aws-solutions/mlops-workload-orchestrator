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
import sys
import shutil
import tempfile
import logging
import traceback
import boto3
from crhelper import CfnResource


logger = logging.getLogger(__name__)

s3_client = boto3.client("s3")
helper = CfnResource(json_logging=True, log_level="INFO")


def copy_assets_to_s3(s3_client):
    # get the source/destination bukcets and file key
    s3_bucket_name = os.environ.get("SOURCE_BUCKET")
    bucket = os.environ.get("DESTINATION_BUCKET")
    file_key = os.environ.get("FILE_KEY")
    base_dir = "blueprints"

    # create a tmpdir for the zip file to downlaod
    zip_tmpdir = tempfile.mkdtemp()
    zip_file_path = os.path.join(zip_tmpdir, f"{base_dir}.zip")

    # download blueprints.zip
    s3_client.download_file(s3_bucket_name, file_key, zip_file_path)

    # unpack the zip file in another tmp directory
    unpack_tmpdir = tempfile.mkdtemp()
    shutil.unpack_archive(zip_file_path, unpack_tmpdir, "zip")

    # construct the path to the unpacked file
    local_directory = os.path.join(unpack_tmpdir, base_dir)

    # enumerate local files recursively
    for root, dirs, files in os.walk(local_directory):

        for filename in files:

            # construct the full local path
            local_path = os.path.join(root, filename)

            # construct the full s3 path
            relative_path = os.path.relpath(local_path, local_directory)
            s3_path = os.path.join(base_dir, relative_path)
            logger.info(f"Uploading {s3_path}...")
            s3_client.upload_file(local_path, bucket, s3_path)

    return "CopyAssets-" + bucket


def on_event(event, context):
    helper(event, context)


@helper.create
def custom_resource(event, _):

    try:
        resource_id = copy_assets_to_s3(s3_client)
        return resource_id

    except Exception as e:
        exc_type, exc_value, exc_tb = sys.exc_info()
        logger.error(traceback.format_exception(exc_type, exc_value, exc_tb))
        raise e


@helper.update
@helper.delete
def no_op(_, __):
    pass  # No action is required when stack is deleted
