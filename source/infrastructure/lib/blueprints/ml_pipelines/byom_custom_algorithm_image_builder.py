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
    CfnOutput,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sns as sns,
    aws_events_targets as targets,
    aws_events as events,
    aws_codepipeline as codepipeline,
)
from lib.blueprints.pipeline_definitions.source_actions import source_action_custom
from lib.blueprints.pipeline_definitions.build_actions import build_action
from lib.blueprints.pipeline_definitions.helpers import (
    pipeline_permissions,
    suppress_pipeline_bucket,
    suppress_iam_complex,
)
from lib.blueprints.pipeline_definitions.templates_parameters import (
    ParameteresFactory as pf,
)


class BYOMCustomAlgorithmImageBuilderStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Parameteres #
        assets_bucket_name = pf.create_assets_bucket_name_parameter(self)
        custom_container = pf.create_custom_container_parameter(self)
        ecr_repo_name = pf.create_ecr_repo_name_parameter(self)
        image_tag = pf.create_image_tag_parameter(self)
        mlops_sns_topic_arn = pf.create_sns_topic_arn_parameter(self)

        # Resources #
        assets_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedAssetsBucket", assets_bucket_name.value_as_string
        )

        # Defining pipeline stages
        # source stage
        source_output, source_action_definition = source_action_custom(
            assets_bucket, custom_container
        )

        # build stage
        build_action_definition, container_uri = build_action(
            self,
            ecr_repo_name.value_as_string,
            image_tag.value_as_string,
            source_output,
        )

        # import the sns Topic
        pipeline_notification_topic = sns.Topic.from_topic_arn(
            self,
            "ImageBuilderPipelineNotification",
            mlops_sns_topic_arn.value_as_string,
        )

        # createing pipeline stages
        source_stage = codepipeline.StageProps(
            stage_name="Source", actions=[source_action_definition]
        )
        build_stage = codepipeline.StageProps(
            stage_name="Build", actions=[build_action_definition]
        )

        image_builder_pipeline = codepipeline.Pipeline(
            self,
            "BYOMPipelineRealtimeBuild",
            stages=[source_stage, build_stage],
            cross_account_keys=False,
        )
        image_builder_pipeline.on_state_change(
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
            event_pattern=events.EventPattern(
                detail={"state": ["SUCCEEDED", "FAILED"]}
            ),
        )

        image_builder_pipeline.add_to_role_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                resources=[
                    f"arn:{Aws.PARTITION}:events:{Aws.REGION}:{Aws.ACCOUNT_ID}:event-bus/*",
                ],
            )
        )

        # add ArtifactBucket cfn supression (not needing a logging bucket)
        image_builder_pipeline.node.find_child(
            "ArtifactsBucket"
        ).node.default_child.cfn_options.metadata = suppress_pipeline_bucket()

        # add supression for complex policy
        image_builder_pipeline.node.find_child("Role").node.find_child(
            "DefaultPolicy"
        ).node.default_child.cfn_options.metadata = suppress_iam_complex()

        # attaching iam permissions to the pipelines
        pipeline_permissions(image_builder_pipeline, assets_bucket)

        # Outputs #
        CfnOutput(
            self,
            id="Pipelines",
            value=(
                f"https://console.aws.amazon.com/codesuite/codepipeline/pipelines/"
                f"{image_builder_pipeline.pipeline_name}/view?region={Aws.REGION}"
            ),
        )
        CfnOutput(
            self,
            id="CustomAlgorithmImageURI",
            value=container_uri,
        )
