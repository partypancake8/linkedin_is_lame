#!/bin/bash
# LinkedIn Easy Apply Bot - Runner Script

if [ -z "$1" ]; then
    echo "Usage: ./run.sh [--speed dev|super] <job_url>"
    echo ""
    echo "Examples:"
    echo "  ./run.sh https://www.linkedin.com/jobs/view/1234567890/"
    echo "  ./run.sh --speed dev https://www.linkedin.com/jobs/view/1234567890/"
    echo "  ./run.sh --speed super https://www.linkedin.com/jobs/view/1234567890/"
    echo ""
    echo "Speed modes:"
    echo "  (none)       Production speed (default, safest)"
    echo "  --speed dev  1.5x-2x faster (40-50% reduction)"
    echo "  --speed super 3x-5x faster (70-80% reduction)"
    exit 1
fi

# Activate venv and run with all arguments
source venv/bin/activate
python -m linkedin_easy_apply.main "$@"
