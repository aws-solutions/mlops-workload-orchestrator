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
import boto3
import tempfile
import pytest
from unittest.mock import patch
from moto import mock_s3

from index import copy_assets_to_s3, on_event, custom_resource, no_op


@pytest.fixture(autouse=True)
def mock_env_variables():
    os.environ["source_bucket"] = "solutions-bucket"
    os.environ["destination_bucket"] = "blueprints-bucket"
    os.environ["TESTFILE"] = "blueprints.zip"


@pytest.fixture
def event():
    return {"bucket": os.environ["source_bucket"]}


@pytest.fixture
def mocked_response():
    return f"CopyAssets-{os.environ['destination_bucket']}"


@mock_s3
@patch("index.os.walk")
@patch("index.shutil.unpack_archive")
@patch("index.urllib.request.urlretrieve")
def test_copy_assets_to_s3(mocked_urllib, mocked_shutil, mocked_walk, mocked_response):
    s3_client = boto3.client("s3", region_name="us-east-1")
    testfile = tempfile.NamedTemporaryFile()
    s3_client.create_bucket(Bucket="solutions-bucket")
    s3_client.create_bucket(Bucket="blueprints-bucket")
    s3_client.upload_file(testfile.name, os.environ["source_bucket"], os.environ["TESTFILE"])
    local_file = tempfile.NamedTemporaryFile()
    mocked_urllib.side_effect = s3_client.download_file(
        os.environ["source_bucket"], os.environ["TESTFILE"], local_file.name
    )
    tmp = tempfile.mkdtemp()
    mocked_walk.return_value = [
        (tmp, (local_file.name,), (local_file.name,)),
    ]

    assert copy_assets_to_s3(s3_client) == mocked_response


@patch("index.custom_resource")
def test_no_op(mocked_custom, event):
    response = no_op(event, {})
    assert response is None
    mocked_custom.assert_not_called()


@patch("index.helper")
def test_on_event(mocked_helper, event):
    on_event(event, {})
    mocked_helper.assert_called_with(event, {})


@patch("index.copy_assets_to_s3")
def test_custom_resource(mocked_copy, event, mocked_response):
    # assert expected response
    mocked_copy.return_value = mocked_response
    respone = custom_resource(event, {})
    assert respone == mocked_response
    # assert for error
    mocked_copy.side_effect = Exception("mocked error")
    with pytest.raises(Exception):
        custom_resource(event, {})
