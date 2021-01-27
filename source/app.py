#!/usr/bin/env python3
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
from aws_cdk import core
from lib.aws_mlops_stack import MLOpsStack
from lib.blueprints.byom.byom_batch_build_container import BYOMBatchBuildStack
from lib.blueprints.byom.byom_batch_builtin_container import BYOMBatchBuiltinStack
from lib.blueprints.byom.byom_realtime_build_container import BYOMRealtimeBuildStack
from lib.blueprints.byom.byom_realtime_builtin_container import BYOMRealtimeBuiltinStack
from lib.blueprints.byom.model_monitor import ModelMonitorStack

solution_id = "SO0136"
app = core.App()
MLOpsStack(app, "aws-mlops-framework", description=f"({solution_id}) - AWS MLOps Framework. Version %%VERSION%%")

BYOMBatchBuildStack(
    app,
    "BYOMBatchBuildStack",
    description=(
        f"({solution_id}byom-bc) - Bring Your Own Model pipeline with Batch Transform and a custom "
        f"model build in AWS MLOps Framework. Version %%VERSION%%"
    ),
)
BYOMBatchBuiltinStack(
    app,
    "BYOMBatchBuiltinStack",
    description=(
        f"({solution_id}byom-bb) - Bring Your Own Model pipeline with Batch Transform and a Built-in "
        f"Sagemaker model in AWS MLOps Framework. Version %%VERSION%%"
    ),
)
BYOMRealtimeBuildStack(
    app,
    "BYOMRealtimeBuildStack",
    description=(
        f"({solution_id}byom-rc) - Bring Your Own Model pipeline with Realtime inference and a custom "
        f"model build in AWS MLOps Framework. Version %%VERSION%%"
    ),
)
BYOMRealtimeBuiltinStack(
    app,
    "BYOMRealtimeBuiltinStack",
    description=(
        f"({solution_id}byom-rb) - Bring Your Own Model pipeline with Realtime inference and a Built-in "
        f"Sagemaker model in AWS MLOps Framework. Version %%VERSION%%"
    ),
)

ModelMonitorStack(
    app,
    "ModelMonitorStack",
    description=(f"({solution_id}byom-mm) - Model Monitor pipeline. Version %%VERSION%%"),
)

app.synth()
