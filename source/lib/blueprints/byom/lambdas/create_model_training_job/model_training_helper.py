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
from sagemaker.estimator import Estimator
from sagemaker.tuner import HyperparameterTuner
from sagemaker.inputs import TrainingInput
from sagemaker.parameter import ParameterRange
from sagemaker.tuner import ContinuousParameter, IntegerParameter, CategoricalParameter
from shared.wrappers import exception_handler
from typing import Dict, Any, List
from enum import Enum


class TrainingType(Enum):
    TrainingJob = 1
    HyperparameterTuningJob = 2


class SolutionModelTraining:
    def __init__(
        self,
        job_name: str,
        estimator_config: Dict[str, Any],
        hyperparameters: Dict[str, Any],
        data_channels: Dict[str, TrainingInput],
        job_type: TrainingType = TrainingType.TrainingJob,
        hyperparameter_tuner_config: Dict[str, Any] = None,
        hyperparameter_ranges: Dict[str, ParameterRange] = None,
    ) -> None:
        self.job_name = job_name
        self.estimator_config = estimator_config
        self.hyperparameters = hyperparameters
        self.data_channels = data_channels
        self.job_type = job_type
        self.hyperparameter_tuner_config = hyperparameter_tuner_config
        self.hyperparameter_ranges = hyperparameter_ranges

    @exception_handler
    def create_training_job(self):
        # create Training Job type MonitoringType->function_name map
        type_function_map = dict(
            TrainingJob="_create_estimator",
            HyperparameterTuningJob="_create_hyperparameter_tuner",
        )

        # call the right function to create the training/hyperparameter tunning Job
        job = getattr(self, type_function_map[self.job_type.name])()
        # start the training/hyperparameters tuning job
        job.fit(job_name=self.job_name, inputs=self.data_channels, wait=False)

    @exception_handler
    def _create_estimator(self):
        # create the estimator
        estimator = Estimator(**self.estimator_config)
        # set its hyperparameters
        estimator.set_hyperparameters(**self.hyperparameters)
        # return the estimator to the caller
        return estimator

    @exception_handler
    def _create_hyperparameter_tuner(self):
        # create the estimator
        estimator = self._create_estimator()
        # configure the hyperparameters tuning job
        hyperparameter_tuner = HyperparameterTuner(
            estimator=estimator, hyperparameter_ranges=self.hyperparameter_ranges, **self.hyperparameter_tuner_config
        )
        # return the hyperparameter tuner
        return hyperparameter_tuner

    @staticmethod
    @exception_handler
    def format_search_grid(hyperparameter_ranges: Dict[str, List]) -> Dict[str, ParameterRange]:
        parameter_type_map = dict(
            integer=IntegerParameter, continuous=ContinuousParameter, categorical=CategoricalParameter
        )
        search_grid = {
            k: (parameter_type_map[v[0]](*v[1]) if v[0] != "categorical" else parameter_type_map[v[0]](v[1]))
            for k, v in hyperparameter_ranges.items()
        }
        return search_grid
