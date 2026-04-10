import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import re
import base64

# Set Page Config
st.set_page_config(page_title="Dashboard Analisis Kemiskinan", page_icon="sigap_-removebg-preview.png", layout="wide")

# Custom CSS for modern styling (Mengacu pada warna screenshot)
st.markdown("""
    <style>
    /* Styling Streamlit Main Background */
    .css-18e3th9 {
        padding-top: 1rem;
    }
    .st-emotion-cache-1y4p8pa {
        padding: 2rem 1rem;
    }
    
    /* Custom Metric Cards */
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
        color: #333333;
    }
    .metric-value {
        font-size: 36px;
        font-weight: 800;
        color: #1f1f1f;
    }
    .metric-label {
        font-size: 16px;
        font-weight: bold;
        color: #555555;
        margin-bottom: 5px;
    }
    .metric-change {
        font-size: 14px;
        color: #2BB0A4; /* Teal color from image */
        font-weight: bold;
    }
    .metric-change.bad {
        color: #EA4380; /* Pink color from image */
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    ## Read Data
    df = pd.read_excel('Output_Nilai_RR_Per_KabKota.xlsx')
    gdf = gpd.read_file('peta_ntb_ntt.geojson')
    
    # Cleaning function mimicking R
    def clean_name(x):
        x = str(x).lower()
        x = re.sub(r'[^a-z0-9 ]', ' ', x)
        x = re.sub(r'\s+', ' ', x).strip()
        return x
    
    
    # Identitas kolom pada Excel mungkin berbeda (Kabupaten/Kota atau KabupatenKota)
    kab_col = 'Kabupaten/Kota' if 'Kabupaten/Kota' in df.columns else 'KabupatenKota'
    df['kab_key'] = df[kab_col].apply(clean_name)
    
    # Merge geometries
    merged_gdf = gdf[['kab_key', 'ADM1_EN', 'ADM2_EN', 'geometry']].merge(df, on='kab_key', how='inner')
    return df, merged_gdf, kab_col, gdf

df, merged_gdf, kab_col, gdf_full = load_data()

# Custom CSS for the new Banner Header
st.markdown("""
    <style>
    .top-banner {
        background-color: #2b2b36;
        padding: 30px 30px 60px 30px;
        border-radius: 15px;
        margin-bottom: 20px;
        margin-top: -30px;
    }
    .banner-title {
        display: flex;
        align-items: center;
        margin-bottom: 30px;
    }
    .cards-row {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        /* Pull cards upwards to overlap the banner */
        margin-bottom: -80px; 
    }
    .metric-card-custom {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px 15px;
        flex: 1;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        border: 1px solid #f0f0f0;
    }
    .metric-label-custom {
        font-size: 16px;
        font-weight: 700;
        color: #1f1f1f;
        margin-bottom: 8px;
    }
    .metric-value-custom {
        font-size: 34px;
        font-weight: 800;
        color: #000000;
        margin-bottom: 5px;
    }
    .metric-change-custom {
        font-size: 15px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Filters Sidebar
st.sidebar.markdown("### ⚙️ Filter Data")
years = sorted(df['Tahun'].unique())
year_options = ['Semua'] + [str(y) for y in years]
selected_year_opt = st.sidebar.selectbox("Pilih Tahun:", year_options)
# Optional Province Filter using ADM1_EN
provinsi = ['Semua', 'Nusa Tenggara Barat', 'Nusa Tenggara Timur']
selected_prov = st.sidebar.selectbox("Pilih Provinsi:", provinsi)

# Filter Data Logic
if selected_year_opt == 'Semua':
    df_filtered = df.copy()
    gdf_filtered = merged_gdf.copy()
    year_label = "Tahun 2020 - 2024"
else:
    selected_year = int(selected_year_opt)
    df_filtered = df[df['Tahun'] == selected_year]
    gdf_filtered = merged_gdf[merged_gdf['Tahun'] == selected_year]
    year_label = f"Tahun {selected_year}"

if selected_prov != 'Semua':
    # Kita butuh merge region dari geodataframe back to df untuk filter.
    # Karena gdf_filtered punya ADM2_EN, kita mapping prov.
    prov_dict = merged_gdf[['kab_key']].copy()
    # Mengambil ADM1_EN manual:
    temp_gdf = gpd.read_file('peta_ntb_ntt.geojson')
    temp_gdf['kab_key'] = temp_gdf['ADM2_EN'].apply(lambda x: re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', str(x).lower())).strip())
    
    # Join the province data to our dataframes (if we don't have it)
    valid_kabs = temp_gdf[temp_gdf['ADM1_EN'] == selected_prov]['kab_key'].tolist()
    
    df_filtered = df_filtered[df_filtered['kab_key'].isin(valid_kabs)]
    gdf_filtered = gdf_filtered[gdf_filtered['kab_key'].isin(valid_kabs)]

# Total daerah dari GeoJSON (seluruh 32 kabupaten/kota, bukan hanya yang masuk model)
if selected_prov != 'Semua':
    total_all_daerah = len(gdf_full[gdf_full['ADM1_EN'] == selected_prov])
else:
    total_all_daerah = len(gdf_full)

# Metric Computation
rata_ppm = df_filtered['PPM'].mean()
if len(df_filtered) > 0:
    # Untuk "Semua", ambil rata-rata RR per daerah lalu cari max
    if selected_year_opt == 'Semua':
        avg_rr = df_filtered.groupby(kab_col).agg({'RR': 'mean', 'PPM': 'mean'}).reset_index()
        max_rr_row = avg_rr.loc[avg_rr['RR'].idxmax()]
        keparahan = len(avg_rr[avg_rr['RR'] > 1.0])
    else:
        max_rr_row = df_filtered.loc[df_filtered['RR'].idxmax()]
        keparahan = len(df_filtered[df_filtered['RR'] > 1.0])
else:
    rata_ppm = 0
    max_rr_row = {kab_col: '-', 'RR': 0, 'PPM': 0}
    keparahan = 0
    
total_daerah = len(df_filtered[kab_col].unique()) if len(df_filtered) > 0 else 0

kab_name = str(max_rr_row[kab_col]).title() if len(df_filtered) > 0 else "-"
rr_val = float(max_rr_row['RR']) if len(df_filtered) > 0 else 0.0
ppm_val = float(max_rr_row['PPM']) if len(df_filtered) > 0 else 0.0
# Load the logo image and encode it as base64
with open("sigap_-removebg-preview.png", "rb") as img_file:
    sigap_base64 = base64.b64encode(img_file.read()).decode()

# Render Integrated Banner & Cards
st.markdown(f"""
<div class="top-banner">
    <div class="banner-title" style="display: flex; align-items: center;">
        <img src="data:image/png;base64,{sigap_base64}" style="height: 65px; transform: scale(2.8); transform-origin: center left; margin-left: -20px; margin-right: 120px; object-fit: contain;" alt="Logo Sigap">
        <div style="height: 55px; border-left: 3px solid rgba(255, 255, 255, 0.7); margin-right: 25px;"></div>
        <span style="color: white; font-weight: bold; font-size: 42px; letter-spacing: 0.5px;">Dashboard Analisis Spasial Kemiskinan</span>
    </div>
    <div class="cards-row">
        <div class="metric-card-custom">
            <div class="metric-label-custom">Total Rata-rata PPM</div>
            <div class="metric-value-custom">{rata_ppm:.2f}%</div>
            <div class="metric-change-custom" style="color: #EA4380;">{year_label}</div>
        </div>
        <div class="metric-card-custom">
            <div class="metric-label-custom">Daerah Risiko Bencana (Tertinggi)</div>
            <div class="metric-value-custom">{rr_val:.2f}</div>
            <div class="metric-change-custom" style="color: #2BB0A4;">{kab_name} (PPM: {ppm_val:.2f}%)</div>
        </div>
        <div class="metric-card-custom">
            <div class="metric-label-custom">Total Daerah Berisiko Tinggi</div>
            <div class="metric-value-custom">{keparahan}</div>
            <div class="metric-change-custom" style="color: #555555;">Dari {total_all_daerah} Kabupaten/Kota</div>
        </div>
    </div>
</div>
<br><br><br> <!-- Spacer to account for negative margin overlapping -->
""", unsafe_allow_html=True)

# Charts Section
row2_col1, row2_col2 = st.columns((7, 3))

with row2_col1:
    with st.container(border=True):
        st.markdown("#### 🗺️ Peta Relative Risk (RR)")
        if len(gdf_filtered) > 0:
            # Jika Semua, rata-ratakan RR & PPM per daerah
            if selected_year_opt == 'Semua':
                gdf_avg = gdf_filtered.dissolve(by='kab_key', aggfunc={'RR': 'mean', 'PPM': 'mean', 'ADM2_EN': 'first'})
            else:
                gdf_avg = gdf_filtered.set_index('kab_key')
            fig_map = px.choropleth_map(
                gdf_avg,
                geojson=gdf_avg.geometry,
                locations=gdf_avg.index,
                color="RR",
                color_continuous_scale="sunsetdark",
                map_style="carto-positron",
                zoom=5.8,
                center={"lat": -8.6, "lon": 120.0},
                opacity=0.8,
                hover_name="ADM2_EN",
                hover_data={"RR": ":.3f", "PPM": ":.2f"}
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("Data peta tidak tersedia untuk filter yang dipilih.")

with row2_col2:
    with st.container(border=True):
        st.markdown("#### 🏆 10 Daerah Kemiskinan Tertinggi")
        if len(df_filtered) > 0:
            if selected_year_opt == 'Semua':
                df_bar = df_filtered.groupby(kab_col)['PPM'].mean().reset_index()
            else:
                df_bar = df_filtered.copy()
            df_top = df_bar.sort_values(by='PPM', ascending=True).tail(10)
            fig_bar = px.bar(df_top, x="PPM", y=kab_col, orientation='h', color_discrete_sequence=['#2BB0A4'])
            fig_bar.update_layout(
                xaxis_title="Kemiskinan (PPM %)", 
                yaxis_title="", 
                margin={"r":0,"t":0,"l":0,"b":0},
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
row3_col1, row3_col2 = st.columns((7, 3))

with row3_col1:
    with st.container(border=True):
        st.markdown("#### 📈 Tren Rata-rata Kemiskinan")
        if selected_prov == 'Semua':
            trend_ppm = df.groupby('Tahun')['PPM'].mean().reset_index()
        else:
            trend_ppm = df[df['kab_key'].isin(valid_kabs)].groupby('Tahun')['PPM'].mean().reset_index()
            
        # Mengubah jadi line chart dengan range dinamis agar tren jelas
        fig_line = px.line(trend_ppm, x='Tahun', y='PPM', color_discrete_sequence=['#EA4380'], markers=True)
        fig_line.update_xaxes(type='category')
        
        # Memberikan range sedikit di atas dan bawah dari nilai asli
        y_min = trend_ppm['PPM'].min() - 0.5
        y_max = trend_ppm['PPM'].max() + 0.5
        fig_line.update_yaxes(range=[y_min, y_max])
        
        fig_line.update_layout(
            margin={"r":0,"t":10,"l":0,"b":0},
            plot_bgcolor='rgba(0,0,0,0)'
        )
        # Menambahkan efek bayangan pada line traces (fill='tozeroy' seperti area tapi mulai dari margin)
        fig_line.update_traces(fill='tozeroy', fillcolor='rgba(234, 67, 128, 0.1)', line=dict(width=3))
        st.plotly_chart(fig_line, use_container_width=True)

with row3_col2:
    with st.container(border=True):
        st.markdown("#### ⭕ Persentase Kategori Wilayah")
        if len(df_filtered) > 0:
            prop_data = pd.DataFrame({
                'Kategori': ['Berisiko (RR > 1)', 'Aman (RR ≤ 1)'],
                'Jumlah': [keparahan, total_daerah - keparahan]
            })
            fig_pie = px.pie(
                prop_data, 
                values='Jumlah', 
                names='Kategori', 
                hole=0.55, 
                color='Kategori',
                color_discrete_map={'Berisiko (RR > 1)': '#EA4380', 'Aman (RR ≤ 1)': '#2BB0A4'}
            )
            # Menarik irisan pink keluar (pull), persentase di dalam
            fig_pie.update_traces(
                pull=[0.08, 0], 
                textinfo='percent', 
                textposition='inside',
                insidetextfont=dict(color='white', size=16),
                marker=dict(line=dict(color='#ffffff', width=2))
            )
            fig_pie.update_layout(
                margin={"r":0,"t":10,"l":0,"b":0},
                showlegend=True, 
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

