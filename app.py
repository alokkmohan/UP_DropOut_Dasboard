import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import os
from io import StringIO

# --- GOOGLE DRIVE FILE CONFIG ---
# Folder link:
# https://drive.google.com/drive/folders/1WKRqYOpH0R2LWjYBkvM9RV3V-XC2RinC?usp=drive_link
# File link example: https://drive.google.com/file/d/1-eQAWfoNyAijKUtVOJDwI-xxxxxxxxx/view?usp=sharing
# Extract FILE_ID from your particular Google Drive file

CSV_FILE_ID = "PASTE_YOUR_FILE_ID_HERE"  # CHANGE THIS to your real file-id, see below
CSV_LOCAL_PATH = "Master_UP_Dropout_Database.csv"

def download_from_gdrive(file_id, dest_path):
    if os.path.exists(dest_path):
        return
    # Create download URL
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

# Page config
st.set_page_config(
    page_title="UP Education Dropout Dashboard",
    page_icon="🎓",
    layout="wide"
)

# CSS
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .main-title { font-size: 2.5rem; font-weight: bold; color: white; text-align: center; }
    .subtitle { font-size: 1.2rem; color: rgba(255,255,255,0.9); text-align: center; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_csv():
    # Download if not exists
    try:
        download_from_gdrive(CSV_FILE_ID, CSV_LOCAL_PATH)
        return pd.read_csv(CSV_LOCAL_PATH, low_memory=False)
    except Exception as e:
        st.error(f"Error loading or downloading data: {e}")
        return None

# Header
st.markdown('<h1 class="main-title">🎓 UP शिक्षा विभाग - Dropout Dashboard</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">State-Level Analysis | 75 Districts | 1+ Crore Records</p>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Data loading
with st.spinner("Loading data from Google Drive..."):
    df = load_csv()

if df is None:
    st.stop()

st.sidebar.success(f"✅ Loaded {len(df):,} records")

# Filters
st.sidebar.markdown("---")
st.sidebar.markdown("## 🎛️ Filters")

districts = ['All'] + sorted(df['District Name'].unique().tolist())
selected_district = st.sidebar.selectbox("District:", districts)

years = ['All'] + sorted(df['Academic Year'].unique().tolist())
selected_year = st.sidebar.selectbox("Academic Year:", years)

edu_levels = ['All'] + df['Education Level'].unique().tolist()
selected_edu = st.sidebar.selectbox("Education Level:", edu_levels)

genders = ['All'] + df['Gender'].unique().tolist()
selected_gender = st.sidebar.selectbox("Gender:", genders)

mgmt_types = ['All'] + df['Management Type Label'].unique().tolist()
selected_mgmt = st.sidebar.selectbox("Management Type:", mgmt_types)

filtered_df = df.copy()
if selected_district != 'All':
    filtered_df = filtered_df[filtered_df['District Name'] == selected_district]
if selected_year != 'All':
    filtered_df = filtered_df[filtered_df['Academic Year'] == selected_year]
if selected_edu != 'All':
    filtered_df = filtered_df[filtered_df['Education Level'] == selected_edu]
if selected_gender != 'All':
    filtered_df = filtered_df[filtered_df['Gender'] == selected_gender]
if selected_mgmt != 'All':
    filtered_df = filtered_df[filtered_df['Management Type Label'] == selected_mgmt]

total = len(filtered_df)
districts_count = filtered_df['District Name'].nunique()
blocks_count = filtered_df['Block Name'].nunique()
schools_count = filtered_df['Last UDISE Code'].nunique()

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""<div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                padding: 1.5rem; border-radius: 15px; text-align: center; color: white;'>
        <h4 style='margin: 0; font-size: 0.9rem;'>Total Dropouts</h4>
        <h2 style='margin: 0.5rem 0; font-size: 2rem;'>{total:,}</h2>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                padding: 1.5rem; border-radius: 15px; text-align: center; color: white;'>
        <h4 style='margin: 0; font-size: 0.9rem;'>Districts</h4>
        <h2 style='margin: 0.5rem 0; font-size: 2rem;'>{districts_count}</h2>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""<div style='background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); 
                padding: 1.5rem; border-radius: 15px; text-align: center; color: white;'>
        <h4 style='margin: 0; font-size: 0.9rem;'>Blocks</h4>
        <h2 style='margin: 0.5rem 0; font-size: 2rem;'>{blocks_count}</h2>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""<div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); 
                padding: 1.5rem; border-radius: 15px; text-align: center; color: white;'>
        <h4 style='margin: 0; font-size: 0.9rem;'>Schools</h4>
        <h2 style='margin: 0.5rem 0; font-size: 2rem;'>{schools_count:,}</h2>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview",
    "🗺️ Districts",
    "📚 Education Level", 
    "🏫 Schools",
    "📥 Export"
])

with tab1:
    st.markdown("## 📊 Overview")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📅 Year-wise Trend")
        year_data = filtered_df['Academic Year'].value_counts().sort_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=year_data.index,
            y=year_data.values,
            mode='lines+markers',
            line=dict(color='#667eea', width=3),
            marker=dict(size=12)
        ))
        fig.update_layout(height=350, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("### 👥 Gender Distribution")
        gender_data = filtered_df['Gender'].value_counts()
        fig = go.Figure(data=[go.Pie(
            labels=gender_data.index,
            values=gender_data.values,
            hole=.5
        )])
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### 📚 Education Level Distribution")
    edu_data = filtered_df['Education Level'].value_counts()
    fig = px.bar(x=edu_data.index, y=edu_data.values, color=edu_data.values, color_continuous_scale='Reds')
    fig.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("## 🗺️ District Analysis")
    st.markdown("### Top 20 Districts")
    district_counts = filtered_df['District Name'].value_counts().head(20)
    fig = px.bar(
        x=district_counts.index,
        y=district_counts.values,
        color=district_counts.values,
        color_continuous_scale='Reds'
    )
    fig.update_layout(height=500, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("### District Summary")
    district_summary = filtered_df.groupby('District Name').agg({
        'District Name': 'count',
        'Block Name': 'nunique',
        'Last UDISE Code': 'nunique'
    }).rename(columns={
        'District Name': 'Dropouts',
        'Block Name': 'Blocks',
        'Last UDISE Code': 'Schools'
    }).sort_values('Dropouts', ascending=False)
    st.dataframe(district_summary, use_container_width=True, height=400)

with tab3:
    st.markdown("## 📚 Education Level Analysis")
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown("### Class-wise Dropouts")
        class_data = filtered_df['Last Class'].value_counts()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[f"Class {c}" for c in class_data.index],
            y=class_data.values,
            marker=dict(color=class_data.values, colorscale='Reds')
        ))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("### Education Levels")
        for level in ['Primary (1-5)', 'Upper Primary (6-8)', 'Secondary (9-10)', 'Sr. Secondary (11-12)']:
            count = len(filtered_df[filtered_df['Education Level'] == level])
            pct = (count/total*100) if total > 0 else 0
            color = {
                'Primary (1-5)': '#fef3c7',
                'Upper Primary (6-8)': '#fecaca',
                'Secondary (9-10)': '#ddd6fe',
                'Sr. Secondary (11-12)': '#d1fae5'
            }[level]
            st.markdown(f"""
            <div style='background: {color}; padding: 1rem; border-radius: 10px; margin-bottom: 0.5rem;'>
                <h4 style='margin: 0; font-size: 0.9rem;'>{level}</h4>
                <h3 style='margin: 0.25rem 0;'>{count:,}</h3>
                <p style='margin: 0; font-size: 0.85rem;'>{pct:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)

with tab4:
    st.markdown("## 🏫 School Analysis")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Management Type")
        mgmt_data = filtered_df['Management Type Label'].value_counts()
        fig = px.pie(values=mgmt_data.values, names=mgmt_data.index, hole=0.4)
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("### Top 10 Schools")
        school_counts = filtered_df.groupby('Last School Name').size().sort_values(ascending=False).head(10)
        st.dataframe(school_counts, use_container_width=True, height=350)

with tab5:
    st.markdown("## 📥 Data Export")
    st.markdown("### Download Filtered Data")
    col1, col2, col3 = st.columns(3)
    with col1:
        sample_df = filtered_df.head(100000)
        csv = sample_df.to_csv(index=False)
        st.download_button(
            "📄 Download Sample (100k)",
            csv,
            f"UP_Dropout_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
    with col2:
        district_summary_csv = district_summary.to_csv()
        st.download_button(
            "📊 District Summary",
            district_summary_csv,
            f"District_Summary_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
    with col3:
        st.markdown(f"""
        <div style='background: #e0e7ff; padding: 1rem; border-radius: 10px;'>
            <h4 style='margin: 0;'>📊 Current Filter</h4>
            <p style='margin: 0.5rem 0 0 0;'>Records: {total:,}</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: white; padding: 1rem;'>
    <p>🎓 उत्तर प्रदेश शिक्षा विभाग | UP Education Department</p>
</div>
""", unsafe_allow_html=True)
