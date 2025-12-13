# Project Structure

```
linkedin_is_lame/
├── bot_manual.py          # Main bot - manual Easy Apply trigger (recommended)
├── bot.py                 # Experimental fully-automated bot
├── login.py               # Helper for initial LinkedIn login
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
│
├── run_manual.sh         # Script to run manual bot
├── run.sh                # Script to run automated bot
├── setup_login.sh        # Script to set up LinkedIn session
│
├── PLAN.md               # Original project plan
├── README.md             # Main documentation
├── RESEARCH_FINDINGS.md  # Research on LinkedIn automation
│
├── venv/                 # Python virtual environment (gitignored)
├── browser_data/         # Persistent browser session (gitignored)
├── log.jsonl            # Application logs (gitignored)
└── archive/             # Old debug scripts and screenshots (gitignored)
```

## Core Files

### Active Scripts

- **bot_manual.py** - Production-ready bot with manual Easy Apply trigger
- **bot.py** - Experimental automation (blocked by LinkedIn)
- **login.py** - One-time setup for LinkedIn session

### Helper Scripts

- **run_manual.sh** - Wrapper to run bot_manual.py
- **run.sh** - Wrapper to run bot.py
- **setup_login.sh** - Wrapper to run login.py

### Documentation

- **README.md** - Setup and usage instructions
- **PLAN.md** - Original technical specification
- **RESEARCH_FINDINGS.md** - Analysis of working implementations

## Ignored Directories (Not in Git)

- `venv/` - Python dependencies (143MB)
- `browser_data/` - Chrome profile with LinkedIn session
- `archive/` - Debug scripts and screenshots
- `log.jsonl` - Application run logs
