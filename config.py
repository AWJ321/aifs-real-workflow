import os

USER = "ang.wj"
BASE_DIR = "/data/projects/17001770/weather_department/nwp/wjang/aifs_rt"
PBS_PROJECT = "17001770"
PLATFORM = "aspire"

RAW_DIR       = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
PLOTS_DIR         = os.path.join(BASE_DIR, "data", "plots")
PLOTS_GIF_DIR     = os.path.join(PLOTS_DIR, "gif")
PLOTS_FRAMES_DIR  = os.path.join(PLOTS_DIR, "frames")

# New plot output directories
PLOTS_PRECIP_GIF_DIR    = os.path.join(BASE_DIR, "data", "plots_precip", "gif")
PLOTS_PRECIP_FRAMES_DIR = os.path.join(BASE_DIR, "data", "plots_precip", "frames")
PLOTS_WIND_GIF_DIR      = os.path.join(BASE_DIR, "data", "plots_wind", "gif")
PLOTS_WIND_FRAMES_DIR   = os.path.join(BASE_DIR, "data", "plots_wind", "frames")

LOG_DIR        = os.path.join(BASE_DIR, "logs")
DURATION_FILE  = os.path.join(BASE_DIR, "data_availability_duration.txt")
CAUGHT_UP_FILE = os.path.join(BASE_DIR, "caught_up.txt")

RETRY_INTERVAL_MINS  = 10
CYCLE2_TIMEOUT_HOURS = 7
STEADY_TIMEOUT_HOURS = 4

STEPS  = list(range(0, 174, 6))
PARAMS = [
    "2t", "2d",
    "10u", "10v",
    "100u", "100v",
    "msl", "sp",
    "tp", "cp", "sf", "ro",
    "t", "u", "v", "w", "z", "q"
]
