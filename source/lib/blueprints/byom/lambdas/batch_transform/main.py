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
import uuid
from shared.logger import get_logger
from shared.helper import get_client

logger = get_logger(__name__)
sm_client = get_client("sagemaker")


def handler(*_):
    try:
        model_name = os.environ.get("model_name").lower()
        batch_inference_data = os.environ.get("batch_inference_data")
        batch_job_output_location = os.environ.get("batch_job_output_location")
        inference_instance = os.environ.get("inference_instance")
        kms_key_arn = os.environ.get("kms_key_arn")
        batch_job_name = f"{model_name}-batch-transform-{str(uuid.uuid4())[:8]}"

        request = {
            "TransformJobName": batch_job_name,
            "ModelName": model_name,
            "TransformOutput": {
                "S3OutputPath": f"s3://{batch_job_output_location}",
                "Accept": "text/csv",
                "AssembleWith": "Line",
            },
            "TransformInput": {
                "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": f"s3://{batch_inference_data}"}},
                "ContentType": "text/csv",
                "SplitType": "Line",
                "CompressionType": "None",
            },
            "TransformResources": {"InstanceType": inference_instance, "InstanceCount": 1},
        }
        # add KmsKey if provided by the customer
        if kms_key_arn:
            request["TransformOutput"].update({"KmsKeyId": kms_key_arn})
            request["TransformResources"].update({"VolumeKmsKeyId": kms_key_arn})

        response = sm_client.create_transform_job(**request)
        logger.info(f"Response from create transform job request. response: {response}")
        logger.info(f"Created Transform job with name: {batch_job_name}")

    except Exception as e:
        logger.error(f"Error creating the batch transform job {batch_job_name}: {str(e)}")
        raise e
