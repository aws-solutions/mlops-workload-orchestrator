# #####################################################################################################################
#  Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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
import traceback
from stackset_helpers import (
    find_artifact,
    get_template,
    put_job_failure,
    start_stackset_update_or_create,
    check_stackset_update_status,
    get_user_params,
    setup_s3_client,
)
from shared.logger import get_logger
from shared.helper import get_client

logger = get_logger(__name__)

logger.info("Loading stackset helpers...")

cf_client = get_client("cloudformation")
cp_client = get_client("codepipeline")


def lambda_handler(event, _):
    """The Lambda function handler

    If a continuing job then checks the CloudFormation stackset and its instances status
    and updates the job accordingly.

    If a new job then kick of an update or creation of the target
    CloudFormation stackset and its instances.

    Args:
        event: The event passed by Lambda
        context: The context passed by Lambda

    """
    job_id = None
    try:
        # Extract the Job ID
        job_id = event["CodePipeline.job"]["id"]

        # Extract the Job Data
        job_data = event["CodePipeline.job"]["data"]

        # Get user paramameters
        # User data is expected to be passed to lambda , for example:
        # {"stackset_name": "model2", "artifact":"SourceArtifact",
        # "template_file":"realtime-inference-pipeline.yaml",
        # "stage_params_file":"staging-config.json",
        # "account_ids":["<account_id>"], "org_ids":["<org_unit_id>"],
        # "regions":["us-east-1"]}
        params = get_user_params(job_data)

        # Get the list of artifacts passed to the function
        artifacts = job_data["inputArtifacts"]
        # Extract parameters
        stackset_name = params["stackset_name"]
        artifact = params["artifact"]
        template_file = params["template_file"]
        stage_params_file = params["stage_params_file"]
        account_ids = params["account_ids"]
        org_ids = params["org_ids"]
        regions = params["regions"]

        if "continuationToken" in job_data:
            logger.info(f"Checking the status of {stackset_name}")
            # If we're continuing then the create/update has already been triggered
            # we just need to check if it has finished.
            check_stackset_update_status(job_id, stackset_name, account_ids[0], regions[0], cf_client, cp_client)

        else:
            logger.info(f"Creating StackSet {stackset_name} and its instances")
            # Get the artifact details
            artifact_data = find_artifact(artifacts, artifact)
            # Get S3 client to access artifact with
            s3 = setup_s3_client(job_data)
            # Get the JSON template file out of the artifact
            template, stage_params = get_template(s3, artifact_data, template_file, stage_params_file)
            logger.info(stage_params)
            # Kick off a stackset update or create
            start_stackset_update_or_create(
                job_id,
                stackset_name,
                template,
                json.loads(stage_params),
                account_ids,
                org_ids,
                regions,
                cf_client,
                cp_client,
            )

    except Exception as e:
        logger.error(f"Error in create_update_cf_stackset lambda functions: {str(e)}")
        traceback.print_exc()
        put_job_failure(job_id, "Function exception", cp_client)
        raise e
