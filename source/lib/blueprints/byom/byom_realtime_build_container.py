# #####################################################################################################################
#  Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                       #
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
import uuid
from aws_cdk import (
    aws_iam as iam,
    aws_s3 as s3,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_events_targets as targets,
    aws_events as events,
    aws_codepipeline as codepipeline,
    core,
)
from lib.blueprints.byom.pipeline_definitions.source_actions import source_action_custom
from lib.blueprints.byom.pipeline_definitions.build_actions import build_action
from lib.blueprints.byom.pipeline_definitions.deploy_actions import (
    create_model,
    create_endpoint,
    sagemaker_layer,
)
from lib.blueprints.byom.pipeline_definitions.share_actions import configure_inference
from lib.blueprints.byom.pipeline_definitions.helpers import (
    suppress_assets_bucket,
    pipeline_permissions,
    suppress_list_function_policy,
    suppress_pipeline_bucket,
    suppress_iam_complex,
    suppress_sns,
)


class BYOMRealtimeBuildStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Parameteres #
        notification_email = core.CfnParameter(
            self,
            "NOTIFICATION_EMAIL",
            type="String",
            description="email for pipeline outcome notifications",
            allowed_pattern="^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            constraint_description="Please enter an email address with correct format (example@exmaple.com)",
            min_length=5,
            max_length=320,
        )
        blueprint_bucket_name = core.CfnParameter(
            self,
            "BLUEPRINT_BUCKET",
            type="String",
            description="Bucket name for blueprints of different types of ML Pipelines.",
            min_length=3,
        )
        assets_bucket_name = core.CfnParameter(
            self, "ASSETS_BUCKET", type="String", description="Bucket name for access logs.", min_length=3
        )
        custom_container = core.CfnParameter(
            self,
            "CUSTOM_CONTAINER",
            default="",
            type="String",
            description=(
                "Should point to a zip file containing dockerfile and assets for building a custom model. "
                "If empty it will beusing containers from SageMaker Registry"
            ),
        )
        model_framework = core.CfnParameter(
            self,
            "MODEL_FRAMEWORK",
            default="",
            type="String",
            description="The ML framework which is used for training the model. E.g., xgboost, kmeans, etc.",
        )
        model_framework_version = core.CfnParameter(
            self,
            "MODEL_FRAMEWORK_VERSION",
            default="",
            type="String",
            description="The version of the ML framework which is used for training the model. E.g., 1.1-2",
        )
        model_name = core.CfnParameter(
            self, "MODEL_NAME", type="String", description="An arbitrary name for the model.", min_length=1
        )
        model_artifact_location = core.CfnParameter(
            self,
            "MODEL_ARTIFACT_LOCATION",
            type="String",
            description="Path to model artifact inside assets bucket.",
        )
        inference_instance = core.CfnParameter(
            self,
            "INFERENCE_INSTANCE",
            type="String",
            description="Inference instance that inference requests will be running on. E.g., ml.m5.large",
            allowed_pattern="^[a-zA-Z0-9_.+-]+\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            min_length=7,
        )
        # Resources #

        # access_bucket = s3.Bucket.from_bucket_name(self, "AccessBucket", access_bucket_name.value_as_string)
        assets_bucket = s3.Bucket.from_bucket_name(self, "AssetsBucket", assets_bucket_name.value_as_string)
        # getting blueprint bucket object from its name - will be used later in the stack
        blueprint_bucket = s3.Bucket.from_bucket_name(self, "BlueprintBucket", blueprint_bucket_name.value_as_string)

        # Defining pipeline stages
        # source stage
        source_output, source_action_definition = source_action_custom(
            model_artifact_location, assets_bucket, custom_container
        )

        # build stage
        build_action_definition, container_uri = build_action(self, source_output)

        # deploy stage
        sm_layer = sagemaker_layer(self, blueprint_bucket)
        # creating a sagemaker model
        model_lambda_arn, create_model_definition = create_model(
            self,
            blueprint_bucket,
            assets_bucket,
            model_name,
            model_artifact_location,
            custom_container,
            model_framework,
            model_framework_version,
            container_uri,
            sm_layer,
        )
        # creating a sagemaker endpoint
        endpoint_lambda_arn, create_endpoint_definition = create_endpoint(
            self, blueprint_bucket, assets_bucket, model_name, inference_instance
        )
        # Share stage
        configure_lambda_arn, configure_inference_definition = configure_inference(self, blueprint_bucket)

        # create invoking lambda policy
        invoke_lambdas_policy = iam.PolicyStatement(
            actions=[
                "lambda:InvokeFunction",
            ],
            resources=[model_lambda_arn, endpoint_lambda_arn, configure_lambda_arn],
        )

        pipeline_notification_topic = sns.Topic(
            self,
            "PipelineNotification",
        )
        pipeline_notification_topic.node.default_child.cfn_options.metadata = suppress_sns()
        pipeline_notification_topic.add_subscription(
            subscriptions.EmailSubscription(email_address=notification_email.value_as_string)
        )

        # createing pipeline stages
        source_stage = codepipeline.StageProps(stage_name="Source", actions=[source_action_definition])
        build_stage = codepipeline.StageProps(stage_name="Build", actions=[build_action_definition])
        deploy_stage_realtime = codepipeline.StageProps(
            stage_name="Deploy",
            actions=[
                create_model_definition,
                create_endpoint_definition,
            ],
        )
        share_stage = codepipeline.StageProps(stage_name="Share", actions=[configure_inference_definition])

        realtime_build_pipeline = codepipeline.Pipeline(
            self,
            "BYOMPipelineReatimeBuild",
            stages=[source_stage, build_stage, deploy_stage_realtime, share_stage],
            cross_account_keys=False,
        )
        realtime_build_pipeline.on_state_change(
            "NotifyUser",
            description="Notify user of the outcome of the pipeline",
            target=targets.SnsTopic(
                pipeline_notification_topic,
                message=events.RuleTargetInput.from_text(
                    (
                        f"Pipeline {events.EventField.from_path('$.detail.pipeline')} finished executing. "
                        f"Pipeline execution result is {events.EventField.from_path('$.detail.state')}"
                    )
                ),
            ),
            event_pattern=events.EventPattern(detail={"state": ["SUCCEEDED", "FAILED"]}),
        )
        realtime_build_pipeline.add_to_role_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                resources=[
                    f"arn:{core.Aws.PARTITION}:events:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:event-bus/*",
                ],
            )
        )
        # add lambda permissons
        realtime_build_pipeline.add_to_role_policy(invoke_lambdas_policy)
        # Enhancement: This is to find CDK object nodes so that unnecessary cfn-nag warnings can be suppressed
        # There is room for improving the method in future versions to find CDK nodes without having to use
        # hardocded index numbers
        pipeline_child_nodes = realtime_build_pipeline.node.find_all()
        pipeline_child_nodes[1].node.default_child.cfn_options.metadata = suppress_pipeline_bucket()
        pipeline_child_nodes[6].node.default_child.cfn_options.metadata = suppress_iam_complex()
        pipeline_child_nodes[13].node.default_child.cfn_options.metadata = suppress_iam_complex()
        pipeline_child_nodes[19].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        pipeline_child_nodes[25].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        pipeline_child_nodes[30].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        pipeline_child_nodes[36].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        # attaching iam permissions to the pipelines
        pipeline_permissions(realtime_build_pipeline, assets_bucket)

        # Outputs #
        core.CfnOutput(
            self,
            id="Pipelines",
            value=(
                f"https://console.aws.amazon.com/codesuite/codepipeline/pipelines/"
                f"{realtime_build_pipeline.pipeline_name}/view?region={core.Aws.REGION}"
            ),
        )
        core.CfnOutput(
            self,
            id="SageMakerModelName",
            value=model_name.value_as_string,
        )
        core.CfnOutput(
            self,
            id="SageMakerEndpointConfigName",
            value=f"{model_name.value_as_string}-endpoint-config",
        )
        core.CfnOutput(
            self,
            id="SageMakerEndpointName",
            value=f"{model_name.value_as_string}-endpoint",
        )
        core.CfnOutput(
            self,
            id="EndpointDataCaptureLocation",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{assets_bucket.bucket_name}/datacapture",
            description="Endpoint data capture location (to be used by Model Monitor)",
        )