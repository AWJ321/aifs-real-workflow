# AIFS Real-Time Workflow

Real-time AI weather forecasting pipeline running on HPC cluster using Cylc 8 and PBS.

Every 6 hours:
1. Downloads latest ECMWF AIFS forecast from ECMWF open data
2. Converts GRIB2 to per-lead-time NetCDF files
3. Generates animated GIF and individual PNG frames of SE Asia weather forecast

---

## Repository Structure

    aifs-real-workflow/
    |-- aifs_rt/
    |   |-- flow.cylc              # Cylc workflow scheduling
    |-- scripts/
    |   |-- config.py              # All configuration — edit this first
    |   |-- detect_start.py        # Detects latest available AIFS cycle
    |   |-- detect_oldest.py       # Detects oldest available AIFS cycle
    |   |-- download_aifs.py       # Downloads AIFS GRIB2 from ECMWF open data
    |   |-- process_aifs.py        # Converts GRIB2 to per-lead-time NetCDF
    |   |-- plot_aifs.py           # Generates forecast GIF and PNG frames
    |   |-- plot_precip_aifs.py    # Generates precipitation log-colorscale plots
    |   |-- plot_wind_aifs.py      # Generates wind speed and barb plots (925/850/700hPa)
    |-- bash/
    |   |-- download_aifs.sh
    |   |-- process_aifs.sh
    |   |-- plot_aifs.sh
    |   |-- wait_adaptive.sh
    |-- start_workflow.sh          # Main entry point
    |-- config.py                  # All paths and settings — edit this first

---

## Prerequisites

- Cylc 8.5+
- PBS job scheduler
- Conda/Miniforge

---

## Setup

### 1. Clone the repository into your storage directory

    cd /data/projects/17001770/weather_department/nwp/wjang
    git clone https://github.com/AWJ321/aifs-real-workflow.git aifs_rt
    cd aifs_rt

### 2. Edit config.py

Open config.py and update:

    USER = "your_username"
    BASE_DIR = "/data/projects/17001770/weather_department/nwp/wjang/aifs_rt"
    PBS_PROJECT = "17001770"
    PLATFORM = "aspire"

### 3. Create data directories

    source /app/apps/miniforge3/25.3.1/etc/profile.d/conda.sh
    conda activate aifs_rt_env
    python -c "
    import sys; sys.path.insert(0, '/data/projects/17001770/weather_department/nwp/wjang/aifs_rt')
    import config, os
    for d in [config.RAW_DIR, config.PROCESSED_DIR, config.PLOTS_DIR,
              config.PLOTS_GIF_DIR, config.PLOTS_FRAMES_DIR, config.LOG_DIR]:
        os.makedirs(d, exist_ok=True)
        print(f'Created: {d}')
    "

### 4. Create conda environment and install packages

    source /app/apps/miniforge3/25.3.1/etc/profile.d/conda.sh
    conda create -n aifs_rt_env python=3.11 -y
    conda activate aifs_rt_env
    pip install cylc-flow
    pip install ecmwf-opendata
    pip install xarray cfgrib netCDF4 scipy numpy pandas
    pip install metpy cartopy matplotlib imageio tqdm

### 5. Set up Cylc platform configuration

Create ~/.cylc/flow/global.cylc:

    mkdir -p ~/.cylc/flow
    cat > ~/.cylc/flow/global.cylc << EOF
    [platforms]
        [[aspire]]
            hosts = localhost
            job runner = pbs
            install target = localhost
            cylc path = /home/users/gov/nea/YOUR_USERNAME/.conda/envs/aifs_rt_env/bin
    EOF

Replace YOUR_USERNAME with your actual username.

---

## Running the Workflow

    bash /data/projects/17001770/weather_department/nwp/wjang/aifs_rt/start_workflow.sh

### Monitor

    cylc tui aifs_rt
    qstat -u your_username

### Stop

    cylc stop --kill aifs_rt

---

## After System Maintenance / Server Restart

The workflow does not restart automatically after maintenance. To restart manually:

### 1. Restart the workflow

    conda activate aifs_rt_env
    bash /data/projects/17001770/weather_department/nwp/wjang/aifs_rt/start_workflow.sh

start_workflow.sh automatically:
- Detects oldest available AIFS data (ECMWF open data only keeps last few days)
- Finds the last completed cycle from data/plots/gif/
- If last completed cycle is older than oldest available: starts from oldest available
- If last completed cycle is within available range: starts from there + 6h
- Runs missed cycles back to back with no waiting
- Resumes normal operation once caught up to latest available data

### 2. Monitor catch-up progress

    cylc tui aifs_rt

### 3. Verify catch-up completed

    cat /data/projects/17001770/weather_department/nwp/wjang/aifs_rt/caught_up.txt

This file is written when the workflow reaches the latest available data.
Once it exists, normal scheduling resumes.

---

## Scheduling Logic

Catch-up cycles — if missed cycles exist, runs all back to back immediately with no waiting
New Cycle 1   — latest available data, downloads immediately
New Cycle 2   — starts immediately after Cycle 1, probes every 10 min for up to 7h
New Cycle 3   — starts immediately after Cycle 2, probes every 10 min for up to 7h, records data availability duration
New Cycle 4+  — waits (measured duration - 30 min), then probes every 10 min for 2h

Data availability duration measured in Cycle 3 is saved to data_availability_duration.txt
If file already exists it is not overwritten — preserved across restarts
ECMWF open data typically keeps last 3-5 days — cycles older than this cannot be caught up

---

## Output

    data/plots/
    |-- gif/
    |   |-- aifs_YYYY-MM-DD_HHz.gif
    |-- frames/
    |   |-- aifs_YYYY-MM-DD_HHz/
    |       |-- aifs_YYYY-MM-DD_HHz-lead-006h.png
    |       |-- ... (28 files)
    data/plots_precip/
    |-- gif/
    |   |-- aifs_precip_aifs_YYYY-MM-DD_HHz.gif
    |-- frames/
    |   |-- aifs_YYYY-MM-DD_HHz/ (28 files)
    data/plots_wind/
    |-- gif/
    |   |-- aifs_wind925hPa_aifs_YYYY-MM-DD_HHz.gif
    |   |-- aifs_wind850hPa_aifs_YYYY-MM-DD_HHz.gif
    |   |-- aifs_wind700hPa_aifs_YYYY-MM-DD_HHz.gif
    |-- frames/
        |-- 925hPa/aifs_YYYY-MM-DD_HHz/ (28 files)
        |-- 850hPa/aifs_YYYY-MM-DD_HHz/ (28 files)
        |-- 700hPa/aifs_YYYY-MM-DD_HHz/ (28 files)

Download GIFs to local machine:

    scp your_username@aspire2a.nscc.sg:/data/projects/17001770/weather_department/nwp/wjang/aifs_rt/data/plots/gif/*.gif C:\Users\your_username\Desktop\

---

## PBS Resources

    Task             CPUs   GPUs   RAM     Walltime   Queue
    download_aifs     1      0      8gb     8h         normal
    process_aifs      1      0     32gb     1h         normal
    plot_aifs         1      0     32gb     1h         normal
    wait_adaptive     1      0      1gb     10h        normal

---

## Troubleshooting

Check logs:

    find ~/cylc-run/aifs_rt -name "job.out" | sort
    cat ~/cylc-run/aifs_rt/run1/log/job/CYCLE_POINT/TASK/01/job.out

Common issues:
- Download fails with 404: data older than ECMWF open data retention period, start_workflow.sh will automatically use oldest available instead
- CYLC_WORKFLOW_INITIAL_CYCLE_POINT not set: fallback used, workflow still runs correctly
- PBS queue wait times can be long during peak hours
- Never run start_workflow.sh multiple times without stopping the previous run first
- If caught_up.txt exists from a previous run, start_workflow.sh deletes it automatically
