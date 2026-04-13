#!/usr/bin/env python3
"""
Real-time download script for AIFS workflow.
Probe window logic:
  - Cycle 1: data already confirmed available by detect_start.py — no probing needed
  - Cycle 2: probe every 10 min for up to 7 hours
  - Cycle 3: probe every 10 min for up to 7 hours, records data availability duration
  - Cycle 4+: adaptive wait task already slept, probe every 10 min for 2 hours
"""

import os
import sys
import time
import pathlib
from datetime import datetime, timedelta
from ecmwf.opendata import Client

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ==============================================================================
# CONFIGURATION — all settings come from config.py
# ==============================================================================
RAW_DIR              = config.RAW_DIR
RETRY_INTERVAL_MINS  = config.RETRY_INTERVAL_MINS
CYCLE2_TIMEOUT_HOURS = config.CYCLE2_TIMEOUT_HOURS
STEADY_TIMEOUT_HOURS = config.STEADY_TIMEOUT_HOURS
DURATION_FILE        = config.DURATION_FILE
STEPS                = config.STEPS
PARAMS               = config.PARAMS
# ==============================================================================


def setup_dirs():
    pathlib.Path(RAW_DIR).mkdir(parents=True, exist_ok=True)


def get_initial_cycle_point():
    """
    Read the initial cycle point from Cylc environment variable.
    Falls back to a manual value if running outside Cylc.
    """
    icp = os.environ.get("CYLC_WORKFLOW_INITIAL_CYCLE_POINT")
    if icp:
        return datetime.strptime(icp, "%Y%m%dT%H%MZ")
    print("WARNING: CYLC_WORKFLOW_INITIAL_CYCLE_POINT not set, using fallback")
    return datetime(2026, 4, 13, 6)


def get_cycle_time():
    """
    Read the current cycle's time from Cylc environment variable.
    """
    cycle_point = os.environ.get("CYLC_TASK_CYCLE_POINT")
    if cycle_point:
        try:
            dt = datetime.strptime(cycle_point, "%Y%m%dT%H%MZ")
            print(f"Cycle time from Cylc: {dt}")
            return dt
        except ValueError:
            print(f"WARNING: Could not parse CYLC_TASK_CYCLE_POINT='{cycle_point}'")
    INIT_TIME = datetime(2026, 4, 13, 6)
    print(f"Using manual INIT_TIME: {INIT_TIME}")
    return INIT_TIME


def get_cycle_info(init_time):
    """
    Cycle 1 = initial cycle point       -> attempt once
    Cycle 2 = initial cycle point + 6h  -> probe up to 7h
    Cycle 3 = initial cycle point + 12h -> probe up to 7h, record duration
    Cycle 4+ = anything after           -> probe up to 2h
    Returns (max_wait_mins, is_cycle3)
    """
    initial_cp = get_initial_cycle_point()
    cycle2_cp  = initial_cp + timedelta(hours=6)
    cycle3_cp  = initial_cp + timedelta(hours=12)

    if init_time == initial_cp:
        print(f"  Cycle 1 — data already confirmed available, attempting once")
        return 0, False
    elif init_time == cycle2_cp:
        print(f"  Cycle 2 — probing up to {CYCLE2_TIMEOUT_HOURS}h for new data")
        return CYCLE2_TIMEOUT_HOURS * 60, False
    elif init_time == cycle3_cp:
        print(f"  Cycle 3 — probing up to {CYCLE2_TIMEOUT_HOURS}h, will record data availability duration")
        return CYCLE2_TIMEOUT_HOURS * 60, True
    else:
        print(f"  Cycle 4+ — adaptive wait already done, probing up to {STEADY_TIMEOUT_HOURS}h")
        return STEADY_TIMEOUT_HOURS * 60, False


def save_duration(probe_start_time, data_found_time):
    """
    Save the measured data availability duration to a file.
    Read by wait_adaptive.sh to determine sleep time for cycle 4+.
    """
    duration_secs           = int((data_found_time - probe_start_time).total_seconds())
    duration_hrs            = duration_secs // 3600
    duration_mins_remainder = (duration_secs % 3600) // 60
    sleep_secs              = max(0, duration_secs - 1800)
    sleep_hrs               = sleep_secs // 3600
    sleep_mins_remainder    = (sleep_secs % 3600) // 60

    with open(DURATION_FILE, "w") as f:
        f.write(f"{duration_secs}\n")

    print(f"\n  {'='*55}")
    print(f"  DATA AVAILABILITY DURATION (Cycle 3 measurement)")
    print(f"  Probing started : {probe_start_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Data found at   : {data_found_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Duration        : {duration_hrs}h {duration_mins_remainder}m ({duration_secs}s)")
    print(f"  Cycle 4+ sleep  : {sleep_hrs}h {sleep_mins_remainder}m (duration - 30 min)")
    print(f"  Saved to        : {DURATION_FILE}")
    print(f"  {'='*55}\n")


def try_download(dt, out_path):
    """
    Attempt to download AIFS forecast for given cycle time.
    Returns True if successful, False otherwise.
    """
    try:
        client = Client(source="ecmwf", model="aifs-single")
        client.retrieve(
            date=dt.strftime("%Y%m%d"),
            time=dt.hour,
            step=STEPS,
            param=PARAMS,
            target=out_path,
        )
        return os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except Exception as e:
        if os.path.exists(out_path):
            os.remove(out_path)
        print(f"  Download attempt failed: {e}")
        return False


def download_with_retry(dt, max_wait_mins, is_cycle3=False):
    """
    Download AIFS forecast with retry logic.
    For cycle 3, records how long it took for data to appear.
    """
    out_filename = f"aifs_{dt.strftime('%Y-%m-%d')}_{dt.hour:02d}z.grib2"
    out_path     = os.path.join(RAW_DIR, out_filename)
    max_retries  = max(1, int(max_wait_mins // RETRY_INTERVAL_MINS))

    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        print(f"  [SKIP] Already exists: {out_filename}")
        return out_path

    print(f"  [DOWNLOAD] {out_filename} ...")

    # Start timer for cycle 3
    if is_cycle3:
        probe_start = datetime.utcnow()
        print(f"  [CYCLE 3] Timer started: {probe_start.strftime('%Y-%m-%d %H:%M UTC')}")

    success = False
    for attempt in range(1, max_retries + 1):
        print(f"  Attempt {attempt}/{max_retries} ...")
        if try_download(dt, out_path):
            print(f"  [DONE] {out_filename}")
            if is_cycle3:
                data_found = datetime.utcnow()
                save_duration(probe_start, data_found)
            success = True
            break
        if attempt < max_retries:
            print(f"  Not available yet. Waiting {RETRY_INTERVAL_MINS} mins ...")
            time.sleep(RETRY_INTERVAL_MINS * 60)

    if not success:
        raise RuntimeError(
            f"AIFS data for {dt} not available after "
            f"{max_wait_mins:.0f} minutes. Giving up."
        )

    return out_path


def main():
    init_time                = get_cycle_time()
    max_wait_mins, is_cycle3 = get_cycle_info(init_time)

    print("=" * 60)
    print(" AIFS Real-Time Download Script")
    print(f" Forecast init time : {init_time}")
    print(f" Max wait           : {max_wait_mins:.0f} mins")
    print(f" Record duration    : {is_cycle3}")
    print("=" * 60)

    setup_dirs()
    download_with_retry(init_time, max_wait_mins, is_cycle3)

    print("\n" + "=" * 60)
    print(" Download complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
