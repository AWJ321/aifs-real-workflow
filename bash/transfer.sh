#!/bin/bash
#PBS -N aifs_transfer
#PBS -P 17001770
#PBS -l select=1:ncpus=1:mem=4gb
#PBS -l walltime=00:30:00
#PBS -j oe
#PBS -q normal
#PBS -o /data/projects/17001770/weather_department/nwp/wjang/aifs_rt/logs/transfer.log

REMOTE="aramanathan@118.189.84.226"
REMOTE_BASE="/nas44/aramanathan/AI-NWP/RealTime/aifs"
LOCAL_BASE="/data/projects/17001770/weather_department/nwp/wjang/aifs_rt/data"

# Parse cycle point from Cylc
CYCLE_POINT=$CYLC_TASK_CYCLE_POINT
CYCLE_DATE="${CYCLE_POINT:0:4}-${CYCLE_POINT:4:2}-${CYCLE_POINT:6:2}"
CYCLE_HOUR="${CYCLE_POINT:9:2}"
AIFS_BASENAME="aifs_${CYCLE_DATE}_${CYCLE_HOUR}z"

echo "=============================="
echo " AIFS Transfer Started"
echo " Host: $(hostname)"
echo " Time: $(date)"
echo " Cycle: $AIFS_BASENAME"
echo "=============================="

# Transfer GIF
rsync -av $LOCAL_BASE/plots/gif/${AIFS_BASENAME}.gif \
    $REMOTE:$REMOTE_BASE/plots/gif/ 2>/dev/null || echo "No GIF found for $AIFS_BASENAME"

# Transfer frames
rsync -av $LOCAL_BASE/plots/frames/${AIFS_BASENAME}/     $REMOTE:$REMOTE_BASE/plots/frames/${AIFS_BASENAME}/ 2>/dev/null || echo "No frames found for $AIFS_BASENAME"
# Transfer precip plots
rsync -av $LOCAL_BASE/plots_precip/gif/aifs_precip_${AIFS_BASENAME}.gif     $REMOTE:$REMOTE_BASE/plots_precip/gif/ 2>/dev/null || echo "No precip GIF found for $AIFS_BASENAME"
rsync -av $LOCAL_BASE/plots_precip/frames/${AIFS_BASENAME}/     $REMOTE:$REMOTE_BASE/plots_precip/frames/${AIFS_BASENAME}/ 2>/dev/null || true
# Transfer wind plots
rsync -av $LOCAL_BASE/plots_wind/gif/aifs_wind925hPa_${AIFS_BASENAME}.gif     $REMOTE:$REMOTE_BASE/plots_wind/gif/ 2>/dev/null || true
rsync -av $LOCAL_BASE/plots_wind/gif/aifs_wind850hPa_${AIFS_BASENAME}.gif     $REMOTE:$REMOTE_BASE/plots_wind/gif/ 2>/dev/null || true
rsync -av $LOCAL_BASE/plots_wind/gif/aifs_wind700hPa_${AIFS_BASENAME}.gif     $REMOTE:$REMOTE_BASE/plots_wind/gif/ 2>/dev/null || true
rsync -av $LOCAL_BASE/plots_wind/frames/925hPa/${AIFS_BASENAME}/     $REMOTE:$REMOTE_BASE/plots_wind/frames/925hPa/${AIFS_BASENAME}/ 2>/dev/null || true
rsync -av $LOCAL_BASE/plots_wind/frames/850hPa/${AIFS_BASENAME}/     $REMOTE:$REMOTE_BASE/plots_wind/frames/850hPa/${AIFS_BASENAME}/ 2>/dev/null || true
rsync -av $LOCAL_BASE/plots_wind/frames/700hPa/${AIFS_BASENAME}/     $REMOTE:$REMOTE_BASE/plots_wind/frames/700hPa/${AIFS_BASENAME}/ 2>/dev/null || true

echo "=============================="
echo " AIFS Transfer Finished"
echo " Time: $(date)"
echo "=============================="
