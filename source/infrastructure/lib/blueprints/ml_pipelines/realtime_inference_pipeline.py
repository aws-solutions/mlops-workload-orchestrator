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
from constructs import Construct
from aws_cdk import (
    Stack,
    Aws,
    Fn,
    Duration,
    CfnOutput,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_apigateway as apigw,
)

from aws_solutions_constructs.aws_lambda_sagemakerendpoint import (
    LambdaToSagemakerEndpoint,
)
from aws_solutions_constructs import aws_apigateway_lambda
from lib.blueprints.pipeline_definitions.sagemaker_role import (
    create_sagemaker_role,
)
from lib.blueprints.pipeline_definitions.sagemaker_model import (
    create_sagemaker_model,
)
from lib.blueprints.pipeline_definitions.sagemaker_endpoint_config import (
    create_sagemaker_endpoint_config,
)
from lib.blueprints.pipeline_definitions.sagemaker_endpoint import (
    create_sagemaker_endpoint,
)
from lib.blueprints.pipeline_definitions.helpers import suppress_lambda_policies
from lib.blueprints.pipeline_definitions.templates_parameters import (
    ParameteresFactory as pf,
    ConditionsFactory as cf,
)


class BYOMRealtimePipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Parameteres #
        assets_bucket_name = pf.create_assets_bucket_name_parameter(self)
        blueprint_bucket_name = pf.create_blueprint_bucket_name_parameter(self)
        custom_algorithms_ecr_repo_arn = (
            pf.create_custom_algorithms_ecr_repo_arn_parameter(self)
        )
        kms_key_arn = pf.create_kms_key_arn_parameter(self)
        algorithm_image_uri = pf.create_algorithm_image_uri_parameter(self)
        model_name = pf.create_model_name_parameter(self)
        model_artifact_location = pf.create_model_artifact_location_parameter(self)
        data_capture_location = pf.create_data_capture_location_parameter(self)
        inference_instance = pf.create_inference_instance_parameter(self)
        model_package_group_name = pf.create_model_package_group_name_parameter(self)
        model_package_name = pf.create_model_package_name_parameter(self)
        # add the optional endpoint_name
        endpoint_name = pf.create_endpoint_name_parameter(self, optional=True)

        # Conditions
        custom_algorithms_ecr_repo_arn_provided = (
            cf.create_custom_algorithms_ecr_repo_arn_provided_condition(
                self, custom_algorithms_ecr_repo_arn
            )
        )
        kms_key_arn_provided = cf.create_kms_key_arn_provided_condition(
            self, kms_key_arn
        )
        model_registry_provided = cf.create_model_registry_provided_condition(
            self, model_package_name
        )
        endpoint_name_provided = cf.create_endpoint_name_provided_condition(
            self, endpoint_name
        )

        # Resources #
        # getting blueprint bucket object from its name - will be used later in the stack
        blueprint_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedBlueprintBucket", blueprint_bucket_name.value_as_string
        )

        # provision api gateway and lambda for inference using solution constructs
        inference_api_gateway = aws_apigateway_lambda.ApiGatewayToLambda(
            self,
            "BYOMInference",
            lambda_function_props={
                "runtime": lambda_.Runtime.PYTHON_3_10,
                "handler": "main.handler",
                "code": lambda_.Code.from_bucket(
                    blueprint_bucket, "blueprints/lambdas/inference.zip"
                ),
                "timeout": Duration.minutes(5),
            },
            api_gateway_props={
                "defaultMethodOptions": {
                    "authorizationType": apigw.AuthorizationType.IAM,
                },
                "restApiName": f"{Aws.STACK_NAME}-inference",
                "proxy": False,
            },
        )
        # add suppressions
        inference_api_gateway.lambda_function.node.default_child.cfn_options.metadata = (
            suppress_lambda_policies()
        )
        provision_resource = inference_api_gateway.api_gateway.root.add_resource(
            "inference"
        )
        provision_resource.add_method("POST")

        # create Sagemaker role
        sagemaker_role = create_sagemaker_role(
            self,
            "MLOpsRealtimeSagemakerRole",
            custom_algorithms_ecr_arn=custom_algorithms_ecr_repo_arn.value_as_string,
            kms_key_arn=kms_key_arn.value_as_string,
            model_package_group_name=model_package_group_name.value_as_string,
            assets_bucket_name=assets_bucket_name.value_as_string,
            input_bucket_name=assets_bucket_name.value_as_string,
            input_s3_location=assets_bucket_name.value_as_string,
            output_s3_location=data_capture_location.value_as_string,
            ecr_repo_arn_provided_condition=custom_algorithms_ecr_repo_arn_provided,
            kms_key_arn_provided_condition=kms_key_arn_provided,
            model_registry_provided_condition=model_registry_provided,
            is_realtime_pipeline=True,
            endpoint_name=endpoint_name,
            endpoint_name_provided=endpoint_name_provided,
        )

        # create sagemaker model
        sagemaker_model = create_sagemaker_model(
            self,
            "MLOpsSagemakerModel",
            execution_role=sagemaker_role,
            model_registry_provided=model_registry_provided,
            algorithm_image_uri=algorithm_image_uri.value_as_string,
            assets_bucket_name=assets_bucket_name.value_as_string,
            model_artifact_location=model_artifact_location.value_as_string,
            model_package_name=model_package_name.value_as_string,
            model_name=model_name.value_as_string,
        )

        # Create Sagemaker EndpointConfig
        sagemaker_endpoint_config = create_sagemaker_endpoint_config(
            scope=self,
            id="MLOpsSagemakerEndpointConfig",
            sagemaker_model_name=sagemaker_model.attr_model_name,
            model_name=model_name.value_as_string,
            inference_instance=inference_instance.value_as_string,
            data_capture_location=data_capture_location.value_as_string,
            kms_key_arn=Fn.condition_if(
                kms_key_arn_provided.logical_id,
                kms_key_arn.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
        )

        # create a dependency on the model
        sagemaker_endpoint_config.add_dependency(sagemaker_model)

        # create Sagemaker endpoint
        sagemaker_endpoint = create_sagemaker_endpoint(
            scope=self,
            id="MLOpsSagemakerEndpoint",
            endpoint_config_name=sagemaker_endpoint_config.attr_endpoint_config_name,
            endpoint_name=Fn.condition_if(
                endpoint_name_provided.logical_id,
                endpoint_name.value_as_string,
                Aws.NO_VALUE,
            ).to_string(),
            model_name=model_name.value_as_string,
        )

        # add dependency on endpoint config
        sagemaker_endpoint.add_dependency(sagemaker_endpoint_config)

        # Create Lambda - sagemakerendpoint
        LambdaToSagemakerEndpoint(
            self,
            "LambdaSagmakerEndpoint",
            existing_sagemaker_endpoint_obj=sagemaker_endpoint,
            existing_lambda_obj=inference_api_gateway.lambda_function,
        )

        # Outputs #
        CfnOutput(
            self,
            id="SageMakerModelName",
            value=sagemaker_model.attr_model_name,
        )
        CfnOutput(
            self,
            id="SageMakerEndpointConfigName",
            value=sagemaker_endpoint_config.attr_endpoint_config_name,
        )
        CfnOutput(
            self,
            id="SageMakerEndpointName",
            value=sagemaker_endpoint.attr_endpoint_name,
        )
        CfnOutput(
            self,
            id="EndpointDataCaptureLocation",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{data_capture_location.value_as_string}/",
            description="Endpoint data capture location (to be used by Model Monitor)",
        )
