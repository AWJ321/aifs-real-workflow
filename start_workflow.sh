#!/bin/bash
# ==============================================================================
# AIFS Real-Time Workflow Starter
# Automatically catches up missed cycles after maintenance
# Finds oldest available data to maximise catch-up
# ==============================================================================

set -e

WORKFLOW_BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
export WORKFLOW_BASE_DIR
CYLC_WORKFLOW_DIR="$WORKFLOW_BASE_DIR/aifs_rt"
GIF_DIR="$WORKFLOW_BASE_DIR/data/plots/gif"

echo "=============================="
echo " AIFS Workflow Starter"
echo " Workflow dir: $WORKFLOW_BASE_DIR"
echo " Time: $(date -u)"
echo "=============================="

source /app/apps/miniforge3/25.3.1/etc/profile.d/conda.sh
conda activate aifs_rt_env
export LD_PRELOAD=$CONDA_PREFIX/lib/libstdc++.so.6

# Get latest available data
echo ""
echo "Detecting latest available AIFS data..."
LATEST_AVAILABLE=$(python $WORKFLOW_BASE_DIR/scripts/detect_start.py 2>/dev/null)
if [ -z "$LATEST_AVAILABLE" ]; then
    echo "ERROR: Could not detect latest available data. Exiting."
    exit 1
fi
echo "Latest available: $LATEST_AVAILABLE"

# Get oldest available data
echo "Detecting oldest available AIFS data..."
OLDEST_AVAILABLE=$(python $WORKFLOW_BASE_DIR/scripts/detect_oldest.py 2>/dev/null)
if [ -z "$OLDEST_AVAILABLE" ]; then
    echo "WARNING: Could not detect oldest available data, falling back to latest"
    OLDEST_AVAILABLE=$LATEST_AVAILABLE
fi
echo "Oldest available: $OLDEST_AVAILABLE"

# Check latest completed cycle from GIF files
LATEST_GIF=$(ls $GIF_DIR/aifs_*.gif 2>/dev/null | sort | tail -1)

if [ -z "$LATEST_GIF" ]; then
    echo ""
    echo "No existing GIFs found — starting fresh from $LATEST_AVAILABLE"
    START_FROM=$LATEST_AVAILABLE
else
    # Extract cycle point from GIF filename
    # aifs_2026-04-30_06z.gif → 20260430T0600Z
    BASENAME=$(basename $LATEST_GIF .gif)
    DATE_PART=$(echo $BASENAME | sed 's/aifs_//' | sed 's/z$//')
    DATE=$(echo $DATE_PART | cut -d'_' -f1 | tr -d '-')
    HOUR=$(echo $DATE_PART | cut -d'_' -f2)
    LAST_COMPLETED="${DATE}T${HOUR}00Z"

    echo ""
    echo "Last completed cycle: $LAST_COMPLETED"

    # Add 6h to get next cycle to run
    NEXT_EPOCH=$(date -u -d "${DATE:0:4}-${DATE:4:2}-${DATE:6:2}T${HOUR}:00:00Z + 6 hours" +%s)
    PROPOSED=$(date -u -d "@$NEXT_EPOCH" +"%Y%m%dT%H%MZ")
    echo "Proposed start     : $PROPOSED"

    # Convert oldest available to epoch for comparison
    OLDEST_DATE="${OLDEST_AVAILABLE:0:4}-${OLDEST_AVAILABLE:4:2}-${OLDEST_AVAILABLE:6:2}"
    OLDEST_HOUR="${OLDEST_AVAILABLE:9:2}"
    OLDEST_EPOCH=$(date -u -d "${OLDEST_DATE}T${OLDEST_HOUR}:00:00Z" +%s)

    if [ "$NEXT_EPOCH" -ge "$OLDEST_EPOCH" ]; then
        echo "Catch-up possible — starting from $PROPOSED"
        START_FROM=$PROPOSED
    else
        echo "Proposed start older than oldest available — starting from $OLDEST_AVAILABLE"
        START_FROM=$OLDEST_AVAILABLE
    fi
fi

# Clean any previous workflow state and caught_up.txt
echo ""
echo "Cleaning previous workflow run..."
cylc stop --now --now aifs_rt/run1 2>/dev/null || true
sleep 3
cylc clean aifs_rt --yes 2>/dev/null || true
rm -f $WORKFLOW_BASE_DIR/caught_up.txt

# Install and start
echo ""
echo "Installing workflow..."
cylc install $CYLC_WORKFLOW_DIR

echo ""
echo "Starting workflow from $START_FROM ..."
cylc play aifs_rt --initial-cycle-point $START_FROM

echo ""
echo "=============================="
echo " Workflow started successfully"
echo " Monitor with: cylc tui aifs_rt"
echo " Oldest available : $OLDEST_AVAILABLE"
echo " Latest available : $LATEST_AVAILABLE"
echo " Starting from    : $START_FROM"
echo "=============================="
