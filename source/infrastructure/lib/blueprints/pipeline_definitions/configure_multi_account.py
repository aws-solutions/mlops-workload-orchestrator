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
    aws_iam as iam,
)
from lib.blueprints.pipeline_definitions.iam_policies import (
    s3_policy_read,
    create_ecr_repo_policy,
    model_package_group_policy,
)
from lib.blueprints.pipeline_definitions.templates_parameters import (
    ParameteresFactory as pf,
)


def configure_multi_account_parameters_permissions(
    scope,  # NOSONAR:S107 this function is designed to take many arguments
    assets_bucket,
    blueprint_repository_bucket,
    ecr_repo,
    model_registry,
    orchestrator_lambda_function,
    paramaters_list,
    paramaters_labels,
):
    """
    configure_multi_account_parameters_permissions creates parameters and permissions for the multi-account option

    :scope: CDK Construct scope that's needed to create CDK resources
    :blueprint_bucket: CDK object of the blueprint bucket that contains resources for BYOM pipeline
    :assets_bucket: the bucket cdk object where pipeline assets are stored
    :ecr_repo: ecr_repo CDK object
    :model_registry: model_registry CDK object
    :orchestrator_lambda_function: orchestrator lambda function CDK object
    :paramaters_list: list parameters' logical ids
    :paramaters_labels: dictionary of paramaters labels

    :return: (paramaters_list, paramaters_labels, send_data_cr_properties)
    """
    # add parameters
    # delegated admin account
    is_delegated_admin = pf.create_delegated_admin_parameter(scope)
    # create development parameters
    account_type = "development"
    dev_account_id = pf.create_account_id_parameter(scope, "DevAccountId", account_type)
    dev_org_id = pf.create_org_id_parameter(scope, "DevOrgId", account_type)
    # create staging parameters
    account_type = "staging"
    staging_account_id = pf.create_account_id_parameter(
        scope, "StagingAccountId", account_type
    )
    staging_org_id = pf.create_org_id_parameter(scope, "StagingOrgId", account_type)
    # create production parameters
    account_type = "production"
    prod_account_id = pf.create_account_id_parameter(
        scope, "ProdAccountId", account_type
    )
    prod_org_id = pf.create_org_id_parameter(scope, "ProdOrgId", account_type)

    principals = [
        iam.AccountPrincipal(dev_account_id.value_as_string),
        iam.AccountPrincipal(staging_account_id.value_as_string),
        iam.AccountPrincipal(prod_account_id.value_as_string),
    ]

    # add permission to access the assets bucket
    assets_bucket.add_to_resource_policy(
        s3_policy_read(
            [assets_bucket.bucket_arn, f"{assets_bucket.bucket_arn}/*"],
            principals,
        )
    )

    # add permissions for other accounts to access the blueprint bucket
    blueprint_repository_bucket.add_to_resource_policy(
        s3_policy_read(
            [
                blueprint_repository_bucket.bucket_arn,
                f"{blueprint_repository_bucket.bucket_arn}/*",
            ],
            principals,
        )
    )

    # add permissions to other account to pull images
    ecr_repo.add_to_resource_policy(create_ecr_repo_policy(principals))

    # give other accounts permissions to use the model registry
    model_registry.add_property_override(
        "ModelPackageGroupPolicy",
        model_package_group_policy(
            model_registry.model_package_group_name,
            [
                dev_account_id.value_as_string,
                staging_account_id.value_as_string,
                prod_account_id.value_as_string,
            ],
        ),
    )

    # add environment variables to orchestrator lambda function
    orchestrator_lambda_function.add_environment(
        key="IS_DELEGATED_ADMIN", value=is_delegated_admin.value_as_string
    )
    orchestrator_lambda_function.add_environment(
        key="DEV_ACCOUNT_ID", value=dev_account_id.value_as_string
    )
    orchestrator_lambda_function.add_environment(
        key="DEV_ORG_ID", value=dev_org_id.value_as_string
    )
    orchestrator_lambda_function.add_environment(
        key="STAGING_ACCOUNT_ID", value=staging_account_id.value_as_string
    )
    orchestrator_lambda_function.add_environment(
        key="STAGING_ORG_ID", value=staging_org_id.value_as_string
    )
    orchestrator_lambda_function.add_environment(
        key="PROD_ACCOUNT_ID", value=prod_account_id.value_as_string
    )
    orchestrator_lambda_function.add_environment(
        key="PROD_ORG_ID", value=prod_org_id.value_as_string
    )

    # add parameters
    paramaters_list.extend(
        [
            is_delegated_admin.logical_id,
            dev_account_id.logical_id,
            dev_org_id.logical_id,
            staging_account_id.logical_id,
            staging_org_id.logical_id,
            prod_account_id.logical_id,
            prod_org_id.logical_id,
        ]
    )
    # add labels
    paramaters_labels.update(
        {
            f"{is_delegated_admin.logical_id}": {
                "default": "Are you using a delegated administrator account (AWS Organizations)?"
            },
            f"{dev_account_id.logical_id}": {
                "default": "Development Account ID (Required)"
            },
            f"{dev_org_id.logical_id}": {
                "default": "Development Account Organizational Unit ID (Required)"
            },
            f"{staging_account_id.logical_id}": {
                "default": "Staging Account ID (Required)"
            },
            f"{staging_org_id.logical_id}": {
                "default": "Staging Account Organizational Unit ID (Required)"
            },
            f"{prod_account_id.logical_id}": {
                "default": "Production Account ID (Required)"
            },
            f"{prod_org_id.logical_id}": {
                "default": "Production Account Organizational Unit ID (Required)"
            },
        }
    )

    # return parameters, labels, and is_delegated_admin
    return (paramaters_list, paramaters_labels, is_delegated_admin.value_as_string)
