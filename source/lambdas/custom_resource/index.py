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
import sys
import shutil
import logging
import traceback
import urllib.request
import boto3
from crhelper import CfnResource


logger = logging.getLogger(__name__)

s3_client = boto3.client('s3')
helper = CfnResource(json_logging=True, log_level='INFO')

def on_event(event, context):
  helper(event, context)

@helper.create
def custom_resource(event, _):

    try:
        # this line is downloading blueprints.zip file from a public bucket.
        # if you would like to change this so that it downloads from a bucket in your account
        # change this following line to use s3_client.download_fileobj('BUCKET_NAME', 'OBJECT_NAME', file)
        # and give s3 read permission to this lambda function
        source_url = os.environ.get('source_bucket') + '/blueprints.zip'
        urllib.request.urlretrieve(source_url, '/tmp/blueprints.zip')
        shutil.unpack_archive('/tmp/blueprints.zip', '/tmp/blueprints/', 'zip')


        local_directory = '/tmp/blueprints'
        bucket = os.environ.get('destination_bucket')
        destination = ''


        # enumerate local files recursively
        for root, dirs, files in os.walk(local_directory):

            for filename in files:

                # construct the full local path
                local_path = os.path.join(root, filename)

                # construct the full s3 path
                relative_path = os.path.relpath(local_path, local_directory)
                s3_path = os.path.join(destination, relative_path)
                logger.info("Uploading %s..." % s3_path)
                s3_client.upload_file(local_path, bucket, s3_path)

        return "CopyAssets-"+bucket
    except Exception as e:
        exc_type, exc_value, exc_tb = sys.exc_info()
        logger.error(traceback.format_exception(exc_type, exc_value, exc_tb))
        raise e

@helper.update
@helper.delete
def no_op(_, __):
    pass # No action is required when stack is deleted