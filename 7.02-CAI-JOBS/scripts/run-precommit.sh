#!/bin/bash
# Script to run pre-commit only on the CAI-JOBS project

cd "$(dirname "$0")"

echo "Running pre-commit hooks for CAI-JOBS project only..."

# Run pre-commit on Python files in this directory only
pre-commit run --files \
  main.py \
  requirements.txt

echo "Pre-commit check completed for CAI-JOBS project."
