#!/bin/bash
#PBS -N aifs_plot_precip
#PBS -P 17001770
#PBS -l select=1:ncpus=1:mem=32gb
#PBS -l walltime=01:00:00
#PBS -j oe
#PBS -q normal
#PBS -o /data/projects/17001770/weather_department/nwp/wjang/aifs_rt/logs/plot_precip_aifs.log

echo "=============================="
echo " AIFS Precip Plot Started"
echo " Host: $(hostname)"
echo " Time: $(date)"
echo "=============================="

source /app/apps/miniforge3/25.3.1/etc/profile.d/conda.sh
conda activate aifs_rt_env
export LD_PRELOAD=$CONDA_PREFIX/lib/libstdc++.so.6

/home/users/gov/nea/ang.wj/.conda/envs/aifs_rt_env/bin/python ${WORKFLOW_BASE_DIR}/scripts/plot_precip_aifs.py

EXIT_CODE=$?
echo "=============================="
echo " AIFS Precip Plot Finished"
echo " Exit code: $EXIT_CODE"
echo " Time: $(date)"
echo "=============================="
exit $EXIT_CODE
