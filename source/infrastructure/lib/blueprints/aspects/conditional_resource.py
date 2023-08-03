# #####################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                            #
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
import jsii
from aws_cdk import CfnCondition, CfnResource, IAspect
from constructs import IConstruct

# This code enables `apply_aspect()` to apply conditions to a resource.
# This way we can provision some resources if a condition is true.
# For example, if PROVISIONTYPE parameter is 'Git' then we provision CodePipeline
# with it's source stage being CodeCommit or GitHub
# https://docs.aws.amazon.com/cdk/latest/guide/aspects.html


@jsii.implements(IAspect)
class ConditionalResources:
    def __init__(self, condition: CfnCondition):
        self.condition = condition

    def visit(self, node: IConstruct):
        child = node.node.default_child  # type: CfnResource
        if child:
            child.cfn_options.condition = self.condition
