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
from lib.blueprints.byom.pipeline_definitions.deploy_actions import create_stackset_action, create_cloudformation_action
from lib.blueprints.byom.pipeline_definitions.approval_actions import approval_action
from lib.blueprints.byom.pipeline_definitions.helpers import (
    pipeline_permissions,
    suppress_list_function_policy,
    suppress_pipeline_bucket,
    suppress_iam_complex,
    suppress_sns,
    suppress_cloudformation_action,
)
from lib.blueprints.byom.pipeline_definitions.templates_parameters import (
    create_notification_email_parameter,
    create_template_zip_name_parameter,
    create_template_file_name_parameter,
    create_stage_params_file_name_parameter,
    create_blueprint_bucket_name_parameter,
    create_assets_bucket_name_parameter,
    create_stack_name_parameter,
    create_account_id_parameter,
    create_org_id_parameter,
)


class MultiAccountCodePipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Parameteres #
        notification_email = create_notification_email_parameter(self)
        template_zip_name = create_template_zip_name_parameter(self)
        template_file_name = create_template_file_name_parameter(self)
        dev_params_file_name = create_stage_params_file_name_parameter(self, "DEV_PARAMS_NAME", "development")
        staging_params_file_name = create_stage_params_file_name_parameter(self, "STAGING_PARAMS_NAME", "staging")
        prod_params_file_name = create_stage_params_file_name_parameter(self, "PROD_PARAMS_NAME", "production")
        # create development parameters
        account_type = "development"
        dev_account_id = create_account_id_parameter(self, "DEV_ACCOUNT_ID", account_type)
        dev_org_id = create_org_id_parameter(self, "DEV_ORG_ID", account_type)
        # create staging parameters
        account_type = "staging"
        staging_account_id = create_account_id_parameter(self, "STAGING_ACCOUNT_ID", account_type)
        staging_org_id = create_org_id_parameter(self, "STAGING_ORG_ID", account_type)
        # create production parameters
        account_type = "production"
        prod_account_id = create_account_id_parameter(self, "PROD_ACCOUNT_ID", account_type)
        prod_org_id = create_org_id_parameter(self, "PROD_ORG_ID", account_type)
        # assets parameters
        blueprint_bucket_name = create_blueprint_bucket_name_parameter(self)
        assets_bucket_name = create_assets_bucket_name_parameter(self)
        stack_name = create_stack_name_parameter(self)

        # Resources #
        assets_bucket = s3.Bucket.from_bucket_name(self, "AssetsBucket", assets_bucket_name.value_as_string)

        # getting blueprint bucket object from its name - will be used later in the stack
        blueprint_bucket = s3.Bucket.from_bucket_name(self, "BlueprintBucket", blueprint_bucket_name.value_as_string)

        # create sns topic and subscription
        pipeline_notification_topic = sns.Topic(
            self,
            "PipelineNotification",
        )
        pipeline_notification_topic.node.default_child.cfn_options.metadata = suppress_sns()
        pipeline_notification_topic.add_subscription(
            subscriptions.EmailSubscription(email_address=notification_email.value_as_string)
        )

        # Defining pipeline stages
        # source stage
        source_output, source_action_definition = source_action_template(template_zip_name, assets_bucket)

        # DeployDev stage
        dev_deploy_lambda_arn, dev_stackset_action = create_stackset_action(
            self,
            "DeployDevStackSet",
            blueprint_bucket,
            source_output,
            "Artifact_Source_S3Source",
            template_file_name.value_as_string,
            dev_params_file_name.value_as_string,
            [dev_account_id.value_as_string],
            [dev_org_id.value_as_string],
            [core.Aws.REGION],
            assets_bucket,
            f"{stack_name.value_as_string}-dev",
        )

        # DeployStaging manual approval
        deploy_staging_approval = approval_action(
            "DeployStaging",
            pipeline_notification_topic,
            [notification_email.value_as_string],
            "Please approve to deploy to staging account",
        )

        # DeployStaging stage
        staging_deploy_lambda_arn, staging_stackset_action = create_stackset_action(
            self,
            "DeployStagingStackSet",
            blueprint_bucket,
            source_output,
            "Artifact_Source_S3Source",
            template_file_name.value_as_string,
            staging_params_file_name.value_as_string,
            [staging_account_id.value_as_string],
            [staging_org_id.value_as_string],
            [core.Aws.REGION],
            assets_bucket,
            f"{stack_name.value_as_string}-staging",
        )

        # DeployProd manual approval
        deploy_prod_approval = approval_action(
            "DeployProd",
            pipeline_notification_topic,
            [notification_email.value_as_string],
            "Please approve to deploy to production account",
        )

        # DeployProd stage
        prod_deploy_lambda_arn, prod_stackset_action = create_stackset_action(
            self,
            "DeployProdStackSet",
            blueprint_bucket,
            source_output,
            "Artifact_Source_S3Source",
            template_file_name.value_as_string,
            prod_params_file_name.value_as_string,
            [prod_account_id.value_as_string],
            [prod_org_id.value_as_string],
            [core.Aws.REGION],
            assets_bucket,
            f"{stack_name.value_as_string}-prod",
        )

        # create invoking lambda policy
        invoke_lambdas_policy = iam.PolicyStatement(
            actions=[
                "lambda:InvokeFunction",
            ],
            resources=[dev_deploy_lambda_arn, staging_deploy_lambda_arn, prod_deploy_lambda_arn],
        )

        # createing pipeline stages
        source_stage = codepipeline.StageProps(stage_name="Source", actions=[source_action_definition])

        deploy_dev_stage = codepipeline.StageProps(
            stage_name="DeployDev",
            actions=[dev_stackset_action, deploy_staging_approval],
        )

        deploy_staging_stage = codepipeline.StageProps(
            stage_name="DeployStaging",
            actions=[staging_stackset_action, deploy_prod_approval],
        )

        deploy_prod_stage = codepipeline.StageProps(
            stage_name="DeployProd",
            actions=[prod_stackset_action],
        )

        # constructing multi-account pipeline
        multi_account_pipeline = codepipeline.Pipeline(
            self,
            "MultiAccountPipeline",
            stages=[source_stage, deploy_dev_stage, deploy_staging_stage, deploy_prod_stage],
            cross_account_keys=False,
        )
        # add notification to the development stackset action
        dev_stackset_action.on_state_change(
            "NotifyUserDevDeployment",
            description="Notify user of the outcome of the DeployDev action",
            target=targets.SnsTopic(
                pipeline_notification_topic,
                message=events.RuleTargetInput.from_text(
                    (
                        f"DeployDev action {events.EventField.from_path('$.detail.action')} in the Pipeline "
                        f"{events.EventField.from_path('$.detail.pipeline')} finished executing. "
                        f"Action execution result is {events.EventField.from_path('$.detail.state')}"
                    )
                ),
            ),
            event_pattern=events.EventPattern(detail={"state": ["SUCCEEDED", "FAILED"]}),
        )

        # add notification to the staging stackset action
        staging_stackset_action.on_state_change(
            "NotifyUserStagingDeployment",
            description="Notify user of the outcome of the DeployStaging action",
            target=targets.SnsTopic(
                pipeline_notification_topic,
                message=events.RuleTargetInput.from_text(
                    (
                        f"DeployStaging action {events.EventField.from_path('$.detail.action')} in the Pipeline "
                        f"{events.EventField.from_path('$.detail.pipeline')} finished executing. "
                        f"Action execution result is {events.EventField.from_path('$.detail.state')}"
                    )
                ),
            ),
            event_pattern=events.EventPattern(detail={"state": ["SUCCEEDED", "FAILED"]}),
        )

        # add notification to the production stackset action
        prod_stackset_action.on_state_change(
            "NotifyUserProdDeployment",
            description="Notify user of the outcome of the DeployProd action",
            target=targets.SnsTopic(
                pipeline_notification_topic,
                message=events.RuleTargetInput.from_text(
                    (
                        f"DeployProd action {events.EventField.from_path('$.detail.action')} in the Pipeline "
                        f"{events.EventField.from_path('$.detail.pipeline')} finished executing. "
                        f"Action execution result is {events.EventField.from_path('$.detail.state')}"
                    )
                ),
            ),
            event_pattern=events.EventPattern(detail={"state": ["SUCCEEDED", "FAILED"]}),
        )

        # add notification to the multi-account pipeline
        multi_account_pipeline.on_state_change(
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
        multi_account_pipeline.add_to_role_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                resources=[
                    f"arn:{core.Aws.PARTITION}:events:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:event-bus/*",
                ],
            )
        )

        # add lambda permissons
        multi_account_pipeline.add_to_role_policy(invoke_lambdas_policy)

        # add cfn supressions

        pipeline_child_nodes = multi_account_pipeline.node.find_all()
        pipeline_child_nodes[1].node.default_child.cfn_options.metadata = suppress_pipeline_bucket()
        pipeline_child_nodes[6].node.default_child.cfn_options.metadata = suppress_iam_complex()
        pipeline_child_nodes[19].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        pipeline_child_nodes[32].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        pipeline_child_nodes[45].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        # attaching iam permissions to the pipelines
        pipeline_permissions(multi_account_pipeline, assets_bucket)

        # Outputs #
        core.CfnOutput(
            self,
            id="Pipelines",
            value=(
                f"https://console.aws.amazon.com/codesuite/codepipeline/pipelines/"
                f"{multi_account_pipeline.pipeline_name}/view?region={core.Aws.REGION}"
            ),
        )
