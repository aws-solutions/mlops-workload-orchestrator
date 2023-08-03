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
    CfnOutput,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sns as sns,
    aws_events_targets as targets,
    aws_events as events,
    aws_codepipeline as codepipeline,
)
from lib.blueprints.pipeline_definitions.source_actions import (
    source_action_template,
)
from lib.blueprints.pipeline_definitions.deploy_actions import (
    create_stackset_action,
)

from lib.blueprints.pipeline_definitions.approval_actions import approval_action
from lib.blueprints.pipeline_definitions.helpers import (
    pipeline_permissions,
    suppress_list_function_policy,
    suppress_pipeline_bucket,
    suppress_iam_complex,
)
from lib.blueprints.pipeline_definitions.templates_parameters import (
    ParameteresFactory as pf,
    ConditionsFactory as cf,
)


class MultiAccountCodePipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Parameteres #
        template_zip_name = pf.create_template_zip_name_parameter(self)
        template_file_name = pf.create_template_file_name_parameter(self)
        dev_params_file_name = pf.create_stage_params_file_name_parameter(
            self, "DevParamsName", "development"
        )
        staging_params_file_name = pf.create_stage_params_file_name_parameter(
            self, "StagingParamsName", "staging"
        )
        prod_params_file_name = pf.create_stage_params_file_name_parameter(
            self, "ProdParamsName", "production"
        )
        mlops_sns_topic_arn = pf.create_sns_topic_arn_parameter(self)

        # create development parameters
        account_type = "development"
        dev_account_id = pf.create_account_id_parameter(
            self, "DevAccountId", account_type
        )
        dev_org_id = pf.create_org_id_parameter(self, "DevOrgId", account_type)
        # create staging parameters
        account_type = "staging"
        staging_account_id = pf.create_account_id_parameter(
            self, "StagingAccountId", account_type
        )
        staging_org_id = pf.create_org_id_parameter(self, "StagingOrgId", account_type)
        # create production parameters
        account_type = "production"
        prod_account_id = pf.create_account_id_parameter(
            self, "ProdAccountId", account_type
        )
        prod_org_id = pf.create_org_id_parameter(self, "ProdOrgId", account_type)
        # assets parameters
        blueprint_bucket_name = pf.create_blueprint_bucket_name_parameter(self)
        assets_bucket_name = pf.create_assets_bucket_name_parameter(self)
        stack_name = pf.create_stack_name_parameter(self)
        # delegated admin account
        is_delegated_admin = pf.create_delegated_admin_parameter(self)
        # create use delegated admin account condition
        delegated_admin_account_condition = cf.create_delegated_admin_condition(
            self, is_delegated_admin
        )

        # Resources #
        assets_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedAssetsBucket", assets_bucket_name.value_as_string
        )

        # getting blueprint bucket object from its name - will be used later in the stack
        blueprint_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedBlueprintBucket", blueprint_bucket_name.value_as_string
        )

        # import the sns Topic
        pipeline_notification_topic = sns.Topic.from_topic_arn(
            self, "PipelineNotification", mlops_sns_topic_arn.value_as_string
        )

        # Defining pipeline stages
        # source stage
        source_output, source_action_definition = source_action_template(
            template_zip_name, assets_bucket
        )

        # use the first 8 characters from last portion of the stack_id as a unique id to be appended
        # to stacksets names. Example stack_id:
        # arn:aws:cloudformation:<region>:<account-id>:stack/<stack-name>/e45f0f20-c886-11eb-98d4-0a1157964cc9
        # the selected id would be e45f0f20
        unique_id = Fn.select(
            0,
            Fn.split("-", Fn.select(2, Fn.split("/", Aws.STACK_ID))),
        )

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
            [Aws.REGION],
            f"{stack_name.value_as_string}-dev-{unique_id}",
            delegated_admin_account_condition,
        )

        # DeployStaging manual approval
        deploy_staging_approval = approval_action(
            "DeployStaging",
            pipeline_notification_topic,
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
            [Aws.REGION],
            f"{stack_name.value_as_string}-staging-{unique_id}",
            delegated_admin_account_condition,
        )

        # DeployProd manual approval
        deploy_prod_approval = approval_action(
            "DeployProd",
            pipeline_notification_topic,
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
            [Aws.REGION],
            f"{stack_name.value_as_string}-prod-{unique_id}",
            delegated_admin_account_condition,
        )

        # create invoking lambda policy
        invoke_lambdas_policy = iam.PolicyStatement(
            actions=[
                "lambda:InvokeFunction",
            ],
            resources=[
                dev_deploy_lambda_arn,
                staging_deploy_lambda_arn,
                prod_deploy_lambda_arn,
            ],
        )

        # createing pipeline stages
        source_stage = codepipeline.StageProps(
            stage_name="Source", actions=[source_action_definition]
        )

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
            stages=[
                source_stage,
                deploy_dev_stage,
                deploy_staging_stage,
                deploy_prod_stage,
            ],
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
            event_pattern=events.EventPattern(
                detail={"state": ["SUCCEEDED", "FAILED"]}
            ),
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
            event_pattern=events.EventPattern(
                detail={"state": ["SUCCEEDED", "FAILED"]}
            ),
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
            event_pattern=events.EventPattern(
                detail={"state": ["SUCCEEDED", "FAILED"]}
            ),
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
            event_pattern=events.EventPattern(
                detail={"state": ["SUCCEEDED", "FAILED"]}
            ),
        )
        multi_account_pipeline.add_to_role_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                resources=[
                    f"arn:{Aws.PARTITION}:events:{Aws.REGION}:{Aws.ACCOUNT_ID}:event-bus/*",
                ],
            )
        )

        # add lambda permissions
        multi_account_pipeline.add_to_role_policy(invoke_lambdas_policy)

        # add cfn suppressions for Lambda:ListFunctions * resource
        multi_account_pipeline.node.find_child("DeployDev").node.find_child(
            "DeployDevStackSet"
        ).node.find_child("CodePipelineActionRole").node.find_child(
            "DefaultPolicy"
        ).node.default_child.cfn_options.metadata = suppress_list_function_policy()
        multi_account_pipeline.node.find_child("DeployStaging").node.find_child(
            "DeployStagingStackSet"
        ).node.find_child("CodePipelineActionRole").node.find_child(
            "DefaultPolicy"
        ).node.default_child.cfn_options.metadata = suppress_list_function_policy()

        multi_account_pipeline.node.find_child("DeployProd").node.find_child(
            "DeployProdStackSet"
        ).node.find_child("CodePipelineActionRole").node.find_child(
            "DefaultPolicy"
        ).node.default_child.cfn_options.metadata = suppress_list_function_policy()

        # add suppression for complex policy
        multi_account_pipeline.node.find_child("Role").node.find_child(
            "DefaultPolicy"
        ).node.default_child.cfn_options.metadata = suppress_iam_complex()

        # add ArtifactBucket cfn suppression (not needing a logging bucket)
        multi_account_pipeline.node.find_child(
            "ArtifactsBucket"
        ).node.default_child.cfn_options.metadata = suppress_pipeline_bucket()
        # attaching iam permissions to the pipelines
        pipeline_permissions(multi_account_pipeline, assets_bucket)

        # Outputs #
        CfnOutput(
            self,
            id="Pipelines",
            value=(
                f"https://console.aws.amazon.com/codesuite/codepipeline/pipelines/"
                f"{multi_account_pipeline.pipeline_name}/view?region={Aws.REGION}"
            ),
        )
