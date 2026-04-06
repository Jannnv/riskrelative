import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import re

# Set Page Config
st.set_page_config(page_title="Dashboard Analisis Kemiskinan", page_icon="📊", layout="wide")

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
    merged_gdf = gdf[['kab_key', 'ADM2_EN', 'geometry']].merge(df, on='kab_key', how='inner')
    return df, merged_gdf, kab_col

df, merged_gdf, kab_col = load_data()

# Header
st.markdown("<h2 style='text-align: center; margin-bottom: 30px; font-weight: 800; color: #2C3E50;'>👨‍💻 Dashboard Analisis Spasial Kemiskinan</h2>", unsafe_allow_html=True)

# Filters Sidebar
st.sidebar.markdown("### ⚙️ Filter Data")
years = sorted(df['Tahun'].unique())
selected_year = st.sidebar.selectbox("Pilih Tahun:", years)
# Optional Province Filter using ADM1_EN
provinsi = ['Seluruhnya', 'Nusa Tenggara Barat', 'Nusa Tenggara Timur']
selected_prov = st.sidebar.selectbox("Pilih Provinsi:", provinsi)

# Filter Data Logic
df_filtered = df[df['Tahun'] == selected_year]
gdf_filtered = merged_gdf[merged_gdf['Tahun'] == selected_year]

if selected_prov != 'Seluruhnya':
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

# Metric Computation
rata_ppm = df_filtered['PPM'].mean()
if len(df_filtered) > 0:
    max_rr_row = df_filtered.loc[df_filtered['RR'].idxmax()]
    keparahan = len(df_filtered[df_filtered['RR'] > 1.0])
else:
    rata_ppm = 0
    max_rr_row = {'kab_key': '-', 'RR': 0, 'PPM': 0}
    keparahan = 0
total_daerah = len(df_filtered)

# Layout Metrics
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Rata-rata PPM</div>
        <div class="metric-value">{rata_ppm:.2f}%</div>
        <div class="metric-change">Tahun {selected_year}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    kab_name = str(max_rr_row[kab_col]).title() if len(df_filtered) > 0 else "-"
    rr_val = float(max_rr_row['RR']) if len(df_filtered) > 0 else 0.0
    ppm_val = float(max_rr_row['PPM']) if len(df_filtered) > 0 else 0.0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Daerah Risiko Bencana (Tertinggi)</div>
        <div class="metric-value">{rr_val:.2f}</div>
        <div class="metric-change bad">{kab_name} (PPM: {ppm_val:.2f}%)</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Daerah Berisiko Tinggi</div>
        <div class="metric-value">{keparahan}</div>
        <div class="metric-change bad">Dari {total_daerah} Kabupaten/Kota</div>
    </div>
    """, unsafe_allow_html=True)

# Charts Section
row2_col1, row2_col2 = st.columns((7, 3))

with row2_col1:
    st.markdown("#### 🗺️ Peta Relative Risk (RR)")
    if len(gdf_filtered) > 0:
        gdf_filtered = gdf_filtered.set_index('kab_key')
        fig_map = px.choropleth_mapbox(
            gdf_filtered,
            geojson=gdf_filtered.geometry,
            locations=gdf_filtered.index,
            color="RR",
            color_continuous_scale="sunsetdark", # Vibrant colors
            mapbox_style="carto-positron",
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
    st.markdown("#### 🏆 10 Daerah Kemiskinan Tertinggi")
    if len(df_filtered) > 0:
        df_top = df_filtered.sort_values(by='PPM', ascending=True).tail(10) # Ascending for correct rendering on horizontal bars
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
    st.markdown("#### 📈 Tren Rata-rata Kemiskinan")
    if selected_prov == 'Seluruhnya':
        trend_ppm = df.groupby('Tahun')['PPM'].mean().reset_index()
    else:
        trend_ppm = df[df['kab_key'].isin(valid_kabs)].groupby('Tahun')['PPM'].mean().reset_index()
        
    fig_area = px.area(trend_ppm, x='Tahun', y='PPM', color_discrete_sequence=['#EA4380'])
    fig_area.update_xaxes(type='category')
    fig_area.update_layout(
        margin={"r":0,"t":10,"l":0,"b":0},
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_area, use_container_width=True)

with row3_col2:
    st.markdown("#### ⭕ Persentase Kategori Wilayah")
    if len(df_filtered) > 0:
        prop_data = pd.DataFrame({
            'Kategori': ['Berisiko (RR > 1)', 'Aman (RR ≤ 1)'],
            'Jumlah': [keparahan, total_daerah - keparahan]
        })
        fig_pie = px.pie(prop_data, values='Jumlah', names='Kategori', hole=0.5, color_discrete_sequence=['#EA4380', '#2BB0A4'])
        fig_pie.update_layout(
            margin={"r":0,"t":10,"l":0,"b":0},
            showlegend=True, 
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

