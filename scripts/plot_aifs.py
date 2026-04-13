#!/usr/bin/env python3
"""
plot_aifs.py
Generates animated GIF of AIFS forecast for Southeast Asia domain.
Reads cycle time from CYLC_TASK_CYCLE_POINT environment variable.
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
from scipy.ndimage import gaussian_filter
import metpy.calc as mpcalc
from metpy.units import units
import imageio
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ==============================================================================
# CONFIGURATION — all settings come from config.py
# ==============================================================================
PROCESSED_DIR = config.PROCESSED_DIR
PLOTS_DIR     = config.PLOTS_DIR
STEPS         = config.STEPS
# ==============================================================================

DOMAIN = {
    "lat_min": -12, "lat_max": 23,
    "lon_min": 92,  "lon_max": 127
}

WIND_LEVEL  = 700
LOW_LEVEL   = 850
UPPER_LEVEL = 200

SIGMA_CONV = 8
SIGMA_DIV  = 8
SIGMA_RAIN = 1.5
SIGMA_RH   = 15
SIGMA_T    = 4

RAIN_LEVELS = [0, 1, 5, 10, 15, 20, 30, 50, 75, 100, 150]
RAIN_COLORS = [
    "#ffffff", "#c8f0c8", "#64c864", "#009000",
    "#f0f000", "#e0a000", "#ff6000", "#ff0000",
    "#c00000", "#800000", "#ff00ff",
]
RAIN_CMAP = mcolors.ListedColormap(RAIN_COLORS)
RAIN_CMAP.set_over("#8000ff")
RAIN_NORM = mcolors.BoundaryNorm(RAIN_LEVELS, RAIN_CMAP.N)

PRECIP_SHADE_MIN = 1.0
CONV_PERCENTILE  = 88
DIV_PERCENTILE   = 85

COLOR_RH   = "#640888"
COLOR_CONV = "#ff3b30"
COLOR_DIV  = "#0066cc"
COLOR_TEMP = "#00a8a8"

LW_ALL = 1.6
LW_RH  = 1.2

ALPHA_CONV = 0.90
ALPHA_DIV  = 0.95
ALPHA_TEMP = 0.98

os.makedirs(PLOTS_DIR, exist_ok=True)


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


def standardize_coords(ds):
    rename_dict = {}
    if "latitude" in ds.coords:
        rename_dict["latitude"] = "lat"
    if "longitude" in ds.coords:
        rename_dict["longitude"] = "lon"
    if rename_dict:
        ds = ds.rename(rename_dict)
    return ds


def subset_domain(ds):
    ds = standardize_coords(ds).sortby("lat").sortby("lon")
    return ds.sel(
        lat=slice(DOMAIN["lat_min"], DOMAIN["lat_max"]),
        lon=slice(DOMAIN["lon_min"], DOMAIN["lon_max"])
    )


def get_level_coord(da):
    if "level" in da.coords:
        return "level"
    elif "isobaricInhPa" in da.coords:
        return "isobaricInhPa"
    raise KeyError("No pressure-level coordinate found")


def squeeze_time(da):
    if "time" in da.dims:
        da = da.isel(time=0)
    return da.squeeze()


def get_level_var(ds, var_name, level):
    da  = ds[var_name]
    lev = get_level_coord(da)
    return squeeze_time(da.sel({lev: level}))


def get_2d_var(ds, var_name):
    return squeeze_time(ds[var_name])


def smooth(arr, sigma):
    return gaussian_filter(arr, sigma=sigma)


def compute_div(u_da, v_da):
    lon = u_da["lon"].values
    lat = u_da["lat"].values
    dx, dy = mpcalc.lat_lon_grid_deltas(lon, lat)
    u_q = u_da.values * units("m/s")
    v_q = v_da.values * units("m/s")
    div = mpcalc.divergence(u_q, v_q, dx=dx, dy=dy).magnitude
    if div.shape != u_da.shape:
        out = np.full(u_da.shape, np.nan)
        out[:div.shape[0], :div.shape[1]] = div
        return out
    return div


def compute_rh_from_q_t(q_da, t_da, pressure_hpa=850):
    q_unit = q_da.values * units("kg/kg")
    t_unit = t_da.values * units.kelvin
    p_unit = pressure_hpa * 100 * units.pascal
    rh     = mpcalc.relative_humidity_from_specific_humidity(p_unit, t_unit, q_unit)
    return rh.to("dimensionless").magnitude * 100.0


def prepare(ds, prev_ds, lead_hours, init_str):
    ds = subset_domain(ds)

    uw   = get_level_var(ds, "u", WIND_LEVEL)
    vw   = get_level_var(ds, "v", WIND_LEVEL)
    u850 = get_level_var(ds, "u", LOW_LEVEL)
    v850 = get_level_var(ds, "v", LOW_LEVEL)
    u200 = get_level_var(ds, "u", UPPER_LEVEL)
    v200 = get_level_var(ds, "v", UPPER_LEVEL)

    # 6h accumulated precipitation
    tp_curr = get_2d_var(ds, "tp")
    if prev_ds is not None:
        prev_ds_sub = subset_domain(prev_ds)
        tp_prev     = get_2d_var(prev_ds_sub, "tp")
        rain        = smooth((tp_curr - tp_prev).values, SIGMA_RAIN)
    else:
        rain = smooth(tp_curr.values, SIGMA_RAIN)

    try:
        t850_raw = get_level_var(ds, "t", LOW_LEVEL)
        t850     = smooth(t850_raw.values, SIGMA_T)
    except Exception:
        t850_raw = None
        t850     = None

    try:
        q850_raw = get_level_var(ds, "q", LOW_LEVEL)
    except Exception:
        q850_raw = None

    rh850 = None
    if q850_raw is not None and t850_raw is not None:
        try:
            rh850 = compute_rh_from_q_t(q850_raw, t850_raw, pressure_hpa=850)
            rh850 = smooth(rh850, SIGMA_RH)
        except Exception:
            rh850 = None

    div850 = compute_div(u850, v850)
    div200 = compute_div(u200, v200)

    init_dt   = np.datetime64(init_str)
    valid_dt  = init_dt + np.timedelta64(lead_hours, "h")
    valid_str = str(valid_dt).replace("T", " ")

    return {
        "lon":        ds["lon"].values,
        "lat":        ds["lat"].values,
        "u":          uw.values,
        "v":          vw.values,
        "t":          t850,
        "rh":         rh850,
        "conv":       smooth(-div850, SIGMA_CONV),
        "div":        smooth(div200,  SIGMA_DIV),
        "rain":       rain,
        "valid_time": valid_str,
        "lead":       lead_hours,
        "init":       init_str,
    }


def base(ax):
    ax.set_extent([
        DOMAIN["lon_min"], DOMAIN["lon_max"],
        DOMAIN["lat_min"], DOMAIN["lat_max"]
    ], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND,  facecolor="#f2efe9")
    ax.add_feature(cfeature.OCEAN, facecolor="#eff3f6")
    ax.coastlines(resolution="50m", linewidth=0.9)
    ax.add_feature(cfeature.BORDERS, linestyle=":", linewidth=0.6)
    gl = ax.gridlines(draw_labels=True, alpha=0.3, linestyle="--", linewidth=0.4)
    gl.top_labels   = False
    gl.right_labels = False


def plot_frame(d):
    fig, ax = plt.subplots(
        1, 1, figsize=(10, 8),
        subplot_kw={"projection": ccrs.PlateCarree()}
    )
    base(ax)
    lon, lat = d["lon"], d["lat"]
    cf = None

    if d["rain"] is not None:
        rain_max = np.nanmax(d["rain"])
        if np.isfinite(rain_max) and rain_max >= PRECIP_SHADE_MIN:
            rain_plot = np.ma.masked_less(d["rain"], PRECIP_SHADE_MIN)
            cf = ax.contourf(
                lon, lat, rain_plot,
                levels=RAIN_LEVELS, cmap=RAIN_CMAP, norm=RAIN_NORM,
                extend="max", transform=ccrs.PlateCarree()
            )

    if d["rh"] is not None:
        rh_max = np.nanmax(d["rh"])
        if np.isfinite(rh_max) and rh_max >= 80:
            rh_cs = ax.contour(
                lon, lat, d["rh"],
                levels=np.arange(80, 100, 10),
                colors=COLOR_RH, linewidths=LW_RH,
                transform=ccrs.PlateCarree()
            )
            ax.clabel(rh_cs, fmt="%d%%", fontsize=6)

    conv_thr = np.nanpercentile(d["conv"], CONV_PERCENTILE)
    conv_max = np.nanmax(d["conv"])
    if np.isfinite(conv_thr) and np.isfinite(conv_max) and conv_max > conv_thr:
        conv_cs = ax.contour(
            lon, lat, d["conv"],
            levels=[conv_thr], colors=COLOR_CONV,
            linestyles="dashed", linewidths=LW_ALL,
            alpha=ALPHA_CONV, transform=ccrs.PlateCarree()
        )
        ax.clabel(conv_cs, fmt="L-CONV", fontsize=7)

    div_thr = np.nanpercentile(d["div"], DIV_PERCENTILE)
    div_max = np.nanmax(d["div"])
    if np.isfinite(div_thr) and np.isfinite(div_max) and div_max > div_thr:
        div_cs = ax.contour(
            lon, lat, d["div"],
            levels=[div_thr], colors=COLOR_DIV,
            linestyles="dashdot", linewidths=LW_ALL,
            alpha=ALPHA_DIV, transform=ccrs.PlateCarree()
        )
        ax.clabel(div_cs, fmt="U-DIV", fontsize=7)

    if d["t"] is not None:
        tmin = np.nanmin(d["t"])
        tmax = np.nanmax(d["t"])
        if np.isfinite(tmin) and np.isfinite(tmax) and tmax > tmin:
            t_levels = np.arange(280, 321, 4)
            t_levels = t_levels[
                (t_levels >= np.floor(tmin)) & (t_levels <= np.ceil(tmax))
            ]
            if len(t_levels) >= 1:
                t_cs = ax.contour(
                    lon, lat, d["t"],
                    levels=t_levels, colors=COLOR_TEMP,
                    linestyles="dotted", linewidths=LW_ALL,
                    alpha=ALPHA_TEMP, transform=ccrs.PlateCarree()
                )
                ax.clabel(t_cs, fmt="%dK", fontsize=6)

    ax.streamplot(
        lon[::2], lat[::2],
        d["u"][::2, ::2], d["v"][::2, ::2],
        density=0.4, linewidth=0.4, color="black"
    )

    if cf is not None:
        cax = fig.add_axes([0.92, 0.15, 0.02, 0.70])
        cb  = fig.colorbar(cf, cax=cax, ticks=RAIN_LEVELS)
        cb.set_label("Total Precipitation (mm)")

    ax.set_title(
        f"AIFS | Init {d['init']} UTC | Valid {d['valid_time']} UTC | Lead +{d['lead']}h",
        fontsize=10
    )
    fig.suptitle("AIFS Forecast — SE Asia", fontsize=13)
    plt.tight_layout(rect=[0, 0, 0.91, 1])

    fig.canvas.draw()
    frame = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    frame = frame.reshape(fig.canvas.get_width_height()[::-1] + (4,))
    frame = frame[:, :, :3]
    plt.close(fig)
    return frame


def main():
    init_time  = get_cycle_time()
    cycle_hour = init_time.hour
    base_name  = f"aifs_{init_time.strftime('%Y-%m-%d')}_{cycle_hour:02d}z"
    init_str   = f"{init_time.strftime('%Y-%m-%d')}T{cycle_hour:02d}:00"
    gif_path   = os.path.join(PLOTS_DIR, f"{base_name}.gif")

    print("=" * 60)
    print(" AIFS Real-Time Plot Script")
    print(f" Cycle: {init_time}")
    print("=" * 60)

    if os.path.exists(gif_path):
        print(f"GIF already exists for cycle {base_name}, skipping.")
        return

    steps  = list(range(6, 174, 6))
    frames = []

    # Load step 0 as baseline for tp differencing
    nc_step0 = os.path.join(PROCESSED_DIR, f"{base_name}-out-0.nc")
    prev_ds  = xr.open_dataset(nc_step0) if os.path.exists(nc_step0) else None

    for step in steps:
        nc_path = os.path.join(PROCESSED_DIR, f"{base_name}-out-{step}.nc")
        if not os.path.exists(nc_path):
            print(f"Missing: {nc_path}, skipping")
            continue

        print(f"Plotting lead +{step}h ...", flush=True)
        ds    = xr.open_dataset(nc_path)
        d     = prepare(ds, prev_ds, step, init_str)
        prev_ds = xr.open_dataset(nc_path)
        ds.close()

        frame = plot_frame(d)
        frames.append(frame)

    if not frames:
        print("No frames to animate!")
        return

    print(f"\nSaving GIF ({len(frames)} frames) → {gif_path}")
    imageio.mimsave(gif_path, frames, fps=2, loop=0)

    print("\n" + "=" * 60)
    print(f" Plot complete!")
    print(f" GIF saved to: {gif_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
