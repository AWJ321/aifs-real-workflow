#!/usr/bin/env python3
"""
process_aifs.py
Converts downloaded AIFS GRIB2 into per-lead-time NetCDF files.
Reads cycle time from CYLC_TASK_CYCLE_POINT environment variable.
"""

import os
import sys
import re
import numpy as np
import xarray as xr
import cfgrib
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ==============================================================================
# CONFIGURATION — all settings come from config.py
# ==============================================================================
RAW_DIR       = config.RAW_DIR
PROCESSED_DIR = config.PROCESSED_DIR
STEPS         = config.STEPS
# ==============================================================================

RENAME_MAP = {
    "u10": "10u",
    "v10": "10v",
    "u100": "100u",
    "v100": "100v",
    "t2m": "2t",
    "d2m": "2d",
}

UNIT_MAP = {
    "u": "m s-1", "v": "m s-1", "w": "Pa s-1",
    "10u": "m s-1", "10v": "m s-1",
    "100u": "m s-1", "100v": "m s-1",
    "t": "K", "2t": "K", "2d": "K",
    "z": "m2 s-2", "q": "kg kg-1",
    "tp": "m", "cp": "m", "sf": "m",
    "msl": "Pa", "sp": "Pa",
}


def get_cycle_time():
    """Read cycle time from Cylc environment variable."""
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


def load_grib(grib_path):
    print(f"Reading GRIB2: {grib_path}", flush=True)
    datasets = cfgrib.open_datasets(grib_path)
    print(f"Found {len(datasets)} datasets", flush=True)
    return datasets


def extract_step(datasets, step_hours):
    step_td = np.timedelta64(step_hours, 'h')
    merged  = xr.Dataset()

    for ds in datasets:
        if "step" not in ds.dims:
            if step_hours == 0:
                for var in ds.data_vars:
                    merged[var + "_orog"] = ds[var]
            continue

        if step_td not in ds.step.values:
            continue

        ds_step = ds.sel(step=step_td)

        coords_to_drop = [c for c in ["step", "valid_time", "heightAboveGround",
                                       "meanSea", "surface"] if c in ds_step.coords]
        ds_step = ds_step.drop_vars(coords_to_drop)

        rename = {k: v for k, v in RENAME_MAP.items() if k in ds_step.data_vars}
        if rename:
            ds_step = ds_step.rename(rename)

        merged = xr.merge([merged, ds_step], compat="override")

    return merged


def save_netcdf(ds, out_path, step_hours, init_time):
    for var in ds.data_vars:
        base = re.match(r"([a-zA-Z]+)", var)
        base = base.group(1) if base else var
        ds[var].attrs["units"] = UNIT_MAP.get(var, UNIT_MAP.get(base, "unknown"))

    ds.attrs["init_time"]  = str(init_time)
    ds.attrs["lead_hours"] = step_hours
    ds.attrs["source"]     = "ECMWF AIFS open data"
    ds.attrs["grid"]       = "0.25 degree global"

    ds.to_netcdf(out_path)
    print(f"Saved: {out_path}", flush=True)


def main():
    init_time = get_cycle_time()
    date_str  = init_time.strftime("%Y%m%d")
    cycle_hour = init_time.hour

    print("=" * 60)
    print(" AIFS Process Script")
    print(f" Init time : {init_time}")
    print("=" * 60)

    os.makedirs(PROCESSED_DIR, exist_ok=True)

    grib_name = f"aifs_{init_time.strftime('%Y-%m-%d')}_{cycle_hour:02d}z.grib2"
    grib_path = os.path.join(RAW_DIR, grib_name)

    if not os.path.exists(grib_path):
        raise FileNotFoundError(f"GRIB2 not found: {grib_path}")

    base_name = f"aifs_{init_time.strftime('%Y-%m-%d')}_{cycle_hour:02d}z"
    init_str  = f"{init_time.strftime('%Y-%m-%d')}T{cycle_hour:02d}:00"

    datasets = load_grib(grib_path)

    for step_hours in STEPS:
        out_name = f"{base_name}-out-{step_hours}.nc"
        out_path = os.path.join(PROCESSED_DIR, out_name)

        if os.path.exists(out_path):
            print(f"Already exists, skipping: {out_name}", flush=True)
            continue

        print(f"Processing step {step_hours}h ...", flush=True)
        ds = extract_step(datasets, step_hours)

        if len(ds.data_vars) == 0:
            print(f"Warning: no data for step {step_hours}h, skipping", flush=True)
            continue

        save_netcdf(ds, out_path, step_hours, init_str)

    print("=" * 60)
    print(f" Process complete!")
    print(f" Output: {PROCESSED_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
