import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Prakiraan Cuaca Kalimantan Barat", layout="wide")
st.title("📡 Prakiraan Cuaca Kalimantan Barat dari GFS (Realtime via NOMADS)")
st.header("Visualisasi Curah Hujan, Suhu, Angin & Tekanan")

@st.cache_data
def load_dataset(run_date, run_hour):
    base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    ds = xr.open_dataset(base_url)
    return ds

# Sidebar
st.sidebar.title("⚙️ Pengaturan")

today = datetime.utcnow()
run_date = st.sidebar.date_input("Tanggal Run GFS (UTC)", today.date())
run_hour = st.sidebar.selectbox("Jam Run GFS (UTC)", ["00", "06", "12", "18"])
forecast_hour = st.sidebar.slider("Jam ke depan", 0, 240, 0, step=1)
parameter = st.sidebar.selectbox("Parameter", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

if st.sidebar.button("🔎 Tampilkan Visualisasi"):
    try:
        ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
        st.success("Dataset berhasil dimuat.")
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        st.stop()

    is_contour = False
    is_vector = False

    # Ambil variabel berdasarkan parameter
    if "pratesfc" in parameter:
        var = ds["pratesfc"][forecast_hour, :, :] * 3600
        label = "Curah Hujan (mm/jam)"
        cmap = "Blues"
        vmin, vmax = 0, 50
    elif "tmp2m" in parameter:
        var = ds["tmp2m"][forecast_hour, :, :] - 273.15
        label = "Suhu (°C)"
        cmap = "coolwarm"
        vmin, vmax = -10, 35
    elif "ugrd10m" in parameter:
        u = ds["ugrd10m"][forecast_hour, :, :]
        v = ds["vgrd10m"][forecast_hour, :, :]
        speed = (u**2 + v**2)**0.5 * 1.94384  # knot
        var = speed
        label = "Kecepatan Angin (knot)"
        cmap = plt.cm.get_cmap("RdYlGn_r", 10)
        vmin, vmax = 0, 50
        is_vector = True
    elif "prmsl" in parameter:
        var = ds["prmslmsl"][forecast_hour, :, :] / 100
        label = "Tekanan Permukaan Laut (hPa)"
        cmap = "cool"
        vmin, vmax = 980, 1020
        is_contour = True
    else:
        st.warning("Parameter tidak dikenali.")
        st.stop()

    # Fokus pada Kalimantan Barat: lon 108-114, lat -1 s.d. 3
    var = var.sel(lat=slice(-1, 3), lon=slice(108, 114))
    if is_vector:
        u = u.sel(lat=slice(-1, 3), lon=slice(108, 114))
        v = v.sel(lat=slice(-1, 3), lon=slice(108, 114))

    # Buat plot
    fig = plt.figure(figsize=(8, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([108, 114, -1, 3], crs=ccrs.PlateCarree())

    lon2d, lat2d = np.meshgrid(var.lon, var.lat)

    valid_time = ds.time[forecast_hour].values
    valid_dt = pd.to_datetime(str(valid_time))
    valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    tstr = f"t+{forecast_hour:03d}"

    ax.set_title(f"{label} - Valid {valid_str}", loc="left", fontsize=10, fontweight="bold")
    ax.set_title(f"GFS {tstr}", loc="right", fontsize=10, fontweight="bold")

    if is_contour:
        cs = ax.contour(lon2d, lat2d, var.values,
                        levels=15, colors='black', linewidths=0.8,
                        transform=ccrs.PlateCarree())
        ax.clabel(cs, fmt="%d", colors='black', fontsize=8)
    else:
        im = ax.pcolormesh(lon2d, lat2d, var.values,
                           cmap=cmap, vmin=vmin, vmax=vmax,
                           transform=ccrs.PlateCarree())
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label(label)

        if is_vector:
            ax.quiver(lon2d[::5, ::5], lat2d[::5, ::5],
                      u.values[::5, ::5], v.values[::5, ::5],
                      transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

    # Tambahkan fitur peta
    ax.coastlines(resolution='10m', linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')

    st.pyplot(fig)
