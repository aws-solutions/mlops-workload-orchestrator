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
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_codepipeline_actions as codepipeline_actions,
    core,
)
from aws_solutions_constructs import aws_apigateway_lambda
from lib.blueprints.byom.pipeline_definitions.helpers import (
    codepipeline_policy,
    suppress_cloudwatch_policy,
)


# configure inference lambda step in the pipeline
def configure_inference(scope, blueprint_bucket):
    """
    configure_inference updates inference lambda function's environment variables and puts the value
    for Sagemaker endpoint URI as a lambda invoked codepipeline action

    :scope: CDK Construct scope that's needed to create CDK resources
    :blueprint_bucket: CDK object of the blueprint bucket that contains resources for BYOM pipeline
    :is_realtime_inference: a CDK CfnCondition object that says if inference type is realtime or not
    :return: codepipeline action in a form of a CDK object that can be attached to a codepipeline stage
    """
    # provision api gateway and lambda for inference using solution constructs
    inference_api_gateway = aws_apigateway_lambda.ApiGatewayToLambda(
        scope,
        "BYOMInference",
        lambda_function_props={
            "runtime": lambda_.Runtime.PYTHON_3_8,
            "handler": "main.handler",
            "code": lambda_.Code.from_bucket(blueprint_bucket, "blueprints/byom/lambdas/inference.zip"),
        },
        api_gateway_props={
            "defaultMethodOptions": {
                "authorizationType": apigw.AuthorizationType.IAM,
            },
            "restApiName": f"{core.Aws.STACK_NAME}-inference",
            "proxy": False,
        },
    )

    provision_resource = inference_api_gateway.api_gateway.root.add_resource("inference")
    provision_resource.add_method("POST")
    inference_api_gateway.lambda_function.add_to_role_policy(
        iam.PolicyStatement(
            actions=[
                "sagemaker:InvokeEndpoint",
            ],
            resources=[
                f"arn:{core.Aws.PARTITION}:sagemaker:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:endpoint/*",
            ],
        )
    )

    # lambda function that gets invoked from codepipeline
    configure_inference_lambda = lambda_.Function(
        scope,
        "configure_inference_lambda",
        runtime=lambda_.Runtime.PYTHON_3_8,
        handler="main.handler",
        code=lambda_.Code.from_bucket(blueprint_bucket, "blueprints/byom/lambdas/configure_inference_lambda.zip"),
        environment={
            "inference_lambda_arn": inference_api_gateway.lambda_function.function_arn,
            "LOG_LEVEL": "INFO",
        },
    )
    configure_inference_lambda.node.default_child.cfn_options.metadata = suppress_cloudwatch_policy()
    # iam permissions to respond to codepipeline and update inference lambda
    configure_inference_lambda.add_to_role_policy(
        iam.PolicyStatement(
            actions=[
                "lambda:UpdateFunctionConfiguration",
            ],
            resources=[inference_api_gateway.lambda_function.function_arn],
        )
    )
    configure_inference_lambda.add_to_role_policy(codepipeline_policy())

    role_child_nodes = configure_inference_lambda.role.node.find_all()
    role_child_nodes[2].node.default_child.cfn_options.metadata = {
        "cfn_nag": {
            "rules_to_suppress": [
                {
                    "id": "W12",
                    "reason": (
                        "The codepipeline permissions PutJobSuccessResult and PutJobFailureResult "
                        "are not able to be bound to resources."
                    ),
                }
            ]
        }
    }
    # configuring codepipeline action to invoke the lambda
    configure_inference_action = codepipeline_actions.LambdaInvokeAction(
        action_name="configure_inference_lambda",
        inputs=[],
        outputs=[],
        # passing the parameter from the last stage in pipeline
        user_parameters=[{"endpointName": "#{sagemaker_endpoint.endpointName}"}],
        lambda_=configure_inference_lambda,
    )

    return (configure_inference_lambda.function_arn, configure_inference_action)
