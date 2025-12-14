#!/bin/bash
# LinkedIn Easy Apply Bot - Runner Script

if [ -z "$1" ]; then
    echo "Usage: ./run.sh <job_url>"
    echo "Example: ./run.sh https://www.linkedin.com/jobs/view/1234567890/"
    exit 1
fi

# Activate venv and run
source venv/bin/activate
python -m linkedin_easy_apply.main "$1"
