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
from aws_cdk import (
    aws_iam as iam,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_codepipeline_actions as codepipeline_actions,
    core,
)
from lib.blueprints.byom.pipeline_definitions.helpers import (
    codepipeline_policy,
    suppress_cloudwatch_policy,
    suppress_pipeline_policy,
    suppress_ecr_policy,
    add_logs_policy,
)


def sagemaker_layer(scope, blueprint_bucket):
    """
    sagemaker_layer creates a Lambda layer with Sagemaker SDK installed in it to allow Lambda functions call
    Sagemaker SDK's methods such as create_model(), etc.

    :blueprint_bucket: CDK object of the blueprint bucket that contains resources for BYOM pipeline
    :scope: CDK Construct scope that's needed to create CDK resources
    :return: Lambda layer version in a form of a CDK object
    """
    # Lambda sagemaker layer for sagemaker sdk that is used in create sagemaker model step
    return lambda_.LayerVersion(
        scope,
        "sagemakerlayer",
        code=lambda_.Code.from_bucket(
            blueprint_bucket, "blueprints/byom/lambdas/sagemaker_layer.zip"
        ),
        compatible_runtimes=[lambda_.Runtime.PYTHON_3_8],
    )


def create_model(
    scope,
    blueprint_bucket,
    assets_bucket,
    model_name,
    model_artifact_location,
    custom_container,
    model_framework,
    model_framework_version,
    container_uri,
    sm_layer,
):
    """
    create_model creates a sagemaker model in a lambda invoked codepipeline action

    :scope: CDK Construct scope that's needed to create CDK resources
    :blueprint_bucket: CDK object of the blueprint bucket that contains resources for BYOM pipeline
    :assets_bucket: the bucket cdk object where pipeline assets are stored
    :model_name: name of the sagemaker model to be created, in the form of a CDK CfnParameter object
    :model_artifact_location: path to the model artifact in the S3 bucket: assets_bucket
    :custom_container: whether to the model is a custom algorithm or a sagemaker algorithmm, in the form of a CDK CfnParameter object
    :model_framework: name of the framework if the model is a sagemaker algorithm, in the form of a CDK CfnParameter object
    :model_framework_version: version of the framework if the model is a sagemaker algorithm, in the form of a CDK CfnParameter object
    :container_uri: URI for the container registry that stores the model if the model is a custom algorithm
    :sm_layer: sagemaker lambda layer
    :return: codepipeline action in a form of a CDK object that can be attached to a codepipeline stage
    """
    create_model_policy = iam.PolicyStatement(
        actions=[
            "sagemaker:CreateModel",
            "sagemaker:DescribeModel",
            "sagemaker:DeleteModel",
        ],
        resources=[
            # Lambda that uses this polict requires access to all objects in the assets bucket
            f"arn:{core.Aws.PARTITION}:s3:::{assets_bucket.bucket_name}/*",
            f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:model/{model_name.value_as_string}",
        ],
    )
    s3_policy = iam.PolicyStatement(
        actions=[
            "s3:GetObject",
            "s3:PutObject",
            "s3:ListBucket",
        ],
        resources=[assets_bucket.arn_for_objects("*"), assets_bucket.bucket_arn],
    )
    # creating this policy for sagemaker create endpoint in custom model
    ecr_policy = iam.PolicyStatement(
        actions=[
            "ecr:BatchGetImage",
            "ecr:BatchCheckLayerAvailability",
            "ecr:DescribeImages",
            "ecr:DescribeRepositories",
            "ecr:GetDownloadUrlForLayer"
        ],
        resources=[
            f"arn:{core.Aws.PARTITION}:ecr:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:repository/awsmlopsmodels*"
        ]
    )
    ecr_token_policy = iam.PolicyStatement(
        actions=["ecr:GetAuthorizationToken"],
        resources=["*"] # GetAuthorizationToken can not be bound to resources other than *
    )
    # creating a role for the lambda function so that it can create a model in sagemaker
    sagemaker_role = iam.Role(
        scope,
        "create_model_sagemaker_role",
        assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
        description="Role that is create sagemaker model Lambda function assumes to create a model in the pipeline.",
    )
    lambda_role = iam.Role(
        scope,
        "create_model_lambda_role",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        description="Role that is create sagemaker model Lambda function assumes to create a model in the pipeline.",
    )
    sagemaker_role.add_to_policy(create_model_policy)
    sagemaker_role.add_to_policy(s3_policy)
    sagemaker_role.add_to_policy(ecr_policy)
    sagemaker_role.add_to_policy(ecr_token_policy)
    sagemaker_role_nodes = sagemaker_role.node.find_all()
    sagemaker_role_nodes[
        2
    ].node.default_child.cfn_options.metadata = suppress_ecr_policy()
    lambda_role.add_to_policy(
        iam.PolicyStatement(
            actions=["iam:PassRole"], resources=[sagemaker_role.role_arn]
        )
    )
    lambda_role.add_to_policy(create_model_policy)
    lambda_role.add_to_policy(s3_policy)
    add_logs_policy(lambda_role)

    # defining the lambda function that gets invoked by codepipeline in this step
    create_sagemaker_model = lambda_.Function(
        scope,
        "create_sagemaker_model",
        runtime=lambda_.Runtime.PYTHON_3_8,
        handler="main.handler",
        timeout=core.Duration.seconds(60),
        code=lambda_.Code.from_bucket(
            blueprint_bucket, "blueprints/byom/lambdas/create_sagemaker_model.zip"
        ),
        layers=[sm_layer],
        role=lambda_role,
        environment={
            "custom_container": custom_container.value_as_string,
            "model_framework": model_framework.value_as_string,
            "model_framework_version": model_framework_version.value_as_string,
            "model_name": model_name.value_as_string,
            "model_artifact_location": assets_bucket.s3_url_for_object(
                model_artifact_location.value_as_string
            ),
            "create_model_role_arn": sagemaker_role.role_arn,
            "container_uri": container_uri,
            "LOG_LEVEL": "INFO",
        },
    )
    create_sagemaker_model.node.default_child.cfn_options.metadata = (
        suppress_cloudwatch_policy()
    )
    role_child_nodes = create_sagemaker_model.role.node.find_all()
    role_child_nodes[
        2
    ].node.default_child.cfn_options.metadata = suppress_pipeline_policy()

    # creating the codepipeline action that invokes create model lambda
    create_sagemaker_model_action = codepipeline_actions.LambdaInvokeAction(
        action_name="create_sagemaker_model",
        inputs=[],
        outputs=[],
        lambda_=create_sagemaker_model,
        run_order=1,  # runs first in the Deploy stage
    )
    return create_sagemaker_model_action


def create_endpoint(
    scope, blueprint_bucket, assets_bucket, model_name, inference_instance
):
    """
    create_endpoint creates a sagemaker inference endpoint in a lambda invoked codepipeline action

    :scope: CDK Construct scope that's needed to create CDK resources
    :blueprint_bucket: CDK object of the blueprint bucket that contains resources for BYOM pipeline
    :assets_bucket: the bucket cdk object where pipeline assets are stored
    :model_name: name of the sagemaker model to be created, in the form of a CDK CfnParameter object
    :inference_instance: compute instance type for the sagemaker inference endpoint, in the form of a CDK CfnParameter object
    :is_realtime_inference: a CDK CfnCondition object that says if inference type is realtime or not
    :return: codepipeline action in a form of a CDK object that can be attached to a codepipeline stage
    """
    create_endpoint_policy = iam.PolicyStatement(
        actions=[
            "sagemaker:CreateEndpoint",
            "sagemaker:CreateEndpointConfig",
            "sagemaker:DeleteEndpointConfig",
            "sagemaker:DescribeEndpointConfig",
            "sagemaker:DescribeEndpoint",
        ],
        resources=[
            f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:endpoint/{model_name.value_as_string}-endpoint",
            f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:endpoint-config/{model_name.value_as_string}-endpoint-config",
        ],
    )
    # creating a role so that this lambda can create a sagemaker endpoint and endpoint config
    lambda_role = iam.Role(
        scope,
        "create_endpoint_lambda_role",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        description="Role that is create sagemaker model Lambda function assumes to create a model in the pipeline.",
    )
    lambda_role.add_to_policy(create_endpoint_policy)
    add_logs_policy(lambda_role)

    # defining the lambda function that gets invoked in this stage
    create_sagemaker_endpoint = lambda_.Function(
        scope,
        "create_sagemaker_endpoint",
        runtime=lambda_.Runtime.PYTHON_3_8,
        handler="main.handler",
        role=lambda_role,
        code=lambda_.Code.from_bucket(
            blueprint_bucket, "blueprints/byom/lambdas/create_sagemaker_endpoint.zip"
        ),
        environment={
            "model_name": model_name.value_as_string,
            "inference_instance": inference_instance.value_as_string,
            "assets_bucket": assets_bucket.bucket_name,
            "LOG_LEVEL": "INFO",
        },
        timeout=core.Duration.minutes(10),
    )
    create_sagemaker_endpoint.node.default_child.cfn_options.metadata = (
        suppress_cloudwatch_policy()
    )
    role_child_nodes = create_sagemaker_endpoint.role.node.find_all()
    role_child_nodes[
        2
    ].node.default_child.cfn_options.metadata = suppress_pipeline_policy()

    # create_endpoint_action = core.Fn.condition_if("isRealtimeInference",
    create_endpoint_action = codepipeline_actions.LambdaInvokeAction(
        action_name="create_sagemaker_endpoint",
        inputs=[],
        outputs=[],
        variables_namespace="sagemaker_endpoint",
        lambda_=create_sagemaker_endpoint,
        run_order=2,  # this runs second in the deploy stage
    )
    return create_endpoint_action


def batch_transform(
    scope,
    blueprint_bucket,
    assets_bucket,
    model_name,
    inference_instance,
    batch_inference_data,
    sm_layer,
):
    """
    batch_transform creates a sagemaker batch transform job in a lambda invoked codepipeline action

    :scope: CDK Construct scope that's needed to create CDK resources
    :blueprint_bucket: CDK object of the blueprint bucket that contains resources for BYOM pipeline
    :assets_bucket: the bucket cdk object where pipeline assets are stored
    :model_name: name of the sagemaker model to be created, in the form of a CDK CfnParameter object
    :inference_instance: compute instance type for the sagemaker inference endpoint, in the form of a CDK CfnParameter object
    :batch_inference_data: location of the batch inference data in assets bucket, in the form of a CDK CfnParameter object
    :is_batch_transform: a CDK CfnCondition object that says if inference type is batch transform or not
    :sm_layer: sagemaker lambda layer
    :return: codepipeline action in a form of a CDK object that can be attached to a codepipeline stage
    """
    batch_transform_policy = iam.PolicyStatement(
        actions=[
            "sagemaker:CreateTransformJob",
            "s3:ListBucket",
            "s3:GetObject",
            "s3:PutObject",
        ],
        resources=[
            assets_bucket.bucket_arn,
            assets_bucket.arn_for_objects("*"),
            f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:transform-job/{model_name.value_as_string}-*",
        ],
    )
    lambda_role = iam.Role(
        scope,
        "batch_transform_lambda_role",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        description="Role that creates a lambda function assumes to create a sagemaker batch transform job in the  aws mlops pipeline.",
    )
    lambda_role.add_to_policy(batch_transform_policy)
    lambda_role.add_to_policy(codepipeline_policy())
    add_logs_policy(lambda_role)

    # defining batch transform lambda function
    batch_transform = lambda_.Function(
        scope,
        "batch_transform",
        runtime=lambda_.Runtime.PYTHON_3_8,
        handler="main.handler",
        layers=[sm_layer],
        role=lambda_role,
        code=lambda_.Code.from_bucket(
            blueprint_bucket, "blueprints/byom/lambdas/batch_transform.zip"
        ),
        environment={
            "model_name": model_name.value_as_string,
            "inference_instance": inference_instance.value_as_string,
            "assets_bucket": assets_bucket.bucket_name,
            "batch_inference_data": batch_inference_data.value_as_string,
            "LOG_LEVEL": "INFO",
        },
    )
    batch_transform.node.default_child.cfn_options.metadata = (
        suppress_cloudwatch_policy()
    )
    role_child_nodes = batch_transform.role.node.find_all()
    role_child_nodes[
        2
    ].node.default_child.cfn_options.metadata = suppress_pipeline_policy()

    batch_transform_action = codepipeline_actions.LambdaInvokeAction(
        action_name="batch_transform",
        inputs=[],
        outputs=[],
        variables_namespace="batch_transform",
        lambda_=batch_transform,
        run_order=2,  # this runs second in the deploy stage
    )
    return batch_transform_action
