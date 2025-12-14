"""Timing utilities"""

import time
import random


def human_delay(min_ms=300, max_ms=800):
    """Random human-like delay"""
    delay = random.uniform(min_ms, max_ms) / 1000
    time.sleep(delay)
