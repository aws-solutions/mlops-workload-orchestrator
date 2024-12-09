# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import List

import jsii
from aws_cdk import CfnResource, IAspect
from constructs import IConstruct



def add_cfn_guard_suppressions(
    resource: CfnResource, suppressions: List[str]
):
    if resource.node.default_child:
        resource.node.default_child.add_metadata(
            "guard",
            {
                "SuppressedRules": suppressions
            },
        )
    else:
        resource.add_metadata(
            "guard",
            {
                "SuppressedRules": suppressions
            },
        )

@jsii.implements(IAspect)
class CfnGuardSuppressResourceList:
    """Suppress certain cfn_guard warnings that can be ignored by this solution"""

    def __init__(self, resource_suppressions: dict):
        self.resource_suppressions = resource_suppressions

    def visit(self, node: IConstruct):
        if "is_cfn_element" in dir(node) and \
            node.is_cfn_element(node) and \
            getattr(node, "cfn_resource_type", None) is not None and \
            node.cfn_resource_type in self.resource_suppressions:
                add_cfn_guard_suppressions(node, self.resource_suppressions[node.cfn_resource_type])
        elif "is_cfn_element" in dir(node.node.default_child) and \
            getattr(node.node.default_child, "cfn_resource_type", None) is not None and \
            node.node.default_child.cfn_resource_type in self.resource_suppressions:
                add_cfn_guard_suppressions(node.node.default_child, self.resource_suppressions[node.node.default_child.cfn_resource_type])
