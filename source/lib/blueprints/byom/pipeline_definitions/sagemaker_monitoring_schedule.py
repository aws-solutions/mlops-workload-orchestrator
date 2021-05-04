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
from aws_cdk import aws_sagemaker as sagemaker, core


def create_sagemaker_monitoring_scheduale(
    scope,  # NOSONAR:S107 this function is designed to take many arguments
    id,
    monitoring_schedule_name,
    endpoint_name,
    baseline_job_name,
    baseline_job_output_location,
    schedule_expression,
    monitoring_output_location,
    instance_type,
    instance_volume_size,
    max_runtime_seconds,
    kms_key_arn,
    role_arn,
    image_uri,
    stack_name,
):
    """
    create_sagemaker_monitoring_scheduale creates a monitoring schedule using CDK

    :scope: CDK Construct scope that's needed to create CDK resources
    :monitoring_schedual_name: name of the monitoring job to be created
    :endpoint_name: name of the deployed SageMaker endpoint to be monitored
    :baseline_job_name: name of the baseline job
    :baseline_job_output_location: S3 prefix in the S3 assets bucket to store the output of the job
    :schedule_expression: cron job expression
    :monitoring_output_location: S3 location where the output will be stored
    :instance_type: compute instance type for the baseline job, in the form of a CDK CfnParameter object
    :instance_volume_size: volume size of the EC2 instance
    :max_runtime_seconds: max time the job is allowd to run
    :kms_key_arn": optional arn of the kms key used to encrypt datacapture and to encrypt job's output
    :role_arn: Sagemaker role's arn to be used to create the monitoring schedule
    :image_uri: the name of the stack where the schedule will be created
    :return: return an sagemaker.CfnMonitoringSchedule object

    """
    schedule = sagemaker.CfnMonitoringSchedule(
        scope,
        id,
        monitoring_schedule_name=monitoring_schedule_name,
        monitoring_schedule_config=sagemaker.CfnMonitoringSchedule.MonitoringScheduleConfigProperty(
            schedule_config=sagemaker.CfnMonitoringSchedule.ScheduleConfigProperty(
                schedule_expression=schedule_expression
            ),
            monitoring_job_definition=sagemaker.CfnMonitoringSchedule.MonitoringJobDefinitionProperty(
                baseline_config=sagemaker.CfnMonitoringSchedule.BaselineConfigProperty(
                    constraints_resource=sagemaker.CfnMonitoringSchedule.ConstraintsResourceProperty(
                        s3_uri=f"s3://{baseline_job_output_location}/{baseline_job_name}/constraints.json"
                    ),
                    statistics_resource=sagemaker.CfnMonitoringSchedule.StatisticsResourceProperty(
                        s3_uri=f"s3://{baseline_job_output_location}/{baseline_job_name}/statistics.json"
                    ),
                ),
                monitoring_inputs=sagemaker.CfnMonitoringSchedule.MonitoringInputsProperty(
                    monitoring_inputs=[
                        sagemaker.CfnMonitoringSchedule.MonitoringInputProperty(
                            endpoint_input=sagemaker.CfnMonitoringSchedule.EndpointInputProperty(
                                endpoint_name=endpoint_name,
                                local_path="/opt/ml/processing/input/monitoring_dataset_input",
                                s3_input_mode="File",
                                s3_data_distribution_type="FullyReplicated",
                            )
                        )
                    ]
                ),
                monitoring_output_config=sagemaker.CfnMonitoringSchedule.MonitoringOutputConfigProperty(
                    monitoring_outputs=[
                        sagemaker.CfnMonitoringSchedule.MonitoringOutputProperty(
                            s3_output=sagemaker.CfnMonitoringSchedule.S3OutputProperty(
                                s3_uri=f"s3://{monitoring_output_location}",
                                local_path="/opt/ml/processing/output",
                                s3_upload_mode="EndOfJob",
                            )
                        )
                    ],
                    kms_key_id=kms_key_arn,
                ),
                monitoring_resources=sagemaker.CfnMonitoringSchedule.MonitoringResourcesProperty(
                    cluster_config=sagemaker.CfnMonitoringSchedule.ClusterConfigProperty(
                        instance_count=1.0,
                        instance_type=instance_type,
                        volume_size_in_gb=core.Token.as_number(instance_volume_size),
                        volume_kms_key_id=kms_key_arn,
                    )
                ),
                monitoring_app_specification=sagemaker.CfnMonitoringSchedule.MonitoringAppSpecificationProperty(
                    image_uri=image_uri
                ),
                stopping_condition=sagemaker.CfnMonitoringSchedule.StoppingConditionProperty(
                    max_runtime_in_seconds=core.Token.as_number(max_runtime_seconds)
                ),
                role_arn=role_arn,
            ),
        ),
        tags=[
            {"key": "stack_name", "value": stack_name},
        ],
    )

    # This is a workaround the current bug in CDK aws-sagemaker, where the MonitoringInputs property
    # is duplicated. link to the bug https://github.com/aws/aws-cdk/issues/12208
    schedule.add_property_override(
        "MonitoringScheduleConfig.MonitoringJobDefinition.MonitoringInputs",
        [
            {
                "EndpointInput": {
                    "EndpointName": {"Ref": "ENDPOINTNAME"},
                    "LocalPath": "/opt/ml/processing/input/monitoring_dataset_input",
                    "S3DataDistributionType": "FullyReplicated",
                    "S3InputMode": "File",
                }
            }
        ],
    )

    return schedule
