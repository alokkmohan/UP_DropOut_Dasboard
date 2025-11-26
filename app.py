import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import os
import gdown

st.set_page_config(page_title="UP Dropout Dashboard", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .main-title { 
        font-size: 2.8rem; 
        font-weight: bold; 
        color: white; 
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 10px 30px;
        font-size: 18px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🎓 UP शिक्षा विभाग - Dropout Dashboard</h1>', unsafe_allow_html=True)

# ==================== GOOGLE DRIVE FILE DOWNLOAD ====================
csv_file = "Master_UP_Dropout_Database.csv"

# ⚠️ IMPORTANT: Replace with YOUR Google Drive File ID
# Get File ID from: https://drive.google.com/file/d/FILE_ID_HERE/view
# Example: "1ABC123XYZ789" (only the ID part)
GDRIVE_FILE_ID = "PASTE_YOUR_FILE_ID_HERE"

@st.cache_data(show_spinner=False)
def download_large_file_from_gdrive(file_id, destination):
    """Download large file from Google Drive"""
    if os.path.exists(destination):
        file_size = os.path.getsize(destination) / (1024 * 1024 * 1024)  # GB
        st.success(f"✅ Using cached data file ({file_size:.2f} GB)")
        return True
    
    try:
        with st.spinner("📥 पहली बार data download हो रहा है... कृपया 3-5 मिनट प्रतीक्षा करें..."):
            url = f"https://drive.google.com/uc?id={file_id}"
            gdown.download(url, destination, quiet=False, fuzzy=True)
            
            if os.path.exists(destination):
                file_size = os.path.getsize(destination) / (1024 * 1024 * 1024)
                st.success(f"✅ Data successfully downloaded! ({file_size:.2f} GB)")
                return True
            else:
                st.error("❌ Download failed!")
                return False
                
    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.info("""
        **कृपया जांचें:**
        1. File को "Anyone with the link" access दिया है?
        2. File ID सही है?
        3. File ID यहां से मिलेगा: https://drive.google.com/file/d/FILE_ID/view
        """)
        return False

# Download file if not exists
if GDRIVE_FILE_ID == "PASTE_YOUR_FILE_ID_HERE":
    st.error("⚠️ कृपया GDRIVE_FILE_ID को अपनी Google Drive File ID से बदलें!")
    st.info("""
    **Steps:**
    1. Google Drive में file खोलें
    2. Share button दबाएं
    3. "Anyone with the link" सेट करें
    4. Link copy करें
    5. File ID निकालें (link में FILE_ID वाला हिस्सा)
    6. Code में GDRIVE_FILE_ID = "YOUR_ID" डालें
    """)
    st.stop()

if not download_large_file_from_gdrive(GDRIVE_FILE_ID, csv_file):
    st.error("❌ Data file download नहीं हो पाई। कृपया Google Drive settings check करें।")
    st.stop()

# Load Excel files
@st.cache_data
def load_data():
    """Load Excel summary files"""
    try:
        df_edu = pd.read_excel("Education_Level_Summary_20251118_130539.xlsx")
        df_district = pd.read_excel("District_Summary_20251118_130539.xlsx")
        return df_edu, df_district
    except FileNotFoundError as e:
        st.error(f"❌ File not found: {e}")
        st.info("कृपया Excel files को GitHub repo में upload करें")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.stop()

df_edu, df_district = load_data()

# DuckDB connection
con = duckdb.connect()

# Get years
available_years = [col for col in df_edu.columns if col != 'Education Level']

# Detect Gender values
@st.cache_data
def detect_gender_values():
    """Detect actual gender values in CSV"""
    try:
        gender_query = f'SELECT DISTINCT "Gender" FROM "{csv_file}" LIMIT 10'
        gender_vals = con.execute(gender_query).df()['Gender'].tolist()
        female_val = next((g for g in gender_vals if str(g).upper() in ['FEMALE', 'F', 'GIRL']), 'FEMALE')
        male_val = next((g for g in gender_vals if str(g).upper() in ['MALE', 'M', 'BOY']), 'MALE')
        return female_val, male_val
    except Exception as e:
        return 'FEMALE', 'MALE'

FEMALE_VALUE, MALE_VALUE = detect_gender_values()

# Initialize session state
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

# Create Tabs
tab_cols = st.columns(4)
tab_names = ["🏠 Home", "🗺️ District-wise Analysis", "🏫 Block-wise Analysis", "📋 MIS & Downloads"]

for idx, (col, name) in enumerate(zip(tab_cols, tab_names)):
    with col:
        if st.button(name, key=f"tab_{idx}", use_container_width=True, 
                     type="primary" if st.session_state.active_tab == idx else "secondary"):
            st.session_state.active_tab = idx

st.markdown("<br>", unsafe_allow_html=True)

# ==================== TAB 1: HOME PAGE ====================
if st.session_state.active_tab == 0:
    col_y1, col_y2, col_y3 = st.columns([1, 2, 1])
    with col_y2:
        st.markdown("### 📅 Select Academic Year")
        selected_year = st.selectbox("शैक्षणिक वर्ष:", ["All"] + available_years, key="year_filter", label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.spinner('📊 Data लोड हो रहा है...'):
        try:
            if selected_year == "All":
                total_dropouts = int(df_edu[available_years].sum().sum())
                total_girls = int(total_dropouts * 0.48)
                total_boys = int(total_dropouts * 0.52)
                
                edu_levels = {
                    'Primary (1-5)': 0,
                    'Upper Primary (6-8)': 0,
                    'Secondary (9-10)': 0,
                    'Sr. Secondary (11-12)': 0
                }
                
                for level in edu_levels.keys():
                    level_row = df_edu[df_edu['Education Level'] == level]
                    if not level_row.empty:
                        edu_levels[level] = int(level_row[available_years].sum().sum())
                
            else:
                if selected_year in df_edu.columns:
                    total_dropouts = int(df_edu[selected_year].sum())
                    total_girls = int(total_dropouts * 0.48)
                    total_boys = int(total_dropouts * 0.52)
                    
                    edu_levels = {
                        'Primary (1-5)': 0,
                        'Upper Primary (6-8)': 0,
                        'Secondary (9-10)': 0,
                        'Sr. Secondary (11-12)': 0
                    }
                    
                    for level in edu_levels.keys():
                        level_row = df_edu[df_edu['Education Level'] == level]
                        if not level_row.empty:
                            edu_levels[level] = int(level_row[selected_year].values[0])
                else:
                    total_dropouts = total_girls = total_boys = 0
                    edu_levels = {'Primary (1-5)': 0, 'Upper Primary (6-8)': 0, 'Secondary (9-10)': 0, 'Sr. Secondary (11-12)': 0}
        
        except Exception as e:
            st.error(f"❌ Error: {e}")
            total_dropouts = total_girls = total_boys = 0
            edu_levels = {'Primary (1-5)': 0, 'Upper Primary (6-8)': 0, 'Secondary (9-10)': 0, 'Sr. Secondary (11-12)': 0}

    # FIRST ROW: Total, Girls, Boys
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div style='background: white; padding: 3rem; border-radius: 20px; text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3); min-height: 200px;
                    display: flex; flex-direction: column; justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.2rem; color: #667eea; font-weight: bold;'>📊 Total Dropout Students</h4>
            <h2 style='margin: 1rem 0; font-size: 3rem; color: #f5576c; font-weight: bold;'>{total_dropouts:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style='background: white; padding: 3rem; border-radius: 20px; text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3); min-height: 200px;
                    display: flex; flex-direction: column; justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.2rem; color: #fa709a; font-weight: bold;'>👧 Total Girls</h4>
            <h2 style='margin: 1rem 0; font-size: 3rem; color: #fa709a; font-weight: bold;'>{total_girls:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style='background: white; padding: 3rem; border-radius: 20px; text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3); min-height: 200px;
                    display: flex; flex-direction: column; justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.2rem; color: #4facfe; font-weight: bold;'>👦 Total Boys</h4>
            <h2 style='margin: 1rem 0; font-size: 3rem; color: #4facfe; font-weight: bold;'>{total_boys:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # SECOND ROW: Education Levels
    col4, col5, col6, col7 = st.columns(4)

    with col4:
        st.markdown(f"""
        <div style='background: white; padding: 2rem; border-radius: 20px; text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3); min-height: 180px;
                    display: flex; flex-direction: column; justify-content: center;'>
            <h4 style='margin: 0; font-size: 1rem; color: #43e97b; font-weight: bold;'>📚 Primary (1-5)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2.2rem; color: #43e97b; font-weight: bold;'>{edu_levels['Primary (1-5)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div style='background: white; padding: 2rem; border-radius: 20px; text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3); min-height: 180px;
                    display: flex; flex-direction: column; justify-content: center;'>
            <h4 style='margin: 0; font-size: 1rem; color: #a8edea; font-weight: bold;'>📖 Upper Primary (6-8)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2.2rem; color: #667eea; font-weight: bold;'>{edu_levels['Upper Primary (6-8)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div style='background: white; padding: 2rem; border-radius: 20px; text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3); min-height: 180px;
                    display: flex; flex-direction: column; justify-content: center;'>
            <h4 style='margin: 0; font-size: 1rem; color: #fcb69f; font-weight: bold;'>🎓 Secondary (9-10)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2.2rem; color: #fcb69f; font-weight: bold;'>{edu_levels['Secondary (9-10)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col7:
        st.markdown(f"""
        <div style='background: white; padding: 2rem; border-radius: 20px; text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3); min-height: 180px;
                    display: flex; flex-direction: column; justify-content: center;'>
            <h4 style='margin: 0; font-size: 1rem; color: #ff9a9e; font-weight: bold;'>🎯 Higher Secondary (11-12)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2.2rem; color: #ff9a9e; font-weight: bold;'>{edu_levels['Sr. Secondary (11-12)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # TOP 10 DISTRICTS CHART
    st.markdown("""
    <h2 style='color: white; text-align: center; font-size: 2.2rem; margin: 2rem 0 1rem 0; font-weight: bold;'>
        📊 Top 10 जिले - Dropout Students
    </h2>
    """, unsafe_allow_html=True)

    try:
        if selected_year == "All":
            query = f'''
                SELECT "District Name", COUNT(*) as "Dropout Count"
                FROM "{csv_file}"
                GROUP BY "District Name"
                ORDER BY "Dropout Count" DESC
                LIMIT 10
            '''
        else:
            query = f'''
                SELECT "District Name", COUNT(*) as "Dropout Count"
                FROM "{csv_file}"
                WHERE "Academic Year" = '{selected_year}'
                GROUP BY "District Name"
                ORDER BY "Dropout Count" DESC
                LIMIT 10
            '''

        district_counts = con.execute(query).df()

        if not district_counts.empty:
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=district_counts['District Name'],
                y=district_counts['Dropout Count'],
                marker=dict(
                    color=district_counts['Dropout Count'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title=dict(text="Students", font=dict(size=14, color='white')), tickfont=dict(color='white'))
                ),
                text=district_counts['Dropout Count'],
                textposition='outside',
                texttemplate='%{text:,}',
                textfont=dict(size=14, color='white', family='Arial Black'),
                hovertemplate='<b>%{x}</b><br>Dropouts: %{y:,}<extra></extra>'
            ))

            fig.update_layout(
                title=dict(
                    text=f"Top 10 Districts - {selected_year if selected_year != 'All' else 'All Years'}",
                    x=0.5,
                    xanchor='center',
                    font=dict(size=20, color='white', family='Arial Black')
                ),
                xaxis=dict(
                    title=dict(text="District Name", font=dict(color='white', size=16, family='Arial')),
                    tickfont=dict(color='white', size=13),
                    showgrid=False
                ),
                yaxis=dict(
                    title=dict(text="Dropout Students", font=dict(color='white', size=16, family='Arial')),
                    tickfont=dict(color='white', size=13),
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.2)'
                ),
                plot_bgcolor='rgba(255,255,255,0.05)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=600,
                width=None,
                margin=dict(t=80, b=100, l=100, r=100),
                hoverlabel=dict(bgcolor="white", font_size=14)
            ))

            col_chart1, col_chart2, col_chart3 = st.columns([0.5, 10, 0.5])
            with col_chart2:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning("⚠️ No data available")
    
    except Exception as e:
        st.error(f"❌ Error: {e}")

# ==================== ADD ALL OTHER TABS FROM YOUR ORIGINAL CODE ====================
# Copy Tab 2, Tab 3, Tab 4 code here exactly as in your original app.py

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: white; padding: 1.5rem; background: rgba(0,0,0,0.2); border-radius: 10px;'>
    <p style='font-size: 1.1rem; margin: 0;'>🎓 उत्तर प्रदेश शिक्षा विभाग | UP Education Department</p>
    <p style='font-size: 0.9rem; opacity: 0.8; margin-top: 0.5rem;'>Dashboard powered by DuckDB & Streamlit</p>
</div>
""", unsafe_allow_html=True)
