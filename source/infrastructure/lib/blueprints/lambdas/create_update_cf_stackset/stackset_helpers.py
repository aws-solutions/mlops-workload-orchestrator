# #####################################################################################################################
#  Copyright  Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                #
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
from boto3.session import Session
import os
import zipfile
import tempfile
import botocore
from shared.logger import get_logger
from shared.helper import get_client

logger = get_logger(__name__)

# Get the AWS Orginization's setup of "CallAs"
# If delegated admin account is used, CALL_AS = "DELEGATED_ADMIN", else CALL_AS = "SELF").
call_as = os.environ.get("CALL_AS", "SELF")


def find_artifact(artifacts, name):
    """Finds the artifact 'name' among the 'artifacts'

    Args:
        artifacts: The list of artifacts available to the function
        name: The artifact we wish to use
    Returns:
        The artifact dictionary found
    Raises:
        Exception: If no matching artifact is found

    """
    for artifact in artifacts:
        if artifact["name"] == name:
            return artifact

    raise ValueError(f"Input artifact named {name} not found in lambda's event")


def get_template(s3_client, artifact, template_file_in_zip, params_file_in_zip):
    """Gets the template artifact

    Downloads the artifact from the S3 artifact store to a temporary file
    then extracts the zip and returns the file containing the CloudFormation
    template and temaplate parameters.

    Args:
        s3_client: boto3 configured S3 client
        artifact: The artifact to download
        template_file_in_zip: The path to the file within the zip containing the template
        params_file_in_zip: The path to the file within the zip containing the template parameters

    Returns:
        The (CloudFormation template as a string, template paramaters as json)

    Raises:
        Exception: Any exception thrown while downloading the artifact or unzipping it

    """
    bucket = artifact["location"]["s3Location"]["bucketName"]
    key = artifact["location"]["s3Location"]["objectKey"]

    with tempfile.NamedTemporaryFile() as tmp_file:
        s3_client.download_file(bucket, key, tmp_file.name)
        with zipfile.ZipFile(tmp_file.name, "r") as zip:
            template = zip.read(template_file_in_zip).decode()
            params = zip.read(params_file_in_zip).decode()
            return (template, params)


def update_stackset(stackset_name, template, parameters, org_ids, regions, cf_client):
    """Start a CloudFormation stack update

    Args:
        stackset_name: The stackset name to update
        template: The template to apply
        parameters: template parameters
        org_ids: list of target org_ids
        regions: list of target regions
        cf_client: Boto3 CloudFormation client

    Returns:
        True if an update was started, false if there were no changes
        to the template since the last update.

    Raises:
        Exception: Any exception besides "No updates are to be performed."

    """
    try:
        cf_client.update_stack_set(
            StackSetName=stackset_name,
            TemplateBody=template,
            Parameters=parameters,
            Capabilities=["CAPABILITY_NAMED_IAM"],
            PermissionModel="SERVICE_MANAGED",
            # If PermissionModel="SERVICE_MANAGED", "OrganizationalUnitIds" must be used
            # If PermissionModel="SELF_MANAGED", "AccountIds" must be used
            DeploymentTargets={"OrganizationalUnitIds": org_ids},
            AutoDeployment={"Enabled": False},
            Regions=regions,
            CallAs=call_as,
        )
        return True

    except botocore.exceptions.ClientError as e:
        logger.error(f"Error updating CloudFormation StackSet {stackset_name}. Error message: {str(e)}")
        raise e


def stackset_exists(stackset_name, cf_client):
    """Check if a stack exists or not

    Args:
        stackset_name: The stackset name to check
        cf_client: Boto3 CloudFormation client

    Returns:
        True or False depending on whether the stack exists

    Raises:
        Any exceptions raised .describe_stack_set() besides that
        the stackset doesn't exist.

    """
    try:
        logger.info(f"Checking if StackSet {stackset_name} exits.")
        cf_client.describe_stack_set(StackSetName=stackset_name, CallAs=call_as)
        return True
    except Exception as e:
        if f"{stackset_name} not found" in str(e) or f"{stackset_name} does not exist" in str(e):
            logger.info(f"StackSet {stackset_name} does not exist.")
            return False
        else:
            raise e


def create_stackset_and_instances(stackset_name, template, parameteres, org_ids, regions, cf_client):
    """Starts a new CloudFormation stackset and its instances creation

    Args:
        stackset_name: The stackset to be created
        template: The template for the stackset to be created with
        parameters: template parameters
        org_ids: list of target org_ids
        regions: list of target regions
        cf_client: Boto3 CloudFormation client

    Throws:
        Exception: Any exception thrown by .create_stack_set() or .create_stack_instances()
    """
    try:
        logger.info(f"creating stackset {stackset_name}")
        # create StackSet first
        cf_client.create_stack_set(
            StackSetName=stackset_name,
            TemplateBody=template,
            Parameters=parameteres,
            Capabilities=["CAPABILITY_NAMED_IAM"],
            PermissionModel="SERVICE_MANAGED",
            AutoDeployment={"Enabled": False},
            CallAs=call_as,
        )

        # Then create StackSet instances
        logger.info(f"creating instances for {stackset_name} StckSet")
        cf_client.create_stack_instances(
            StackSetName=stackset_name,
            DeploymentTargets={"OrganizationalUnitIds": org_ids},
            Regions=regions,
            CallAs=call_as,
        )

    except botocore.exceptions.ClientError as e:
        logger.error(f"Error creating StackSet {stackset_name} and its inatances")
        raise e


def get_stackset_instance_status(stackset_name, stack_instance_account_id, region, cf_client):
    """Get the status of an existing CloudFormation stackset's instance

    Args:
        stackset_name: The name of the stackset to check
        stack_instance_account_id: the account id, where the stack instance is deployed
        region: The region of the stackset's instance
        cf_client: Boto3 CloudFormation client

    Returns:
        The CloudFormation status string of the stackset instance
        ('PENDING'|'RUNNING'|'SUCCEEDED'|'FAILED'|'CANCELLED'|'INOPERABLE')

    Raises:
        Exception: Any exception thrown by .describe_stack_instance()

    """
    try:
        logger.info(f"Checking the status of {stackset_name} instance")
        stack_instance_description = cf_client.describe_stack_instance(
            StackSetName=stackset_name,
            StackInstanceAccount=stack_instance_account_id,
            StackInstanceRegion=region,
            CallAs=call_as,
        )
        # Status could be one of 'PENDING'|'RUNNING'|'SUCCEEDED'|'FAILED'|'CANCELLED'|'INOPERABLE'
        return stack_instance_description["StackInstance"]["StackInstanceStatus"]["DetailedStatus"]

    except botocore.exceptions.ClientError as e:
        logger.error(
            f"Error describing StackSet {stackset_name} instance in {region} for account {stack_instance_account_id}"
        )
        raise e


def put_job_success(job_id, message, cp_client):
    """Notify CodePipeline of a successful job

    Args:
        job_id: The CodePipeline job ID
        message: A message to be logged relating to the job status
        cp_client: Boto3 CodePipeline client

    Raises:
        Exception: Any exception thrown by .put_job_success_result()

    """
    logger.info(f"Putting job success for jobId: {job_id} with message: {message}")
    cp_client.put_job_success_result(jobId=job_id)


def put_job_failure(job_id, message, cp_client):
    """Notify CodePipeline of a failed job

    Args:
        job_id: The CodePipeline job ID
        message: A message to be logged relating to the job status
        cp_client: Boto3 CodePipeline client

    Raises:
        Exception: Any exception thrown by .put_job_failure_result()

    """
    logger.info(f"Putting job failure for jobId: {job_id} with message: {message}")
    cp_client.put_job_failure_result(jobId=job_id, failureDetails={"message": message, "type": "JobFailed"})


def put_job_continuation(job_id, message, cp_client):
    """Notify CodePipeline of a continuing job

    This will cause CodePipeline to invoke the function again with the
    supplied continuation token.

    Args:
        job_id: The JobID
        message: A message to be logged relating to the job status
        continuation_token: The continuation token
        cp_client: Boto3 CodePipeline client

    Raises:
        Exception: Any exception thrown by .put_job_success_result()

    """
    logger.info(f"Putting continuation token for jobId: {job_id} with message: {message}")
    # This data will be available when a new job is scheduled to continue the current execution
    continuation_token = json.dumps({"previous_job_id": job_id})
    cp_client.put_job_success_result(jobId=job_id, continuationToken=continuation_token)


def start_stackset_update_or_create(
    job_id,  # NOSONAR:S107 this function is designed to take many arguments
    stackset_name,
    template,
    parameteres,
    stack_instance_account_ids,
    org_ids,
    regions,
    cf_client,
    cp_client,
):
    """Starts the stackset update or create process

    If the stackset exists then update, otherwise create.

    Args:
        job_id: The ID of the CodePipeline job
        stackset_name: The stackset to create or update
        template: The template to create/update the stackset with
        parameters: template parameters
        stack_instance_account_ids: list of target account ids
        org_ids: list of target org_ids
        regions: list of target regions
        cf_client: Boto3 CloudFormation client
        cp_client: Boto3 CodePipeline client

    """
    if stackset_exists(stackset_name, cf_client):
        logger.info(f"Stackset {stackset_name} exists")
        status = get_stackset_instance_status(stackset_name, stack_instance_account_ids[0], regions[0], cf_client)
        # If the CloudFormation stackset instance is not in a 'SUCCEEDED' state, it can not be updated
        if status != "SUCCEEDED":
            # if the StackSet instance in a failed state, fail the job
            put_job_failure(
                job_id,
                (
                    f"StackSet cannot be updated when status is: {status}. Delete the faild stackset/instance,"
                    " fix the issue, and retry."
                ),
                cp_client,
            )
            return

        # Update the StackSet and its instances
        were_updates = update_stackset(stackset_name, template, parameteres, org_ids, regions, cf_client)

        if were_updates:
            # If there were updates then continue the job so it can monitor
            # the progress of the update.
            logger.info(f"Starting update for {stackset_name} StackSet")
            put_job_continuation(job_id, "StackSet update started", cp_client)

        else:
            # If there were no updates then succeed the job immediately
            logger.info(f"No updates for {stackset_name} StackSet")
            put_job_success(job_id, "There were no StackSet updates", cp_client)
    else:
        # If the StackSet doesn't already exist then create it and its instances
        create_stackset_and_instances(stackset_name, template, parameteres, org_ids, regions, cf_client)
        logger.info(f"Creatiation of {stackset_name} StackSet and its instances started")
        # Continue the job so the pipeline will wait for the StackSet and its instances to be created
        put_job_continuation(job_id, "StackSet and its instances creatiation started", cp_client)


def check_stackset_update_status(job_id, stackset_name, stack_instance_account_id, region, cf_client, cp_client):
    """Monitor an already-running CloudFormation StackSet and its instance update/create

    Succeeds, fails or continues the job depending on the stack status.

    Args:
        job_id: The CodePipeline job ID
        stackset_name: The stackset to monitor
        stack_instance_account_id: the account id
        region: The region, where the StackSet's instance is deployed
        cf_client: Boto3 CloudFormation client
        cp_client: Boto3 CodePipeline client

    """
    status = get_stackset_instance_status(stackset_name, stack_instance_account_id, region, cf_client)
    if status == "SUCCEEDED":
        # If the update/create finished successfully then
        # succeed the job and don't continue.
        put_job_success(job_id, "StackSet and its instance update complete", cp_client)

    elif status in [
        "RUNNING",
        "PENDING",
    ]:
        # If the job isn't finished yet then continue it
        put_job_continuation(job_id, "StackSet update still in progress", cp_client)

    else:
        # The stackSet update/create has failed so end the job with
        # a failed result.
        put_job_failure(job_id, f"Update failed: {status}", cp_client)


def validate_user_params(decoded_params, list_of_required_params):
    """Validate user provided parameters via codepipline event

    Raise an exception if one of the required parameters is missing.

    Args:
        decoded_params: json object of user parameters passed via codepipline's event
        list_of_required_params: list of required parameters

    Raises:
        Your UserParameters JSON must include <missing parameter's name>
    """
    for param in list_of_required_params:
        if param not in decoded_params:
            raise ValueError(f"Your UserParameters JSON must include {param}")


def get_user_params(job_data):
    """Decodes the JSON user parameters passed by codepipeline's event.

    Args:
        job_data: The job data structure containing the UserParameters string which should be a valid JSON structure

    Returns:
        The JSON parameters decoded as a dictionary.

    Raises:
        Exception: The JSON can't be decoded.

    """
    required_params = [
        "stackset_name",
        "artifact",
        "template_file",
        "stage_params_file",
        "account_ids",
        "org_ids",
        "regions",
    ]
    try:
        # Get the user parameters which contain the stackset_name, artifact, template_name,
        # stage_params, account_ids, org_ids, and regions
        user_parameters = job_data["actionConfiguration"]["configuration"]["UserParameters"]
        decoded_parameters = json.loads(user_parameters)

    except Exception as e:
        # We're expecting the user parameters to be encoded as JSON
        # so we can pass multiple values. If the JSON can't be decoded
        # then fail the job with a helpful message.
        raise ValueError("UserParameters could not be decoded as JSON", e)

    # Validate required params were provided
    validate_user_params(
        decoded_parameters,
        required_params,
    )

    return decoded_parameters


def setup_s3_client(job_data):
    """Creates an S3 client

    Uses the credentials passed in the event by CodePipeline. These
    credentials can be used to access the artifact bucket.

    Args:
        job_data: The job data structure

    Returns:
        An S3 client with the appropriate credentials

    """
    key_id = job_data["artifactCredentials"]["accessKeyId"]
    key_secret = job_data["artifactCredentials"]["secretAccessKey"]
    session_token = job_data["artifactCredentials"]["sessionToken"]

    session = Session(aws_access_key_id=key_id, aws_secret_access_key=key_secret, aws_session_token=session_token)

    return session.client("s3", config=botocore.client.Config(signature_version="s3v4"))
