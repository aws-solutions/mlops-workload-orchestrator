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
    aws_codepipeline as codepipeline,
    aws_events_targets as targets,
    aws_events as events,
    core,
)
from lib.blueprints.byom.pipeline_definitions.source_actions import source_action_custom
from lib.blueprints.byom.pipeline_definitions.build_actions import build_action
from lib.blueprints.byom.pipeline_definitions.deploy_actions import (
    create_model,
    batch_transform,
    sagemaker_layer,
)
from lib.blueprints.byom.pipeline_definitions.helpers import (
    suppress_assets_bucket,
    pipeline_permissions,
    suppress_iam_complex,
    suppress_pipeline_bucket,
    suppress_list_function_policy,
    suppress_sns,
)


class BYOMBatchBuildStack(core.Stack):
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
        inference_type = core.CfnParameter(
            self,
            "INFERENCE_TYPE",
            type="String",
            allowed_values=["batch", "realtime"],
            default="realtime",
            description="Type of inference. Possible values: batch | realtime",
        )
        batch_inference_data = core.CfnParameter(
            self,
            "BATCH_INFERENCE_DATA",
            type="String",
            default="",
            description=(
                "Location of batch inference data if inference type is set to batch. Otherwise, can be left empty."
            ),
        )

        # Resources #
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
        # creating a batch transform job
        batch_lambda_arn, batch_transform_definition = batch_transform(
            self,
            blueprint_bucket,
            assets_bucket,
            model_name,
            inference_instance,
            batch_inference_data,
            sm_layer,
        )

        # create invoking lambda policy
        invoke_lambdas_policy = iam.PolicyStatement(
            actions=[
                "lambda:InvokeFunction",
            ],
            resources=[model_lambda_arn, batch_lambda_arn],
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
        deploy_stage_batch = codepipeline.StageProps(
            stage_name="Deploy",
            actions=[create_model_definition, batch_transform_definition],
        )
        batch_build_pipeline = codepipeline.Pipeline(
            self,
            "BYOMPipelineBatchBuild",
            stages=[source_stage, build_stage, deploy_stage_batch],
            cross_account_keys=False,
        )
        batch_build_pipeline.on_state_change(
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
        batch_build_pipeline.add_to_role_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                resources=[
                    f"arn:{core.Aws.PARTITION}:events:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:event-bus/*",
                ],
            )
        )
        # add lambda permissons
        batch_build_pipeline.add_to_role_policy(invoke_lambdas_policy)

        # Enhancement: This is to find CDK object nodes so that unnecessary cfn-nag warnings can be suppressed
        # There is room for improving the method in future versions to find CDK nodes without having to use
        # hardocded index numbers
        pipeline_child_nodes = batch_build_pipeline.node.find_all()
        pipeline_child_nodes[1].node.default_child.cfn_options.metadata = suppress_pipeline_bucket()
        pipeline_child_nodes[6].node.default_child.cfn_options.metadata = suppress_iam_complex()
        pipeline_child_nodes[13].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        pipeline_child_nodes[19].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        pipeline_child_nodes[25].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        pipeline_child_nodes[30].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        # attaching iam permissions to the pipelines
        pipeline_permissions(batch_build_pipeline, assets_bucket)

        core.CfnOutput(
            self,
            id="Pipelines",
            value=(
                f"https://console.aws.amazon.com/codesuite/codepipeline/pipelines/"
                f"{batch_build_pipeline.pipeline_name}/view?region={core.Aws.REGION}"
            ),
        )
        core.CfnOutput(
            self,
            id="BatchTransformOutputLocation",
            value=f"https://s3.console.aws.amazon.com/s3/buckets/{assets_bucket.bucket_name}/batch_transform/output",
            description="Output location of the batch transform. Output will be saved under the job name",
        )
