import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO

# Konfigurasi halaman
st.set_page_config(page_title="Prakiraan Cuaca Kalimantan Barat", page_icon="🌦", layout="wide")

# Judul dan Identitas
st.title("📡 Prakiraan Cuaca Kalimantan Barat dari GFS (Realtime via NOMADS)")
st.markdown("**Vigris Pranadifo (M8TB_14.24.0016)**")
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

# Daftar kota utama Kalbar
kota_kalbar = {
    "Pontianak": (0.02, 109.33),
    "Singkawang": (0.9, 108.98),
    "Sambas": (1.4, 109.3),
    "Ketapang": (-1.8, 110.0),
    "Sintang": (0.07, 111.5),
    "Kapuas Hulu": (0.9, 113.9),
    "Sekadau": (0.02, 110.9),
    "Melawi": (0.1, 111.5)
}

if st.sidebar.button("🔎 Tampilkan Visualisasi"):
    try:
        ds = load_dataset(run_date.strftime("%Y%m%d"), run_hour)
        st.success("Dataset berhasil dimuat.")
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        st.stop()

    is_contour = False
    is_vector = False

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
        speed = (u**2 + v**2)**0.5 * 1.94384
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

    # Fokus Kalbar (margin aman agar tidak terpotong)
    lat_min, lat_max = -5, 4
    lon_min, lon_max = 107, 115
    var = var.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
    if is_vector:
        u = u.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))
        v = v.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    # Plot
    fig = plt.figure(figsize=(10, 7))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    lon2d, lat2d = np.meshgrid(var.lon, var.lat)

    valid_time = ds.time[forecast_hour].values
    valid_dt = pd.to_datetime(str(valid_time))
    valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
    tstr = f"t+{forecast_hour:03d}"

    ax.set_title(f"{label} - Valid {valid_str}", loc="left", fontsize=10, fontweight="bold")
    ax.set_title(f"GFS {tstr}", loc="right", fontsize=10, fontweight="bold")

    if is_contour:
        cs = ax.contour(lon2d, lat2d, var.values, levels=15, colors='black', linewidths=0.8, transform=ccrs.PlateCarree())
        ax.clabel(cs, fmt="%d", colors='black', fontsize=8)
    else:
        im = ax.pcolormesh(lon2d, lat2d, var.values, cmap=cmap, vmin=vmin, vmax=vmax, transform=ccrs.PlateCarree())
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
        cbar.set_label(label)

        if is_vector:
            ax.quiver(lon2d[::5, ::5], lat2d[::5, ::5], u.values[::5, ::5], v.values[::5, ::5],
                      transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

    # Tambahkan peta dasar
    ax.coastlines(resolution='10m', linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAND, facecolor='lightgray')

    # Tampilkan kota-kota utama
    for kota, (lat, lon) in kota_kalbar.items():
        ax.plot(lon, lat, marker='o', color='red', markersize=4, transform=ccrs.PlateCarree())
        ax.text(lon + 0.1, lat + 0.1, kota, fontsize=8, transform=ccrs.PlateCarree())

    # Tampilkan plot di Streamlit
    st.pyplot(fig)

    # Info tambahan
    st.markdown(f"""
    **Waktu Validasi:** {valid_str}  
    **Jam Prakiraan ke-:** {forecast_hour}  
    **Model:** GFS 0.25° via NOMADS  
    """)

    # Tombol unduh
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    st.download_button("💾 Unduh Gambar", buf.getvalue(), file_name=f"{parameter}_{tstr}.png", mime="image/png")
