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
    Aws,
    aws_iam as iam,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
)
from lib.blueprints.pipeline_definitions.helpers import suppress_pipeline_policy


def build_action(scope, ecr_repository_name, image_tag, source_output):
    """
    build_action configures a codepipeline action with repository name and tag

    :scope: CDK Construct scope that's needed to create CDK resources
    :ecr_repository_name: name of Amazon ECR repository where the image will be stored
    :image_tag: docker image tag to be assigned.
    :return: codepipeline action in a form of a CDK object that can be attached to a codepipeline stage
    """

    codebuild_role = iam.Role(
        scope,
        "codebuildRole",
        assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
    )

    codebuild_policy = iam.PolicyStatement(
        actions=[
            "ecr:BatchCheckLayerAvailability",
            "ecr:CompleteLayerUpload",
            "ecr:InitiateLayerUpload",
            "ecr:PutImage",
            "ecr:UploadLayerPart",
        ],
        resources=[
            f"arn:{Aws.PARTITION}:ecr:{Aws.REGION}:{Aws.ACCOUNT_ID}:repository/{ecr_repository_name}",
        ],
    )
    codebuild_role.add_to_policy(codebuild_policy)
    codebuild_role.add_to_policy(
        iam.PolicyStatement(actions=["ecr:GetAuthorizationToken"], resources=["*"])
    )
    # add suppression
    codebuild_role.node.find_child(
        "DefaultPolicy"
    ).node.default_child.cfn_options.metadata = suppress_pipeline_policy()
    # codebuild setup for build stage
    container_factory_project = codebuild.PipelineProject(
        scope,
        "Container_Factory",
        build_spec=codebuild.BuildSpec.from_object(
            {
                "version": "0.2",
                "phases": {
                    "pre_build": {
                        "commands": [
                            "echo Logging in to Amazon ECR...",
                            (
                                "aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS "
                                "--password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"
                            ),
                            'find . -iname "serve" -exec chmod 777 "{}" \\;',
                            'find . -iname "train" -exec chmod 777 "{}" \\;',
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo Build started on `date`",
                            "echo Building the Docker image...",
                            "docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .",
                            (
                                "docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr."
                                "$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG"
                            ),
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "echo Build completed on `date`",
                            "echo Pushing the Docker image...",
                            (
                                "docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/"
                                "$IMAGE_REPO_NAME:$IMAGE_TAG"
                            ),
                        ]
                    },
                },
            }
        ),
        environment=codebuild.BuildEnvironment(
            build_image=codebuild.LinuxBuildImage.STANDARD_6_0,
            compute_type=codebuild.ComputeType.SMALL,
            environment_variables={
                "AWS_DEFAULT_REGION": {"value": Aws.REGION},
                "AWS_ACCOUNT_ID": {"value": Aws.ACCOUNT_ID},
                "IMAGE_REPO_NAME": {"value": ecr_repository_name},
                "IMAGE_TAG": {"value": image_tag},
            },
            privileged=True,
        ),
        role=codebuild_role,
    )
    build_action_definition = codepipeline_actions.CodeBuildAction(
        action_name="CodeBuild",
        project=container_factory_project,
        input=source_output,
        outputs=[codepipeline.Artifact()],
    )
    container_uri = f"{Aws.ACCOUNT_ID}.dkr.ecr.{Aws.REGION}.amazonaws.com/{ecr_repository_name}:{image_tag}"
    return build_action_definition, container_uri
