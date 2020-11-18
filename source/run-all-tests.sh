#!/bin/bash

[ "$DEBUG" == 'true' ] && set -x
set -e

source_dir="$PWD"
echo "------------------------------------------------------------------------------"
echo "[Init] Setup the Python environment"
echo "------------------------------------------------------------------------------"

echo "cd $source_dir"
cd $source_dir
echo "python3 -m venv .env"
python3 -m venv .env
echo "source .env/bin/activate"
source .env/bin/activate
echo "pip install -r requirements-test.txt"
pip install -r requirements-test.txt


echo "------------------------------------------------------------------------------"
echo "[Test] Run framework lambda unit tests"
echo "------------------------------------------------------------------------------"

echo "cd lambdas"
cd lambdas

for d in `find . -mindepth 1 -maxdepth 1 -type d`; do
  if [ $d != "./custom_resource" ]; then
    cd $d
    pip install -r requirements-test.txt
    pytest --cov --cov-fail-under=80
    rm -rf *.egg-info
    cd ..
  fi
done

echo "------------------------------------------------------------------------------"
echo "[Test] Run blueprint lambda unit tests"
echo "------------------------------------------------------------------------------"

echo "cd $source_dir/lib/blueprints/byom/lambdas"
cd $source_dir/lib/blueprints/byom/lambdas

for d in `find . -mindepth 1 -maxdepth 1 -type d`; do
  if [ $d != "./sagemaker_layer" ]; then
    cd $d
    pip install -r requirements-test.txt
    pytest --cov --cov-fail-under=80
    rm -rf *.egg-info
    cd ..
  fi
done

echo "Done unit testing"