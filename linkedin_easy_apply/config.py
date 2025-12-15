"""Configuration and timing profiles for Easy Apply automation"""

# ========================================
# SPEED MODE CONFIGURATION
# ========================================
# Choose one mode (set all others to False):
# - DEV_TEST_SPEED: 40-50% faster (1.5x-2x speed)
# - SUPER_DEV_SPEED: 70-80% faster (3x-5x speed) - maximum safe speed
# - Production: All False (default, safest)

DEV_TEST_SPEED = False
SUPER_DEV_SPEED = True  # ⚡ Maximum safe speed for rapid testing

# ========================================
# TIMING PROFILES
# ========================================
# All delays are in milliseconds (ms)
# Each delay maintains randomization via human_delay() for organic behavior

TIMING_PROFILES = {
    "default": {
        # Keyboard interaction delays
        "key_delay_min": 200,  # Min delay after key press
        "key_delay_max": 400,  # Max delay after key press
        "focus_delay_min": 300,  # Min delay after focus
        "focus_delay_max": 500,  # Max delay after focus
        # Dropdown interaction delays
        "dropdown_open_min": 300,  # Min wait for dropdown to open
        "dropdown_open_max": 500,  # Max wait for dropdown to open
        "dropdown_nav_min": 50,  # Min delay between arrow key presses
        "dropdown_nav_max": 100,  # Max delay between arrow key presses
        "dropdown_verify_min": 100,  # Min wait to verify selection
        "dropdown_verify_max": 150,  # Max wait to verify selection
        "dropdown_close_min": 400,  # Min wait after closing dropdown
        "dropdown_close_max": 600,  # Max wait after closing dropdown
        # Modal and UI transition delays
        "modal_transition_min": 400,  # Min wait for modal transitions
        "modal_transition_max": 600,  # Max wait for modal transitions
        # Text input delays
        "post_input_min": 200,  # Min delay after typing
        "post_input_max": 400,  # Max delay after typing
    },
    "dev_test": {
        # Keyboard interaction delays (40-50% faster)
        "key_delay_min": 120,
        "key_delay_max": 240,
        "focus_delay_min": 180,
        "focus_delay_max": 300,
        # Dropdown interaction delays (40-50% faster)
        "dropdown_open_min": 180,
        "dropdown_open_max": 300,
        "dropdown_nav_min": 30,  # Still > 25ms minimum
        "dropdown_nav_max": 60,
        "dropdown_verify_min": 60,
        "dropdown_verify_max": 90,
        "dropdown_close_min": 240,
        "dropdown_close_max": 360,
        # Modal and UI transition delays (40% faster, respects 400ms minimum)
        "modal_transition_min": 400,  # Kept at safe minimum
        "modal_transition_max": 450,
        # Text input delays (40-50% faster)
        "post_input_min": 120,
        "post_input_max": 240,
    },
    "super_dev": {
        # Keyboard interaction delays (70-80% faster - minimal but human-plausible)
        "key_delay_min": 60,  # Just above detection threshold
        "key_delay_max": 120,
        "focus_delay_min": 100,  # Fast but not instant
        "focus_delay_max": 150,
        # Dropdown interaction delays (70-80% faster)
        "dropdown_open_min": 90,  # Minimal safe open time
        "dropdown_open_max": 150,
        "dropdown_nav_min": 25,  # Absolute minimum (safety floor)
        "dropdown_nav_max": 40,
        "dropdown_verify_min": 40,  # Quick verification
        "dropdown_verify_max": 60,
        "dropdown_close_min": 150,  # Fast close (respects 150ms minimum)
        "dropdown_close_max": 200,
        # Modal and UI transition delays (respects 400ms minimum for stability)
        "modal_transition_min": 400,  # Cannot go lower without breaking
        "modal_transition_max": 450,  # Tight range for speed
        # Text input delays (70-80% faster)
        "post_input_min": 60,
        "post_input_max": 120,
    },
}

# ========================================
# ACTIVE TIMING CONFIGURATION
# ========================================
# Select profile based on speed mode flags (priority: SUPER_DEV > DEV_TEST > default)
if SUPER_DEV_SPEED:
    TIMING = TIMING_PROFILES["super_dev"]
    _ACTIVE_MODE = "super_dev"
elif DEV_TEST_SPEED:
    TIMING = TIMING_PROFILES["dev_test"]
    _ACTIVE_MODE = "dev_test"
else:
    TIMING = TIMING_PROFILES["default"]
    _ACTIVE_MODE = "default"

# ========================================
# SAFETY VALIDATIONS
# ========================================
# Ensure timing values meet minimum thresholds
_MIN_DELAY_MS = 25
_MIN_MODAL_TRANSITION_MS = 400
_MIN_DROPDOWN_CLOSE_MS = 150  # Only dropdown close needs 150ms minimum


def get_active_timing():
    """Get the active timing profile based on current speed mode settings"""
    if SUPER_DEV_SPEED:
        return TIMING_PROFILES["super_dev"]
    elif DEV_TEST_SPEED:
        return TIMING_PROFILES["dev_test"]
    else:
        return TIMING_PROFILES["default"]


# Initialize TIMING with current settings
TIMING = get_active_timing()

# Validate and fallback to default if constraints violated
_violations = []

for key, value in TIMING.items():
    if "nav" in key and value < _MIN_DELAY_MS:
        _violations.append(f"{key}={value}ms < {_MIN_DELAY_MS}ms minimum")
    if "modal" in key and value < _MIN_MODAL_TRANSITION_MS:
        _violations.append(f"{key}={value}ms < {_MIN_MODAL_TRANSITION_MS}ms minimum")
    if "dropdown_close" in key and "min" in key and value < _MIN_DROPDOWN_CLOSE_MS:
        _violations.append(f"{key}={value}ms < {_MIN_DROPDOWN_CLOSE_MS}ms minimum")

if _violations:
    print("⚠️ TIMING PROFILE VIOLATIONS - Falling back to default profile:")
    for violation in _violations:
        print(f"  - {violation}")
    TIMING = TIMING_PROFILES["default"]
    DEV_TEST_SPEED = False

# ========================================
# STARTUP LOGGING
# ========================================
if DEV_TEST_SPEED:
    print("\n" + "=" * 60)
    print("⚙️  DEV TEST SPEED MODE ENABLED")
    print("=" * 60)
    print("Timing profile: ~40-50% faster than default")
    print("For production use, set DEV_TEST_SPEED = False in config.py")
    print("=" * 60 + "\n")
