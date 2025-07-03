import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Cuaca Kalimantan Barat", layout="wide")

st.title("📡 Prakiraan Cuaca Kalimantan Barat")
st.caption("Data GFS 0.25° dari NOMADS (NOAA) - Realtime")

@st.cache_data
def load_dataset(run_date, run_hour):
    base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    ds = xr.open_dataset(base_url)
    return ds

# Sidebar input
st.sidebar.title("⚙️ Pengaturan")
today = datetime.utcnow()
run_date = st.sidebar.date_input("Tanggal Run GFS (UTC)", today.date())
run_hour = st.sidebar.selectbox("Jam Run GFS (UTC)", ["00", "06", "12", "18"])
forecast_hour = st.sidebar.slider("Prakiraan ke depan (jam)", 0, 240, 0, step=1)
parameter = st.sidebar.selectbox("Pilih Parameter Cuaca", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

if st.sidebar.button("🔎 Tampilkan Visualisasi"):
    try:
        ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
        st.success("✅ Dataset berhasil dimuat")
    except Exception as e:
        st.error("❌ Gagal memuat data.")
        st.exception(e)
        st.stop()

    is_vector = False
    is_contour = False

    # Parameter spesifik
    if "pratesfc" in parameter:
        var = ds["pratesfc"][forecast_hour, :, :] * 3600
        label = "Curah Hujan (mm/jam)"
        cmap = "Blues"
        vmin, vmax = 0, 50
    elif "tmp2m" in parameter:
        var = ds["tmp2m"][forecast_hour, :, :] - 273.15
        label = "Suhu Permukaan (°C)"
        cmap = "coolwarm"
        vmin, vmax = 20, 35
    elif "ugrd10m" in parameter:
        u = ds["ugrd10m"][forecast_hour, :, :]
        v = ds["vgrd10m"][forecast_hour, :, :]
        speed = (u**2 + v**2)**0.5 * 1.94384  # m/s ke knot
        var = speed
        label = "Kecepatan Angin (knot)"
        cmap = "YlGnBu"
        is_vector = True
        vmin, vmax = 0, 40
    elif "prmsl" in parameter:
        var = ds["prmslmsl"][forecast_hour, :, :] / 100
        label = "Tekanan Permukaan Laut (hPa)"
        cmap = "viridis"
        is_contour = True
        vmin, vmax = 1000, 1020
    else:
        st.warning("Parameter tidak dikenali.")
        st.stop()

    # Fokus Kalimantan Barat
    lon_min, lon_max = 108, 114
    lat_min, lat_max = -1.5, 2.0
    var = var.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max))
    if is_vector:
        u = u.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max))
        v = v.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max))

    # Buat meshgrid
    lon2d, lat2d = np.meshgrid(var.lon, var.lat)

    # Plotting
    fig = plt.figure(figsize=(8, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    valid_time = ds.time[forecast_hour].values
    valid_dt = pd.to_datetime(str(valid_time))
    valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    tstr = f"t+{forecast_hour:03d}"

    ax.set_title(f"{label}\nValid {valid_str}", loc="left", fontsize=9, fontweight="bold")
    ax.set_title(f"GFS {tstr}", loc="right", fontsize=9)

    if is_contour:
        cs = ax.contour(lon2d, lat2d, var.values, levels=15, colors='black', linewidths=0.6)
        ax.clabel(cs, fmt="%.0f", fontsize=7)
    else:
        im = ax.pcolormesh(lon2d, lat2d, var.values,
                           cmap=cmap, vmin=vmin, vmax=vmax,
                           transform=ccrs.PlateCarree())
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label(label)

        if is_vector:
            lon_q, lat_q = np.meshgrid(var.lon[::3], var.lat[::3])
            ax.quiver(lon_q, lat_q,
                      u.values[::3, ::3], v.values[::3, ::3],
                      transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

    # Tambahan peta
    ax.coastlines(resolution='10m', linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.gridlines(draw_labels=True, linestyle="--", color="gray", alpha=0.5)

    st.pyplot(fig)

   
