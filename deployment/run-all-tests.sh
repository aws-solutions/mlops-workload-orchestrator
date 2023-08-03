#!/bin/bash
######################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################
#
# This script runs all tests for the root CDK project, as well as any microservices, Lambda functions, or dependency
# source code packages. These include unit tests, integration tests, and snapshot tests.
#
# It is important that this script  be tested and validated to ensure that all available test fixtures are run.
#

[ "$DEBUG" == 'true' ] && set -x
set -e

setup_python_env() {
	if [ -d "./.venv-test" ]; then
		echo "Reusing already setup python venv in ./.venv-test. Delete ./.venv-test if you want a fresh one created."
		return
	fi
	echo "Setting up python venv"
	python3 -m venv .venv-test
	echo "Initiating virtual environment"
	source .venv-test/bin/activate
	echo "upgrading pip -> python3 -m pip install --upgrade pip"
    python3 -m pip install --upgrade pip
	echo "Installing python packages"
	pip3 install -r requirements-test.txt
	pip3 install -r requirements.txt
	echo "deactivate virtual environment"
	deactivate
}


run_python_lambda_test() {
	lambda_name=$1
	lambda_description=$2
	run_python_test $source_dir/lambda $lambda_name
}

setup_and_activate_python_env() {
	module_path=$1
	cd $module_path

	[ "${CLEAN:-true}" = "true" ] && rm -fr .venv-test

	setup_python_env

	echo "Initiating virtual environment"
	source .venv-test/bin/activate
}


run_python_test() {
	module_path=$(pwd)
	module_name=$1
	echo "------------------------------------------------------------------------------"
	echo "[Test] Python path=$module_path module=$module_name"
	echo "------------------------------------------------------------------------------"

	coverage_report_path=$coverage_dir/$module_name.coverage.xml
	echo "coverage report path set to $coverage_report_path"

	# Use -vv for debugging
	python3 -m pytest --cov --cov-fail-under=80 --cov-report=term-missing --cov-report "xml:$coverage_report_path"
	if [ "$?" = "1" ]; then
		echo "(source/run-all-tests.sh) ERROR: there is likely output above." 1>&2
		exit 1
	fi
	sed -i -e "s,<source>$source_dir,<source>source,g" $coverage_report_path
}

run_javascript_lambda_test() {
	lambda_name=$1
	lambda_description=$2
	echo "------------------------------------------------------------------------------"
	echo "[Test] Javascript Lambda: $lambda_name, $lambda_description"
	echo "------------------------------------------------------------------------------"
	cd $source_dir/lambda/$lambda_name
	[ "${CLEAN:-true}" = "true" ] && npm run clean
	npm ci
	npm test
	if [ "$?" = "1" ]; then
		echo "(source/run-all-tests.sh) ERROR: there is likely output above." 1>&2
		exit 1
	fi
	[ "${CLEAN:-true}" = "true" ] && rm -fr coverage
}


run_cdk_project_test() {
	echo "------------------------------------------------------------------------------"
	echo "[Test] Running CDK tests"
	echo "------------------------------------------------------------------------------"

	# Test the Lambda functions
	cd $source_dir/infrastructure

	coverage_report_path=$coverage_dir/cdk.coverage.xml
	echo "coverage report path set to $coverage_report_path"

	cd $source_dir/infrastructure
	# Use -vv for debugging
	python3 -m pytest --cov --cov-fail-under=80 --cov-report=term-missing --cov-report "xml:$coverage_report_path"
	rm -rf *.egg-info
	sed -i -e "s,<source>$source_dir,<source>source,g" $coverage_report_path


}

run_framework_lambda_test() {
	echo "------------------------------------------------------------------------------"
	echo "[Test] Run framework lambda unit tests"
	echo "------------------------------------------------------------------------------"

	# Test the Lambda functions
	cd $source_dir/lambdas
	for folder in */ ; do
		cd "$folder"
		function_name=${PWD##*/}

		pip install -r requirements-test.txt
		run_python_test $(basename $folder)
		rm -rf *.egg-info

		cd ..
	done
}

run_blueprint_lambda_test() {
	echo "------------------------------------------------------------------------------"
	echo "[Test] Run blueprint lambda unit tests"
	echo "------------------------------------------------------------------------------"
				   
	cd $source_dir/infrastructure/lib/blueprints/lambdas
	for folder in */ ; do
		echo "$folder"
		cd "$folder"
		if [ "$folder" != "sagemaker_layer/" ]; then
			pip install -r requirements-test.txt
			run_python_test $(basename $folder)
			rm -rf *.egg-info
			cd ..
		fi
	done
}

# Save the current working directory and set source directory
source_dir=$PWD
cd $source_dir

# setup coverage report directory
coverage_dir=$source_dir/test/coverage-reports
mkdir -p $coverage_dir

# Clean the test environment before running tests and after finished running tests
# The variable is option with default of 'true'. It can be overwritten by caller
# setting the CLEAN environment variable. For example
#    $ CLEAN=true ./run-all-tests.sh
# or
#    $ CLEAN=false ./run-all-tests.sh
#
CLEAN="${CLEAN:-true}"

setup_and_activate_python_env $source_dir
python --version
run_framework_lambda_test
run_blueprint_lambda_test
run_cdk_project_test

# deactive Python envn
deactivate


# Return to the source/ level where we started
cd $source_dir