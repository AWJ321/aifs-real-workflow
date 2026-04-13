# ==============================================================================
# AIFS Real-Time Workflow Configuration
# Edit this file before running the workflow on a new system.
# ==============================================================================

import os

# ------------------------------------------------------------------------------
# USER SETTINGS — edit these for your system
# ------------------------------------------------------------------------------

USER = "ang.wj"

# Base directory where all data will be stored
BASE_DIR = "/data/projects/17001770/weather_department/nwp/wjang/aifs_rt"

# PBS project code
PBS_PROJECT = "17001770"

# Cylc platform name
PLATFORM = "aspire"

# ------------------------------------------------------------------------------
# DERIVED PATHS — do not edit these
# ------------------------------------------------------------------------------

RAW_DIR       = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
PLOTS_DIR     = os.path.join(BASE_DIR, "data", "plots")
LOG_DIR       = os.path.join(BASE_DIR, "logs")

# File that stores measured data availability duration from cycle 3
DURATION_FILE = os.path.join(BASE_DIR, "data_availability_duration.txt")

# ------------------------------------------------------------------------------
# DOWNLOAD SETTINGS
# ------------------------------------------------------------------------------
RETRY_INTERVAL_MINS  = 10
CYCLE2_TIMEOUT_HOURS = 7
STEADY_TIMEOUT_HOURS = 2

# ------------------------------------------------------------------------------
# FORECAST SETTINGS
# ------------------------------------------------------------------------------
FORECAST_HOURS = 168
STEP_HOURS     = 6
STEPS          = list(range(0, 174, 6))  # 0 to 168h

PARAMS = [
    "2t", "2d",
    "10u", "10v",
    "100u", "100v",
    "msl", "sp",
    "tp", "cp", "sf", "ro",
    "t", "u", "v", "w", "z", "q"
]
