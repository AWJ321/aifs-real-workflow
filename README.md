# AIFS Real-Time Workflow

Real-time AI weather forecasting pipeline running on HPC cluster using Cylc 8 and PBS.

Every 6 hours:
1. Downloads latest ECMWF AIFS forecast from ECMWF open data
2. Converts GRIB2 to per-lead-time NetCDF files
3. Generates animated GIF of SE Asia weather forecast

---

## Repository Structure

    aifs-real-workflow/
    |-- aifs_rt/
    |   |-- flow.cylc              # Cylc workflow scheduling
    |-- scripts/
    |   |-- config.py              # All configuration — edit this first
    |   |-- detect_start.py        # Detects latest available AIFS cycle
    |   |-- download_aifs.py       # Downloads AIFS GRIB2 from ECMWF open data
    |   |-- process_aifs.py        # Converts GRIB2 to per-lead-time NetCDF
    |   |-- plot_aifs.py           # Generates forecast GIF animation
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
    for d in [config.RAW_DIR, config.PROCESSED_DIR, config.PLOTS_DIR, config.LOG_DIR]:
        os.makedirs(d, exist_ok=True)
        print(f'Created: {d}')
    "

### 4. Create conda environment

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

### Clean and restart

    cylc stop --kill aifs_rt
    cylc clean aifs_rt --yes
    bash start_workflow.sh

---

## Scheduling Logic

Cycle 1  — Starts immediately, data already confirmed available by detect_start.py
Cycle 2  — Starts immediately after Cycle 1 finishes, probes every 10 min for up to 7h
Cycle 3  — Starts immediately after Cycle 2 finishes, probes every 10 min for up to 7h, records data availability duration
Cycle 4+ — Waits (duration - 30 min) after previous cycle finishes, then probes every 10 min for 2h

---

## Output

Animated GIF files saved to:

    {BASE_DIR}/data/plots/aifs_YYYY-MM-DD_HHz.gif

Download to local machine:

    scp your_username@aspire2a.nscc.sg:/data/projects/17001770/weather_department/nwp/wjang/aifs_rt/data/plots/*.gif C:\Users\your_username\Desktop\

---

## PBS Resources

    Task             CPUs   GPUs   RAM     Walltime   Queue
    download_aifs     2      0      8gb     8h         normal
    process_aifs      4      0     32gb     1h         normal
    plot_aifs         4      0     32gb     1h         normal
    wait_adaptive     1      0      1gb     10h        normal

---

## Troubleshooting

Check logs:

    find ~/cylc-run/aifs_rt -name "job.out" | sort
    cat ~/cylc-run/aifs_rt/run1/log/job/CYCLE_POINT/TASK/01/job.out

