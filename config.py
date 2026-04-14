# ==============================================================================
# AIFS Real-Time Workflow Configuration
# Edit this file before running the workflow on a new system.
# ==============================================================================

import os

# ------------------------------------------------------------------------------
# USER SETTINGS — edit these for your system
# ------------------------------------------------------------------------------

USER = "ang.wj"

BASE_DIR = "/data/projects/17001770/weather_department/nwp/wjang/aifs_rt"

PBS_PROJECT = "17001770"

PLATFORM = "aspire"

# ------------------------------------------------------------------------------
# DERIVED PATHS — do not edit these
# ------------------------------------------------------------------------------

RAW_DIR          = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR    = os.path.join(BASE_DIR, "data", "processed")
PLOTS_DIR        = os.path.join(BASE_DIR, "data", "plots")
PLOTS_GIF_DIR    = os.path.join(PLOTS_DIR, "gif")
PLOTS_FRAMES_DIR = os.path.join(PLOTS_DIR, "frames")
LOG_DIR          = os.path.join(BASE_DIR, "logs")

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
STEPS          = list(range(0, 174, 6))

PARAMS = [
    "2t", "2d",
    "10u", "10v",
    "100u", "100v",
    "msl", "sp",
    "tp", "cp", "sf", "ro",
    "t", "u", "v", "w", "z", "q"
]
