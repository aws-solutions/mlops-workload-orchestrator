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
    aws_codepipeline_actions as codepipeline_actions,
)


def approval_action(approval_name, sns_topic, description):
    """
    approval_action configures a codepipeline manual approval

    :approval_name: name of the manual approval action
    :sns_topic: sns topic to use for notifications
    :description: description of the manual approval action
    :return: codepipeline action in a form of a CDK object that can be attached to a codepipeline stage
    """
    return codepipeline_actions.ManualApprovalAction(
        action_name=approval_name,
        notification_topic=sns_topic,
        additional_information=description,
        run_order=2,
    )
