#######################################################################################################################
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
import tempfile
import pytest
from unittest.mock import patch, Mock
from botocore.stub import Stubber
import botocore.session
from tests.fixtures.stackset_fixtures import (
    stackset_name,
    mocked_template_parameters,
    mocked_template,
    mocked_org_ids,
    mocked_account_ids,
    mocked_regions,
    mocked_job_id,
    mocked_cp_success_message,
    mocked_cp_failure_message,
    mocked_cp_continuation_message,
    required_user_params,
    mocked_decoded_parameters,
    mocked_codepipeline_event,
    mocked_invalid_user_parms,
    mocked_describe_response
)
from moto import mock_cloudformation, mock_s3
from unittest.mock import patch
from stackset_helpers import (
    find_artifact,
    get_template,
    update_stackset,
    stackset_exists,
    create_stackset_and_instances,
    get_stackset_instance_status,
    put_job_success,
    put_job_failure,
    put_job_continuation,
    start_stackset_update_or_create,
    check_stackset_update_status,
    validate_user_params,
    get_user_params,
    setup_s3_client,
)
from main import lambda_handler

cp_job = "CodePipeline.job"
client_to_patch = "boto3.client"


@mock_cloudformation
def test_create_stackset_and_instances(
    stackset_name,
    mocked_template,
    mocked_template_parameters,
    mocked_org_ids,
    mocked_account_ids,
    mocked_regions,
):
    cf_client = boto3.client("cloudformation", region_name=mocked_regions[0])
    create_stackset_and_instances(
        stackset_name,
        mocked_template,
        json.loads(mocked_template_parameters),
        mocked_org_ids,
        mocked_regions,
        cf_client,
    )
    stacksets = cf_client.list_stack_sets()
    # assert one StackSet has been created
    assert len(stacksets["Summaries"]) == 1
    # assert the created name has the passed name
    assert stacksets["Summaries"][0]["StackSetName"] == stackset_name
    # assert the status of the stackset is ACTIVE
    assert stacksets["Summaries"][0]["Status"] == "ACTIVE"
    assert stacksets["ResponseMetadata"]["HTTPStatusCode"] == 200

    # assert the function will throw an exception
    with pytest.raises(Exception):
        create_stackset_and_instances(
            stackset_name,
            mocked_template,
            mocked_template_parameters,
            mocked_org_ids,
            mocked_regions,
            cf_client,
        )


def test_create_stackset_and_instances_client_error(
    stackset_name,
    mocked_template,
    mocked_template_parameters,
    mocked_org_ids,
    mocked_account_ids,
    mocked_regions,
):
    cf_client = boto3.client("cloudformation", region_name=mocked_regions[0])

    with pytest.raises(botocore.exceptions.ClientError):
        create_stackset_and_instances(
            stackset_name,
            mocked_template,
            json.loads(mocked_template_parameters),
            mocked_org_ids,
            mocked_regions,
            cf_client,
        )


def test_get_stackset_instance_status_client_error(
    stackset_name,
    mocked_template,
    mocked_template_parameters,
    mocked_org_ids,
    mocked_account_ids,
    mocked_regions,
):

    cf_client = boto3.client("cloudformation", region_name=mocked_regions[0])
    with pytest.raises(botocore.exceptions.ClientError):
        get_stackset_instance_status(stackset_name, mocked_account_ids[0], mocked_regions[0], cf_client)


@patch("boto3.client")
def test_get_stackset_instance_status(
    patched_client,
    stackset_name,
    mocked_account_ids,
    mocked_regions,
    mocked_describe_response
):

    cf_client = boto3.client("cloudformation", region_name=mocked_regions[0])
    patched_client().describe_stack_instance.return_value = mocked_describe_response
    response = get_stackset_instance_status(stackset_name, mocked_account_ids[0], mocked_regions[0], cf_client)

    assert response == "SUCCEEDED"



@mock_cloudformation
def test_update_stackset(
    stackset_name,
    mocked_template,
    mocked_template_parameters,
    mocked_org_ids,
    mocked_account_ids,
    mocked_regions,
):
    cf_client = boto3.client("cloudformation", region_name=mocked_regions[0])
    # Case 1: stack exists and there is an update
    # create a mocked stackset
    cf_client.create_stack_set(
        StackSetName=stackset_name,
        TemplateBody=mocked_template,
        Parameters=json.loads(mocked_template_parameters),
    )
    res = update_stackset(
        stackset_name,
        mocked_template,
        json.loads(mocked_template_parameters),
        mocked_org_ids,
        mocked_regions,
        cf_client,
    )
    assert res is True

    # Case 2: stack exists and there is no update
    with pytest.raises(Exception):
        update_stackset(
            stackset_name, mocked_template, mocked_template_parameters, mocked_org_ids, mocked_regions, cf_client
        )


def test_update_stackset_error(
    stackset_name,
    mocked_template,
    mocked_template_parameters,
    mocked_org_ids,
    mocked_account_ids,
    mocked_regions,
):
    cf_client = boto3.client("cloudformation", region_name=mocked_regions[0])
    with pytest.raises(Exception):
        update_stackset(
            stackset_name,
            mocked_template,
            json.loads(mocked_template_parameters),
            mocked_org_ids,
            mocked_regions,
            cf_client,
        )


@mock_cloudformation
def test_stackset_exists(stackset_name, mocked_template, mocked_template_parameters, mocked_regions):
    cf_client = boto3.client("cloudformation", region_name=mocked_regions[0])
    # assert the stackset does not exist
    assert stackset_exists(stackset_name, cf_client) is False

    # create mocked stackset
    cf_client.create_stack_set(
        StackSetName=stackset_name,
        TemplateBody=mocked_template,
        Parameters=json.loads(mocked_template_parameters),
    )
    # assert the stackset does exist
    assert stackset_exists(stackset_name, cf_client) is True

    # assert for other exceptions (e.g. cf_client is None)
    with pytest.raises(Exception):
        stackset_exists(stackset_name, None)


def test_put_job_success_faiure(mocked_job_id, mocked_cp_success_message, mocked_regions):
    with patch(client_to_patch) as patched_client:
        cp_client = boto3.client("codepipeline", region_name=mocked_regions[0])
        put_job_success(mocked_job_id, mocked_cp_success_message, cp_client)
        # assert the put_job_success_result is called
        patched_client().put_job_success_result.assert_called_once()
        # assert the function is called passed arguments
        patched_client().put_job_success_result.assert_called_with(jobId=mocked_job_id)


def test_put_job_faiure(mocked_job_id, mocked_cp_failure_message, mocked_regions):
    with patch(client_to_patch) as patched_client:
        cp_client = boto3.client("codepipeline", region_name=mocked_regions[0])
        put_job_failure(mocked_job_id, mocked_cp_failure_message, cp_client)
        # assert the put_job_failure_result is called
        patched_client().put_job_failure_result.assert_called_once()
        # assert the function is called passed arguments
        patched_client().put_job_failure_result.assert_called_with(
            jobId=mocked_job_id, failureDetails={"message": mocked_cp_failure_message, "type": "JobFailed"}
        )


def test_put_job_continuation(mocked_job_id, mocked_cp_continuation_message, mocked_regions):
    with patch(client_to_patch) as patched_client:
        cp_client = boto3.client("codepipeline", region_name=mocked_regions[0])
        put_job_continuation(mocked_job_id, mocked_cp_continuation_message, cp_client)
        # assert the put_job_success_result is called
        patched_client().put_job_success_result.assert_called_once()
        # assert the function is called passed arguments
        continuation_token = json.dumps({"previous_job_id": mocked_job_id})
        patched_client().put_job_success_result.assert_called_with(
            jobId=mocked_job_id, continuationToken=continuation_token
        )


@patch("stackset_helpers.put_job_failure")
@patch("stackset_helpers.put_job_continuation")
@patch("stackset_helpers.put_job_success")
@patch("stackset_helpers.get_stackset_instance_status")
def test_check_stackset_update_status(
    mocked_get_stackset_instance_status,  # NOSONAR:S107 this test function is designed to take many fixtures
    mocked_put_job_success,
    mocked_put_job_continuation,
    mocked_put_job_failure,
    mocked_job_id,
    stackset_name,
    mocked_account_ids,
    mocked_regions,
):
    # Case 1: asserting first branch if status == "SUCCEEDED"
    mocked_get_stackset_instance_status.return_value = "SUCCEEDED"
    check_stackset_update_status(mocked_job_id, stackset_name, mocked_account_ids[0], mocked_regions[0], None, None)
    # assert get_stackset_instance_status function is called
    mocked_get_stackset_instance_status.assert_called_once()
    # assert get_stackset_instance_status is called with the passed arguments
    mocked_get_stackset_instance_status.assert_called_with(
        stackset_name, mocked_account_ids[0], mocked_regions[0], None
    )
    # assert the put_job_success is called
    mocked_put_job_success.assert_called_once()
    # assert it was called with the expected arguments
    mocked_put_job_success.assert_called_with(mocked_job_id, "StackSet and its instance update complete", None)

    # Case 2: asserting for the second branch status in ["RUNNING","PENDING"]:
    mocked_get_stackset_instance_status.return_value = "RUNNING"
    check_stackset_update_status(mocked_job_id, stackset_name, mocked_account_ids[0], mocked_regions[0], None, None)
    # assert get_stackset_instance_status function is called
    mocked_get_stackset_instance_status.assert_called()
    # assert get_stackset_instance_status is called with the passed arguments
    mocked_get_stackset_instance_status.assert_called_with(
        stackset_name, mocked_account_ids[0], mocked_regions[0], None
    )
    # assert the put_job_continuation is called
    mocked_put_job_continuation.assert_called_once()
    # assert it was called with the expected arguments
    mocked_put_job_continuation.assert_called_with(mocked_job_id, "StackSet update still in progress", None)

    # Case 3: asserting for the last branch status not one of ["RUNNING","PENDING", "SUCCEEDED"]:
    mocked_get_stackset_instance_status.return_value = "FAILED"
    check_stackset_update_status(mocked_job_id, stackset_name, mocked_account_ids[0], mocked_regions[0], None, None)
    # assert get_stackset_instance_status function is called
    mocked_get_stackset_instance_status.assert_called()
    # assert get_stackset_instance_status is called with the passed arguments
    mocked_get_stackset_instance_status.assert_called_with(
        stackset_name, mocked_account_ids[0], mocked_regions[0], None
    )
    # assert the put_job_continuation is called
    mocked_put_job_failure.assert_called_once()
    # assert it was called with the expected arguments
    mocked_put_job_failure.assert_called_with(mocked_job_id, "Update failed: FAILED", None)


def test_validate_user_params(required_user_params, mocked_decoded_parameters):
    # assert function will throw an exception if a required parameter is missing (e.g. template_file)
    required_parm = "template_file"
    decoded_parameters = mocked_decoded_parameters
    # remove the required parameter template_file
    del decoded_parameters[required_parm]
    with pytest.raises(Exception) as validation_error:
        validate_user_params(decoded_parameters, required_user_params)
    # assert the error message
    assert f"Your UserParameters JSON must include {required_parm}" in str(validation_error.value)


def test_get_user_params(
    required_user_params, mocked_decoded_parameters, mocked_codepipeline_event, mocked_invalid_user_parms
):
    # get the job data
    job_data = mocked_codepipeline_event[cp_job]["data"]
    # assert the user parameters are decoded correctly
    params = get_user_params(job_data)
    assert params == mocked_decoded_parameters
    # assert the decoding will fail if teh input can not be decoded
    with pytest.raises(Exception) as decoding_error:
        get_user_params(mocked_invalid_user_parms)
    # assert the error message
    assert "UserParameters could not be decoded as JSON" in str(decoding_error.value)


@patch("stackset_helpers.create_stackset_and_instances")
@patch("stackset_helpers.put_job_success")
@patch("stackset_helpers.put_job_continuation")
@patch("stackset_helpers.update_stackset")
@patch("stackset_helpers.put_job_failure")
@patch("stackset_helpers.get_stackset_instance_status")
@patch("stackset_helpers.stackset_exists")
def test_start_stackset_update_or_create(
    mocked_stackset_exists,  # NOSONAR:S107 this test function is designed to take many fixtures
    mocked_get_stackset_instance_status,
    mocked_put_job_failure,
    mocked_update_stackset,
    mocked_put_job_continuation,
    mocked_put_job_success,
    mocked_create_stackset_and_instances,
    mocked_job_id,
    stackset_name,
    mocked_template,
    mocked_template_parameters,
    mocked_org_ids,
    mocked_account_ids,
    mocked_regions,
):
    # Case 1: stack exists and status != "SUCCEEDED"
    mocked_stackset_exists.return_value = True
    mocked_get_stackset_instance_status.return_value = "FAILED"
    # Call the function
    start_stackset_update_or_create(
        mocked_job_id,
        stackset_name,
        mocked_template,
        mocked_template_parameters,
        mocked_account_ids,
        mocked_org_ids,
        mocked_regions,
        None,
        None,
    )
    mocked_stackset_exists.assert_called()
    mocked_get_stackset_instance_status.assert_called()
    mocked_put_job_failure.assert_called()

    # Case 2: stack exists, status == "SUCCEEDED" and update_stackset returns True
    mocked_get_stackset_instance_status.return_value = "SUCCEEDED"
    mocked_update_stackset.return_value = True
    # call the function
    start_stackset_update_or_create(
        mocked_job_id,
        stackset_name,
        mocked_template,
        json.loads(mocked_template_parameters),
        mocked_account_ids,
        mocked_org_ids,
        mocked_regions,
        None,
        None,
    )
    # the update_stackset should be called. Returns True
    mocked_update_stackset.assert_called()
    # since there are updates to the stackset, put_job_continuation should be called
    mocked_put_job_continuation.assert_called()

    # Case 3: stack exists, status == "SUCCEEDED" and update_stackset returns False (no updates to be performed)
    mocked_update_stackset.return_value = False
    # call the function
    start_stackset_update_or_create(
        mocked_job_id,
        stackset_name,
        mocked_template,
        json.loads(mocked_template_parameters),
        mocked_account_ids,
        mocked_org_ids,
        mocked_regions,
        None,
        None,
    )
    # the update_stackset should be called. Returns True
    mocked_update_stackset.assert_called()
    # since there are updates to the stackset, put_job_success should be called
    mocked_put_job_success.assert_called()

    # Case 4: stack does not exist
    mocked_stackset_exists.return_value = False
    # call the function
    start_stackset_update_or_create(
        mocked_job_id,
        stackset_name,
        mocked_template,
        json.loads(mocked_template_parameters),
        mocked_account_ids,
        mocked_org_ids,
        mocked_regions,
        None,
        None,
    )
    # The create_stackset_and_instances should be called
    mocked_create_stackset_and_instances.assert_called()
    # Since stackset and its instnace creation has started, put_job_continuation should be called
    mocked_put_job_continuation.assert_called()


def test_find_artifact(mocked_codepipeline_event, mocked_decoded_parameters):
    # Get the list of artifacts passed to the function
    artifacts = mocked_codepipeline_event[cp_job]["data"]["inputArtifacts"]
    # Case 1: artifact exists in the event
    existing_artifact = mocked_decoded_parameters["artifact"]
    artifact = find_artifact(artifacts, existing_artifact)
    assert artifact == artifacts[0]

    # Case 2: artifact does not exist (should throw an exception)
    missing_artifact = "MISSING_ARTIFACT"
    with pytest.raises(Exception) as artifact_error:
        find_artifact(artifacts, missing_artifact)
    # Assert the exception message
    assert f"Input artifact named {missing_artifact} not found in lambda's event" in str(artifact_error.value)


@patch("main.put_job_failure")
@patch("main.start_stackset_update_or_create")
@patch("main.get_template")
@patch("main.setup_s3_client")
@patch("main.find_artifact")
@patch("main.check_stackset_update_status")
@patch("main.get_user_params")
def test_lambda_handler(
    mocked_get_user_params,  # NOSONAR:S107 this test function is designed to take many fixtures
    mocked_check_stackset_update_status,
    mocked_find_artifact,
    mocked_setup_s3_client,
    mocked_get_template,
    mocked_start_stackset_update_or_create,
    mocked_put_job_failure,
    mocked_codepipeline_event,
    mocked_template,
    mocked_template_parameters,
):
    # Case 1: Lambda was called for the first time, no continuationToken in the job data
    mocked_get_template.return_value = (mocked_template, mocked_template_parameters)
    # call the function
    lambda_handler(mocked_codepipeline_event, {})
    # the following functions should be called
    mocked_get_user_params.assert_called()
    mocked_find_artifact.assert_called()
    mocked_setup_s3_client.assert_called()
    mocked_get_template.assert_called()
    mocked_start_stackset_update_or_create.assert_called()

    # Case 2: ContinuationToken in the job data
    # add ContinuationToken
    mocked_codepipeline_event[cp_job]["data"].update({"continuationToken": "A continuation token"})
    # call the function
    lambda_handler(mocked_codepipeline_event, {})
    # assert the check_stackset_update_status is called
    mocked_check_stackset_update_status.assert_called()

    # Case 3: An exception is thrown by one of the functions, and put_job_failure
    del mocked_codepipeline_event[cp_job]
    with pytest.raises(Exception):
        lambda_handler(mocked_codepipeline_event, {})
    mocked_put_job_failure.assert_called()


@mock_s3
def test_setup_s3_client(mocked_codepipeline_event):
    job_data = mocked_codepipeline_event[cp_job]["data"]
    s3_clinet = setup_s3_client(job_data)
    assert s3_clinet is not None


@mock_s3
@patch("zipfile.ZipFile")
def test_get_template(mocked_zipfile, mocked_codepipeline_event, mocked_regions):
    job_data = mocked_codepipeline_event[cp_job]["data"]
    temp_file = tempfile.NamedTemporaryFile()
    s3_clinet = boto3.client("s3", region_name=mocked_regions[0])
    s3_clinet.create_bucket(Bucket="test-bucket")
    s3_clinet.upload_file(temp_file.name, "test-bucket", "template.zip")
    artifact = job_data["inputArtifacts"][0]
    template, params = get_template(s3_clinet, artifact, "template.yaml", "staging-config-test.json")
    assert template is not None
    assert params is not None
