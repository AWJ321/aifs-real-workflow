#!/usr/bin/env python3
"""
Detects the latest available AIFS forecast cycle point.
Prints ONLY the cycle point in Cylc format: YYYYMMDDTHHmmZ
All other output is suppressed.
"""

import os
import sys
import tempfile
import contextlib
from datetime import datetime, timedelta
from ecmwf.opendata import Client

MAX_LOOKBACK_DAYS = 10

def get_latest_cycle():
    # Get current UTC time and round down to nearest 6h cycle
    now     = datetime.utcnow()
    current = now.replace(
        hour=(now.hour // 6) * 6,
        minute=0, second=0, microsecond=0
    )

    max_steps = MAX_LOOKBACK_DAYS * 4

    # Work backwards in time, one 6h cycle at a time
    for i in range(max_steps):
        dt  = current - timedelta(hours=i * 6)
        tmp = tempfile.mktemp(suffix=".grib2")

        try:
            # Try to download a tiny test file using AIFS opendata client
            # Request just 1 step and 1 param to minimise download size
            with open(os.devnull, 'w') as devnull:
                with contextlib.redirect_stdout(devnull):
                    with contextlib.redirect_stderr(devnull):
                        client = Client(source="ecmwf", model="aifs-single")
                        client.retrieve(
                            date=dt.strftime("%Y%m%d"),
                            time=dt.hour,
                            step=[0],
                            param=["2t"],
                            target=tmp,
                        )

            # If file exists and has data, this cycle point is confirmed available
            if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
                os.remove(tmp)
                sys.stdout.write(dt.strftime("%Y%m%dT%H%MZ") + "\n")
                sys.stdout.flush()
                return

        except Exception:
            # Not available yet, try previous cycle
            pass
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    sys.stderr.write("ERROR: No AIFS data found in last {} days\n".format(MAX_LOOKBACK_DAYS))
    sys.exit(1)

if __name__ == "__main__":
    get_latest_cycle()
