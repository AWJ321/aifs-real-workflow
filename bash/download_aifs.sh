#!/bin/bash
#PBS -N aifs_download
#PBS -P 17001770
#PBS -l select=1:ncpus=2:mem=8gb
#PBS -l walltime=08:00:00
#PBS -j oe
#PBS -o /data/projects/17001770/weather_department/nwp/wjang/aifs_rt/logs/download_aifs.log

echo "=============================="
echo " AIFS Download Started"
echo " Host: $(hostname)"
echo " Time: $(date)"
echo "=============================="

source /app/apps/miniforge3/25.3.1/etc/profile.d/conda.sh
conda activate aifs_rt_env
export LD_PRELOAD=$CONDA_PREFIX/lib/libstdc++.so.6

python ${WORKFLOW_BASE_DIR}/scripts/download_aifs.py

EXIT_CODE=$?

echo "=============================="
echo " AIFS Download Finished"
echo " Exit code: $EXIT_CODE"
echo " Time: $(date)"
echo "=============================="

exit $EXIT_CODE
