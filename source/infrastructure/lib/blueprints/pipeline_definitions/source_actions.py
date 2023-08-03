# #####################################################################################################################
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
)


def source_action_custom(assets_bucket, custom_container):
    """
    source_action configures a codepipeline action with S3 as source

    :model_artifact_location: path to the model artifact in the S3 bucket: assets_bucket
    :assets_bucket: the bucket cdk object where pipeline assets are stored
    :custom_container: point to a zip file containing dockerfile and assets for building a custom model
    :return: codepipeline action in a form of a CDK object that can be attached to a codepipeline stage
    """
    source_output = codepipeline.Artifact()
    return source_output, codepipeline_actions.S3SourceAction(
        action_name="S3Source",
        bucket=assets_bucket,
        bucket_key=custom_container.value_as_string,
        output=source_output,
    )


def source_action_template(template_location, assets_bucket):
    """
    source_action_model_monitor configures a codepipeline action with S3 as source

    :template_location: path to the zip file containg the CF template and stages configuration in the S3 bucket: assets_bucket
    :assets_bucket: the bucket cdk object where pipeline assets are stored
    :return: codepipeline action in a form of a CDK object that can be attached to a codepipeline stage
    """
    source_output = codepipeline.Artifact()
    return source_output, codepipeline_actions.S3SourceAction(
        action_name="S3Source",
        bucket=assets_bucket,
        bucket_key=template_location.value_as_string,
        output=source_output,
    )
