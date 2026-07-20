#!/usr/bin/env python3
"""
Detects the oldest available AIFS forecast cycle point.
Works forwards from MAX_LOOKBACK_DAYS ago to find first available data.
Prints ONLY the cycle point in Cylc format: YYYYMMDDTHHmmZ
"""

import os
import sys
import tempfile
import contextlib
from datetime import datetime, timedelta
from ecmwf.opendata import Client

MAX_LOOKBACK_DAYS = 5

def get_oldest_cycle():
    # Start from MAX_LOOKBACK_DAYS ago and work forwards
    now     = datetime.utcnow()
    current = now.replace(
        hour=(now.hour // 6) * 6,
        minute=0, second=0, microsecond=0
    )

    max_steps = MAX_LOOKBACK_DAYS * 4

    # Work forwards from oldest to newest
    for i in range(max_steps, -1, -1):
        dt  = current - timedelta(hours=i * 6)
        tmp = tempfile.mktemp(suffix=".grib2")

        try:
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

            if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
                os.remove(tmp)
                # Found oldest available — print and exit
                sys.stdout.write(dt.strftime("%Y%m%dT%H%MZ") + "\n")
                sys.stdout.flush()
                return

        except Exception:
            pass
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    sys.stderr.write("ERROR: No AIFS data found in last {} days\n".format(MAX_LOOKBACK_DAYS))
    sys.exit(1)

if __name__ == "__main__":
    get_oldest_cycle()
