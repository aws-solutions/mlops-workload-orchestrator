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
from aws_cdk import Aws, RemovalPolicy, aws_sagemaker as sagemaker


def create_sagemaker_model_registry(scope, id, model_package_group_name):
    """
    create_sagemaker_model_registry creates SageMaker model package group (i.e., model registry)

    :scope: CDK Construct scope that's needed to create CDK resources
    :model_package_group_name: the name of the model package group name to be created

    :return: SageMaker model package group CDK object
    """
    # create model registry
    model_registry = sagemaker.CfnModelPackageGroup(
        scope,
        id,
        model_package_group_name=model_package_group_name,
        model_package_group_description="SageMaker model package group name (model registry) for mlops",
        tags=[{"key": "stack-name", "value": Aws.STACK_NAME}],
    )

    # add update/deletion policy
    model_registry.apply_removal_policy(RemovalPolicy.RETAIN)

    return model_registry
