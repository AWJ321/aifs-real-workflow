#!/usr/bin/env python3
"""
Real-time download script for AIFS workflow.
Probe window logic:
- Catch-up cycles (cycle point < latest available): download immediately
- New Cycle 1 (cycle point == latest available): download immediately, write caught_up.txt
- New Cycle 2 (latest available + 6h): probe every 10 min for up to 7 hours
- New Cycle 3 (latest available + 12h): probe every 10 min for up to 7 hours, records duration
- New Cycle 4+ (latest available + 18h+): adaptive wait already slept, probe for 2 hours
"""

import os
import sys
import time
import pathlib
import subprocess
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
CAUGHT_UP_FILE       = os.path.join(config.BASE_DIR, "caught_up.txt")
SCRIPTS_DIR          = os.path.dirname(os.path.abspath(__file__))
# ==============================================================================


def setup_dirs():
    pathlib.Path(RAW_DIR).mkdir(parents=True, exist_ok=True)


def get_latest_available():
    """Run detect_start.py to get latest available AIFS cycle point."""
    try:
        result = subprocess.run(
            ["python", os.path.join(SCRIPTS_DIR, "detect_start.py")],
            capture_output=True, text=True, timeout=120
        )
        cp = result.stdout.strip()
        if cp:
            return datetime.strptime(cp, "%Y%m%dT%H%MZ")
    except Exception as e:
        print(f"WARNING: detect_start.py failed: {e}")
    return None


def get_caught_up_cycle():
    if os.path.exists(CAUGHT_UP_FILE):
        with open(CAUGHT_UP_FILE) as f:
            return datetime.strptime(f.read().strip(), "%Y%m%dT%H%MZ")
    return None


def write_caught_up(cycle_point):
    with open(CAUGHT_UP_FILE, "w") as f:
        f.write(cycle_point.strftime("%Y%m%dT%H%MZ"))
    print(f"  [CAUGHT UP] Written to {CAUGHT_UP_FILE}: {cycle_point}")


def get_cycle_time():
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
    caught_up_cp = get_caught_up_cycle()

    if caught_up_cp is None:
        print("  Checking latest available data...")
        latest = get_latest_available()

        if latest is None:
            print("  WARNING: Could not get latest available, treating as catch-up")
            return 0, False

        print(f"  Latest available: {latest}")

        if init_time < latest:
            print(f"  Catch-up cycle — downloading immediately")
            return 0, False
        elif init_time == latest:
            print(f"  Caught up! This is new Cycle 1 — downloading immediately")
            write_caught_up(init_time)
            return 0, False
        else:
            print(f"  Cycle point ahead of latest available — treating as new Cycle 2")
            write_caught_up(init_time - timedelta(hours=6))
            caught_up_cp = init_time - timedelta(hours=6)

    cycle2_cp = caught_up_cp + timedelta(hours=6)
    cycle3_cp = caught_up_cp + timedelta(hours=12)

    if init_time == caught_up_cp:
        print(f"  New Cycle 1 — data already confirmed available, attempting once")
        return 0, False
    elif init_time == cycle2_cp:
        print(f"  New Cycle 2 — probing up to {CYCLE2_TIMEOUT_HOURS}h for new data")
        return CYCLE2_TIMEOUT_HOURS * 60, False
    elif init_time == cycle3_cp:
        print(f"  New Cycle 3 — probing up to {CYCLE2_TIMEOUT_HOURS}h, will record duration")
        return CYCLE2_TIMEOUT_HOURS * 60, True
    else:
        print(f"  New Cycle 4+ — adaptive wait already done, probing up to {STEADY_TIMEOUT_HOURS}h")
        return STEADY_TIMEOUT_HOURS * 60, False


def save_duration(probe_start_time, data_found_time):
    if os.path.exists(DURATION_FILE):
        print(f"  Duration file already exists — keeping existing value, not overwriting")
        return

    duration_secs           = int((data_found_time - probe_start_time).total_seconds())
    duration_hrs            = duration_secs // 3600
    duration_mins_remainder = (duration_secs % 3600) // 60
    sleep_secs              = max(0, duration_secs - 1800)
    sleep_hrs               = sleep_secs // 3600
    sleep_mins_remainder    = (sleep_secs % 3600) // 60

    with open(DURATION_FILE, "w") as f:
        f.write(f"{duration_secs}\n")

    print(f"\n  {'='*55}")
    print(f"  DATA AVAILABILITY DURATION (New Cycle 3 measurement)")
    print(f"  Probing started : {probe_start_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Data found at   : {data_found_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Duration        : {duration_hrs}h {duration_mins_remainder}m ({duration_secs}s)")
    print(f"  Cycle 4+ sleep  : {sleep_hrs}h {sleep_mins_remainder}m (duration - 30 min)")
    print(f"  Saved to        : {DURATION_FILE}")
    print(f"  {'='*55}\n")


def try_download(dt, out_path):
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
    out_filename = f"aifs_{dt.strftime('%Y-%m-%d')}_{dt.hour:02d}z.grib2"
    out_path     = os.path.join(RAW_DIR, out_filename)
    max_retries  = max(1, int(max_wait_mins // RETRY_INTERVAL_MINS))

    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        print(f"  [SKIP] Already exists: {out_filename}")
        return out_path

    print(f"  [DOWNLOAD] {out_filename} ...")

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
