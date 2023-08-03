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
from aws_cdk import Aws, Fn, aws_sagemaker as sagemaker


def create_sagemaker_model(
    scope,  # NOSONAR:S107 this function is designed to take many arguments
    id,
    execution_role,
    model_registry_provided,
    algorithm_image_uri,
    assets_bucket_name,
    model_artifact_location,
    model_package_name,
    model_name,
    **kwargs,
):
    # Create the model
    model = sagemaker.CfnModel(
        scope,
        id,
        execution_role_arn=execution_role.role_arn,
        # the primary container is set based on whether the SageMaker model registry is used or not
        # if model registry is used, the "modelPackageName" must be provided
        # else "image" and "modelDataUrl" must be provided
        # "image" and "modelDataUrl" will be ignored if "modelPackageName" is provided
        primary_container={
            "image": Fn.condition_if(
                model_registry_provided.logical_id, Aws.NO_VALUE, algorithm_image_uri
            ).to_string(),
            "modelDataUrl": Fn.condition_if(
                model_registry_provided.logical_id,
                Aws.NO_VALUE,
                f"s3://{assets_bucket_name}/{model_artifact_location}",
            ).to_string(),
            "modelPackageName": Fn.condition_if(
                model_registry_provided.logical_id, model_package_name, Aws.NO_VALUE
            ).to_string(),
        },
        tags=[{"key": "model_name", "value": model_name}],
        **kwargs,
    )

    # add dependency on the Sagemaker execution role
    model.node.add_dependency(execution_role)

    return model
