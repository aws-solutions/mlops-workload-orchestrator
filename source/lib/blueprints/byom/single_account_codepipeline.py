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
from lib.blueprints.byom.pipeline_definitions.source_actions import source_action_template
from lib.blueprints.byom.pipeline_definitions.deploy_actions import create_cloudformation_action
from lib.blueprints.byom.pipeline_definitions.helpers import (
    pipeline_permissions,
    suppress_pipeline_bucket,
    suppress_iam_complex,
    suppress_sns,
    suppress_cloudformation_action,
)
from lib.blueprints.byom.pipeline_definitions.templates_parameters import ParameteresFactory as pf


class SingleAccountCodePipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Parameteres #
        notification_email = pf.create_notification_email_parameter(self)
        template_zip_name = pf.create_template_zip_name_parameter(self)
        template_file_name = pf.create_template_file_name_parameter(self)
        template_params_file_name = pf.create_stage_params_file_name_parameter(self, "TemplateParamsName", "main")
        assets_bucket_name = pf.create_assets_bucket_name_parameter(self)
        stack_name = pf.create_stack_name_parameter(self)

        # Resources #
        assets_bucket = s3.Bucket.from_bucket_name(self, "ImportedAssetsBucket", assets_bucket_name.value_as_string)

        # create sns topic and subscription
        pipeline_notification_topic = sns.Topic(
            self,
            "SinglePipelineNotification",
        )
        pipeline_notification_topic.node.default_child.cfn_options.metadata = suppress_sns()
        pipeline_notification_topic.add_subscription(
            subscriptions.EmailSubscription(email_address=notification_email.value_as_string)
        )

        # Defining pipeline stages
        # source stage
        source_output, source_action_definition = source_action_template(template_zip_name, assets_bucket)

        # create cloudformation action
        cloudformation_action = create_cloudformation_action(
            self,
            "deploy_stack",
            stack_name.value_as_string,
            source_output,
            template_file_name.value_as_string,
            template_params_file_name.value_as_string,
        )

        source_stage = codepipeline.StageProps(stage_name="Source", actions=[source_action_definition])
        deploy = codepipeline.StageProps(
            stage_name="DeployCloudFormation",
            actions=[cloudformation_action],
        )

        single_account_pipeline = codepipeline.Pipeline(
            self,
            "SingleAccountPipeline",
            stages=[source_stage, deploy],
            cross_account_keys=False,
        )

        # Add CF suppressions to the action
        deployment_policy = cloudformation_action.deployment_role.node.find_all()[2]
        deployment_policy.node.default_child.cfn_options.metadata = suppress_cloudformation_action()

        # add notification to the single-account pipeline
        single_account_pipeline.on_state_change(
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
        single_account_pipeline.add_to_role_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                resources=[
                    f"arn:{core.Aws.PARTITION}:events:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:event-bus/*",
                ],
            )
        )

        # add cfn suppressions
        pipeline_child_nodes = single_account_pipeline.node.find_all()
        pipeline_child_nodes[1].node.default_child.cfn_options.metadata = suppress_pipeline_bucket()
        pipeline_child_nodes[6].node.default_child.cfn_options.metadata = suppress_iam_complex()
        # attaching iam permissions to the pipelines
        pipeline_permissions(single_account_pipeline, assets_bucket)

        # Outputs #
        core.CfnOutput(
            self,
            id="Pipelines",
            value=(
                f"https://console.aws.amazon.com/codesuite/codepipeline/pipelines/"
                f"{single_account_pipeline.pipeline_name}/view?region={core.Aws.REGION}"
            ),
        )
