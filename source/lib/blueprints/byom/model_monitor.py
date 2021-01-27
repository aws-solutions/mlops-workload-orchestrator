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
from lib.blueprints.byom.pipeline_definitions.source_actions import source_action_model_monitor
from lib.blueprints.byom.pipeline_definitions.deploy_actions import (
    create_data_baseline_job,
    create_monitoring_schedule,
    sagemaker_layer,
)

from lib.blueprints.byom.pipeline_definitions.helpers import (
    suppress_assets_bucket,
    pipeline_permissions,
    suppress_list_function_policy,
    suppress_pipeline_bucket,
    suppress_iam_complex,
    suppress_sns,
)
from time import strftime, gmtime


class ModelMonitorStack(core.Stack):
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
        endpoint_name = core.CfnParameter(
            self, "ENDPOINT_NAME", type="String", description="The name of the ednpoint to monitor", min_length=1
        )
        baseline_job_output_location = core.CfnParameter(
            self,
            "BASELINE_JOB_OUTPUT_LOCATION",
            type="String",
            description="S3 prefix to store the Data Baseline Job's output.",
        )
        monitoring_output_location = core.CfnParameter(
            self,
            "MONITORING_OUTPUT_LOCATION",
            type="String",
            description="S3 prefix to store the Monitoring Schedule output.",
        )
        schedule_expression = core.CfnParameter(
            self,
            "SCHEDULE_EXPRESSION",
            type="String",
            description="cron expression to run the monitoring schedule. E.g., cron(0 * ? * * *), cron(0 0 ? * * *), etc.",
            allowed_pattern="^cron(\\S+\\s){5}\\S+$",
        )
        training_data = core.CfnParameter(
            self,
            "TRAINING_DATA",
            type="String",
            description="Location of the training data in PipelineAssets S3 Bucket.",
        )
        instance_type = core.CfnParameter(
            self,
            "INSTANCE_TYPE",
            type="String",
            description="Inference instance that inference requests will be running on. E.g., ml.m5.large",
            allowed_pattern="^[a-zA-Z0-9_.+-]+\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            min_length=7,
        )
        instance_volume_size = core.CfnParameter(
            self,
            "INSTANCE_VOLUME_SIZE",
            type="Number",
            description="Instance volume size used in model moniroing jobs. E.g., 20",
        )
        monitoring_type = core.CfnParameter(
            self,
            "MONITORING_TYPE",
            type="String",
            allowed_values=["dataquality", "modelquality", "modelbias", "modelexplainability"],
            default="dataquality",
            description="Type of model monitoring. Possible values: DataQuality | ModelQuality | ModelBias | ModelExplainability ",
        )
        max_runtime_seconds = core.CfnParameter(
            self,
            "MAX_RUNTIME_SIZE",
            type="Number",
            description="Max runtime in secodns the job is allowed to run. E.g., 3600",
        )
        baseline_job_name = core.CfnParameter(
            self,
            "BASELINE_JOB_NAME",
            type="String",
            description="Unique name of the data baseline job",
            min_length=3,
            max_length=63,
        )
        monitoring_schedule_name = core.CfnParameter(
            self,
            "MONITORING_SCHEDULE_NAME",
            type="String",
            description="Unique name of the monitoring schedule job",
            min_length=3,
            max_length=63,
        )
        # Resources #
        assets_bucket = s3.Bucket.from_bucket_name(self, "AssetsBucket", assets_bucket_name.value_as_string)
        # getting blueprint bucket object from its name - will be used later in the stack
        blueprint_bucket = s3.Bucket.from_bucket_name(self, "BlueprintBucket", blueprint_bucket_name.value_as_string)

        # Defining pipeline stages
        # source stage
        source_output, source_action_definition = source_action_model_monitor(training_data, assets_bucket)

        # deploy stage
        # creating data baseline job
        baseline_lambda_arn, create_baseline_job_definition = create_data_baseline_job(
            self,
            blueprint_bucket,
            assets_bucket,
            baseline_job_name,
            training_data,
            baseline_job_output_location,
            endpoint_name,
            instance_type,
            instance_volume_size,
            max_runtime_seconds,
            core.Aws.STACK_NAME,
        )
        # creating monitoring schedule
        monitor_lambda_arn, create_monitoring_schedule_definition = create_monitoring_schedule(
            self,
            blueprint_bucket,
            assets_bucket,
            baseline_job_output_location,
            baseline_job_name,
            monitoring_schedule_name,
            monitoring_output_location,
            schedule_expression,
            endpoint_name,
            instance_type,
            instance_volume_size,
            max_runtime_seconds,
            monitoring_type,
            core.Aws.STACK_NAME,
        )
        # create invoking lambda policy
        invoke_lambdas_policy = iam.PolicyStatement(
            actions=[
                "lambda:InvokeFunction",
            ],
            resources=[baseline_lambda_arn, monitor_lambda_arn],
        )
        # createing pipeline stages
        source_stage = codepipeline.StageProps(stage_name="Source", actions=[source_action_definition])
        deploy_stage_model_monitor = codepipeline.StageProps(
            stage_name="Deploy",
            actions=[
                create_baseline_job_definition,
                create_monitoring_schedule_definition,
            ],
        )

        pipeline_notification_topic = sns.Topic(
            self,
            "ModelMonitorPipelineNotification",
        )
        pipeline_notification_topic.node.default_child.cfn_options.metadata = suppress_sns()
        pipeline_notification_topic.add_subscription(
            subscriptions.EmailSubscription(email_address=notification_email.value_as_string)
        )

        # constructing Model Monitor pipelines
        model_monitor_pipeline = codepipeline.Pipeline(
            self,
            "ModelMonitorPipeline",
            stages=[source_stage, deploy_stage_model_monitor],
            cross_account_keys=False,
        )
        model_monitor_pipeline.on_state_change(
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
        model_monitor_pipeline.add_to_role_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                resources=[
                    f"arn:{core.Aws.PARTITION}:events:{core.Aws.REGION}:{core.Aws.ACCOUNT_ID}:event-bus/*",
                ],
            )
        )
        # add lambda permissons
        model_monitor_pipeline.add_to_role_policy(invoke_lambdas_policy)

        pipeline_child_nodes = model_monitor_pipeline.node.find_all()
        pipeline_child_nodes[1].node.default_child.cfn_options.metadata = suppress_pipeline_bucket()
        pipeline_child_nodes[6].node.default_child.cfn_options.metadata = suppress_iam_complex()
        pipeline_child_nodes[13].node.default_child.cfn_options.metadata = suppress_iam_complex()
        pipeline_child_nodes[19].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        pipeline_child_nodes[24].node.default_child.cfn_options.metadata = suppress_list_function_policy()
        # attaching iam permissions to the pipelines
        pipeline_permissions(model_monitor_pipeline, assets_bucket)

        # Outputs #
        core.CfnOutput(
            self,
            id="MonitorPipeline",
            value=(
                f"https://console.aws.amazon.com/codesuite/codepipeline/pipelines/"
                f"{model_monitor_pipeline.pipeline_name}/view?region={core.Aws.REGION}"
            ),
        )

        core.CfnOutput(
            self,
            id="DataBaselineJobName",
            value=baseline_job_name.value_as_string,
        )
        core.CfnOutput(
            self,
            id="MonitoringScheduleJobName",
            value=monitoring_schedule_name.value_as_string,
        )
        core.CfnOutput(
            self,
            id="MonitoringScheduleType",
            value=monitoring_type.value_as_string,
        )
