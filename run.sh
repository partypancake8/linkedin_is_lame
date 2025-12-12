#!/bin/bash
# Helper script to run the LinkedIn Easy Apply bot

# Activate virtual environment
source venv/bin/activate

# Run the bot with the provided job URL
python bot.py "$@"
