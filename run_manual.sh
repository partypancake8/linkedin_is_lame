#!/bin/bash
# Wrapper to run the manual Easy Apply bot

if [ -z "$1" ]; then
    echo "Usage: ./run_manual.sh <job_url>"
    echo "Example: ./run_manual.sh https://www.linkedin.com/jobs/view/4339460943/"
    exit 1
fi

source venv/bin/activate
python bot_manual.py "$1"
