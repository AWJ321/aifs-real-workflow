#!/usr/bin/env python3
"""
AIFS wind plot — filled speed + barbs at 925/850/700hPa.
Generates PNG frames and animated GIF per level per cycle.
"""

import os
import sys
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime
import imageio
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

PROCESSED_DIR = config.PROCESSED_DIR
GIF_DIR       = config.PLOTS_WIND_GIF_DIR
FRAMES_DIR    = config.PLOTS_WIND_FRAMES_DIR
DOMAIN        = {"lat_min": -12, "lat_max": 23, "lon_min": 92, "lon_max": 127}
LEVELS        = [925, 850, 700]
MS_TO_KT      = 1.94384
BARB_SKIP     = 5

WSPD_LEVELS = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
WSPD_COLORS = [
    "#d7f8f5", "#b3deee", "#c7f2bc", "#99e599",
    "#fffa85", "#fffa85", "#ffa06e", "#e46565",
    "#ce1d3a", "#e379a1",
]
WSPD_CMAP = mcolors.ListedColormap(WSPD_COLORS)
WSPD_CMAP.set_over("#f4d4ed")
WSPD_NORM = mcolors.BoundaryNorm(WSPD_LEVELS, WSPD_CMAP.N)


def get_cycle_time():
    cp = os.environ.get("CYLC_TASK_CYCLE_POINT")
    if cp:
        try:
            return datetime.strptime(cp, "%Y%m%dT%H%MZ")
        except ValueError:
            pass
    return datetime(2026, 4, 13, 0)


def open_nc(fpath):
    return xr.open_dataset(fpath, decode_times=False)


def subset(ds):
    if "latitude" in ds.coords:
        ds = ds.rename({"latitude": "lat", "longitude": "lon"})
    return ds.sortby("lat").sortby("lon").sel(
        lat=slice(DOMAIN["lat_min"], DOMAIN["lat_max"]),
        lon=slice(DOMAIN["lon_min"], DOMAIN["lon_max"])
    )


def base(ax, title):
    ax.set_extent([DOMAIN["lon_min"], DOMAIN["lon_max"],
                   DOMAIN["lat_min"], DOMAIN["lat_max"]], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND,  facecolor="#f2efe9")
    ax.add_feature(cfeature.OCEAN, facecolor="#eff3f6")
    ax.coastlines(resolution="50m", linewidth=1.5)
    ax.add_feature(cfeature.BORDERS, linestyle=":", linewidth=0.6)
    gl = ax.gridlines(draw_labels=True, alpha=0.3, linestyle="--", linewidth=0.4)
    gl.top_labels   = False
    gl.right_labels = False
    ax.set_title(title, fontsize=10)


def plot_frame(base_name, step, level, ds, init_str):
    lat     = ds["lat"].values
    lon     = ds["lon"].values
    u_ms    = ds["u"].sel(isobaricInhPa=level).squeeze().values
    v_ms    = ds["v"].sel(isobaricInhPa=level).squeeze().values
    wspd_kt = np.sqrt(u_ms**2 + v_ms**2) * MS_TO_KT
    u_kt    = u_ms * MS_TO_KT
    v_kt    = v_ms * MS_TO_KT

    fig, ax = plt.subplots(1, 1, figsize=(10, 8),
                           subplot_kw={"projection": ccrs.PlateCarree()})
    base(ax, f"AIFS {level}hPa Wind | Init {init_str} | Lead +{step}h")

    cf = ax.contourf(
        lon, lat, wspd_kt,
        levels=WSPD_LEVELS, cmap=WSPD_CMAP, norm=WSPD_NORM,
        extend="max", transform=ccrs.PlateCarree()
    )
    ax.barbs(
        lon[::BARB_SKIP], lat[::BARB_SKIP],
        u_kt[::BARB_SKIP, ::BARB_SKIP], v_kt[::BARB_SKIP, ::BARB_SKIP],
        length=6, linewidth=0.3, transform=ccrs.PlateCarree()
    )

    cax = fig.add_axes([0.83, 0.05, 0.04, 0.90])
    cb  = fig.colorbar(cf, cax=cax, ticks=WSPD_LEVELS,
                       extend="max", extendrect=True)
    cb.set_label("Wind Speed (knots)", fontsize=9)
    cb.outline.set_linewidth(0.8)

    fig.suptitle(f"AIFS Forecast — {level}hPa Wind", fontsize=13)
    plt.tight_layout(rect=[0, 0, 0.83, 1])
    return fig


def main():
    init_time  = get_cycle_time()
    cycle_hour = init_time.hour
    base_name  = f"aifs_{init_time.strftime('%Y-%m-%d')}_{cycle_hour:02d}z"
    init_str   = f"{init_time.strftime('%Y-%m-%d')}T{cycle_hour:02d}:00"

    os.makedirs(GIF_DIR, exist_ok=True)

    print("=" * 60)
    print(" AIFS Wind Plot")
    print(f" Cycle: {init_time}")
    print("=" * 60)

    steps = list(range(6, 174, 6))

    for level in LEVELS:
        gif_path   = os.path.join(GIF_DIR, f"aifs_wind{level}hPa_{base_name}.gif")
        frames_dir = os.path.join(FRAMES_DIR, f"{level}hPa", base_name)
        os.makedirs(frames_dir, exist_ok=True)

        if os.path.exists(gif_path):
            print(f"GIF already exists for {level}hPa {base_name}, skipping.")
            continue

        gif_frames = []
        for step in steps:
            fname = f"{base_name}-out-{step}.nc"
            fpath = os.path.join(PROCESSED_DIR, fname)
            if not os.path.exists(fpath):
                continue

            print(f"Plotting {level}hPa lead +{step}h ...", flush=True)
            ds  = subset(open_nc(fpath))
            fig = plot_frame(base_name, step, level, ds, init_str)
            ds.close()

            png_path = os.path.join(frames_dir,
                                    f"aifs_wind{level}hPa_{base_name}-lead-{step:03d}h.png")
            fig.savefig(png_path, dpi=100, bbox_inches="tight")

            fig.canvas.draw()
            frame = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
            frame = frame.reshape(fig.canvas.get_width_height()[::-1] + (4,))[:, :, :3]
            plt.close(fig)
            gif_frames.append(frame)

        if gif_frames:
            print(f"Saving GIF → {gif_path}")
            imageio.mimsave(gif_path, gif_frames, fps=2, loop=0)

    print("=" * 60)
    print(" AIFS Wind plot complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
