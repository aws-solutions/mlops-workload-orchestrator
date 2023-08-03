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
from aws_cdk import (
    aws_sagemaker as sagemaker,
)


def create_sagemaker_endpoint_config(
    scope,  # NOSONAR:S107 this function is designed to take many arguments
    id,
    sagemaker_model_name,
    model_name,
    inference_instance,
    data_capture_location,
    kms_key_arn,
    **kwargs,
):
    # Create the sagemaker endpoint config
    sagemaker_endpoint_config = sagemaker.CfnEndpointConfig(
        scope,
        id,
        production_variants=[
            {
                "variantName": "AllTraffic",
                "modelName": sagemaker_model_name,
                "initialVariantWeight": 1,
                "initialInstanceCount": 1,
                "instanceType": inference_instance,
            }
        ],
        data_capture_config={
            "enableCapture": True,
            "initialSamplingPercentage": 100,
            "destinationS3Uri": f"s3://{data_capture_location}",
            "captureOptions": [{"captureMode": "Output"}, {"captureMode": "Input"}],
            "captureContentTypeHeader": {"csvContentTypes": ["text/csv"]},
            # The key specified here is used to encrypt data on S3 captured by the endpoint. If you don't provide
            # a KMS key ID, Amazon SageMaker uses the default KMS key for Amazon S3 for your role's account.
            # for more info see DataCaptureConfig
            # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-endpointconfig.html
            "kmsKeyId": kms_key_arn,
        },
        # The key specified here is used to encrypt data on the storage volume attached to the
        # ML compute instance that hosts the endpoint. Note: a key can not be specified here when
        # using an instance type with local storage (e.g. certain Nitro-based instances)
        # for more info see the KmsKeyId doc at
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-endpointconfig.html
        kms_key_id=kms_key_arn,
        tags=[{"key": "endpoint-config-name", "value": f"{model_name}-endpoint-config"}],
        **kwargs,
    )

    return sagemaker_endpoint_config
