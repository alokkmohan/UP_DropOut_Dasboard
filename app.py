import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import os

st.set_page_config(page_title="UP Dropout Dashboard", layout="wide")

# Kaggle Dataset Download Function
@st.cache_data
def download_kaggle_dataset():
    """Download dataset from Kaggle using credentials from Streamlit secrets"""
    try:
        import kaggle
        from kaggle.api.kaggle_api_extended import KaggleApi
        
        # Setup Kaggle credentials from Streamlit secrets
        os.environ['KAGGLE_USERNAME'] = st.secrets["KAGGLE_USERNAME"]
        os.environ['KAGGLE_KEY'] = st.secrets["KAGGLE_KEY"]
        
        # Initialize Kaggle API
        api = KaggleApi()
        api.authenticate()
        
        # Download dataset (replace with your actual dataset path)
        dataset_name = st.secrets.get("KAGGLE_DATASET", "your-username/your-dataset-name")
        
        st.info(f"📥 Downloading dataset from Kaggle: {dataset_name}")
        api.dataset_download_files(dataset_name, path='.', unzip=True)
        st.success("✅ Dataset downloaded successfully!")
        
        return True
    except Exception as e:
        st.error(f"❌ Error downloading from Kaggle: {e}")
        st.info("💡 Make sure you have set KAGGLE_USERNAME, KAGGLE_KEY, and KAGGLE_DATASET in Streamlit secrets")
        return False

# Check if CSV exists locally, if not download from Kaggle
csv_file = "Master_UP_Dropout_Database.csv"
if not os.path.exists(csv_file):
    st.warning("⚠️ CSV file not found locally. Attempting to download from Kaggle...")
    download_kaggle_dataset()
    
    # Check again after download
    if not os.path.exists(csv_file):
        st.error(f"❌ CSV file still not found: {csv_file}")
        st.info("Please ensure the dataset is uploaded to Kaggle and secrets are configured correctly")
        st.stop()

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
    /* Bigger tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 10px 30px;
        font-size: 18px;
        font-weight: 600;
    }
    /* Fix chart container */
    .chart-container {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem auto;
        max-width: 1200px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🎓 UP शिक्षा विभाग - Dropout Dashboard</h1>', unsafe_allow_html=True)

# Load data files
@st.cache_data
def load_data():
    """Load Excel summary files"""
    try:
        df_edu = pd.read_excel("Education_Level_Summary_20251118_130539.xlsx")
        df_district = pd.read_excel("District_Summary_20251118_130539.xlsx")
        return df_edu, df_district
    except FileNotFoundError as e:
        st.error(f"❌ File not found: {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
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

# Initialize session state for active tab
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

# Create Tabs - Use columns to create clickable tab-like buttons
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
    # Year filter - centered
    col_y1, col_y2, col_y3 = st.columns([1, 2, 1])
    with col_y2:
        st.markdown("### 📅 Select Academic Year")
        selected_year = st.selectbox("शैक्षणिक वर्ष:", ["All"] + available_years, key="year_filter", label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Loading indicator
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

    # FIRST ROW: Total, Girls, Boys - WHITE SQUARE CARDS
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div style='background: white; 
                    padding: 3rem; 
                    border-radius: 20px; 
                    text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                    min-height: 200px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.2rem; color: #667eea; font-weight: bold;'>📊 Total Dropout Students</h4>
            <h2 style='margin: 1rem 0; font-size: 3rem; color: #f5576c; font-weight: bold;'>{total_dropouts:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style='background: white; 
                    padding: 3rem; 
                    border-radius: 20px; 
                    text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                    min-height: 200px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.2rem; color: #fa709a; font-weight: bold;'>👧 Total Girls</h4>
            <h2 style='margin: 1rem 0; font-size: 3rem; color: #fa709a; font-weight: bold;'>{total_girls:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style='background: white; 
                    padding: 3rem; 
                    border-radius: 20px; 
                    text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                    min-height: 200px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.2rem; color: #4facfe; font-weight: bold;'>👦 Total Boys</h4>
            <h2 style='margin: 1rem 0; font-size: 3rem; color: #4facfe; font-weight: bold;'>{total_boys:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # SECOND ROW: Education Levels - WHITE SQUARE CARDS
    col4, col5, col6, col7 = st.columns(4)

    with col4:
        st.markdown(f"""
        <div style='background: white; 
                    padding: 2rem; 
                    border-radius: 20px; 
                    text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                    min-height: 180px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1rem; color: #43e97b; font-weight: bold;'>📚 Primary (1-5)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2.2rem; color: #43e97b; font-weight: bold;'>{edu_levels['Primary (1-5)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div style='background: white; 
                    padding: 2rem; 
                    border-radius: 20px; 
                    text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                    min-height: 180px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1rem; color: #a8edea; font-weight: bold;'>📖 Upper Primary (6-8)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2.2rem; color: #667eea; font-weight: bold;'>{edu_levels['Upper Primary (6-8)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div style='background: white; 
                    padding: 2rem; 
                    border-radius: 20px; 
                    text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                    min-height: 180px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1rem; color: #fcb69f; font-weight: bold;'>🎓 Secondary (9-10)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2.2rem; color: #fcb69f; font-weight: bold;'>{edu_levels['Secondary (9-10)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col7:
        st.markdown(f"""
        <div style='background: white; 
                    padding: 2rem; 
                    border-radius: 20px; 
                    text-align: center; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
                    min-height: 180px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1rem; color: #ff9a9e; font-weight: bold;'>🎯 Higher Secondary (11-12)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2.2rem; color: #ff9a9e; font-weight: bold;'>{edu_levels['Sr. Secondary (11-12)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # TOP 10 DISTRICTS CHART - CENTERED AND LARGE
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
            )

            # Center the chart
            col_chart1, col_chart2, col_chart3 = st.columns([0.5, 10, 0.5])
            with col_chart2:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning("⚠️ No data available")
    
    except Exception as e:
        st.error(f"❌ Error loading chart: {e}")

# ==================== TAB 2: DISTRICT-WISE ANALYSIS ====================
if st.session_state.active_tab == 1:
    st.markdown('<h2 style="color: white; text-align: center; font-size: 2.2rem; margin: 1rem 0; font-weight: bold;">🗺️ District-wise Detailed Analysis</h2>', unsafe_allow_html=True)
    
    # Filters
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        st.markdown("### 📅 Select Academic Year")
        selected_year_district = st.selectbox("शैक्षणिक वर्ष:", ["All"] + available_years, key="year_filter_district", label_visibility="collapsed")
    
    with col_filter2:
        st.markdown("### 🏘️ Select District")
        try:
            districts_list = con.execute(f'SELECT DISTINCT "District Name" FROM "{csv_file}" ORDER BY "District Name"').df()['District Name'].tolist()
        except Exception as e:
            st.error(f"❌ Error: {e}")
            districts_list = []
        
        selected_district = st.selectbox("जिला चुनें:", ["-- Select District --"] + districts_list, key="district_filter", label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if selected_district != "-- Select District --":
        with st.spinner(f'📊 {selected_district} का Data लोड हो रहा है...'):
            
            try:
                if selected_year_district == "All":
                    district_query = f'''
                        SELECT COUNT(*) as total,
                               SUM(CASE WHEN UPPER("Gender") LIKE '%{FEMALE_VALUE.upper()}%' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN UPPER("Gender") LIKE '%{MALE_VALUE.upper()}%' THEN 1 ELSE 0 END) as boys
                        FROM "{csv_file}"
                        WHERE "District Name" = '{selected_district}'
                    '''
                else:
                    district_query = f'''
                        SELECT COUNT(*) as total,
                               SUM(CASE WHEN UPPER("Gender") LIKE '%{FEMALE_VALUE.upper()}%' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN UPPER("Gender") LIKE '%{MALE_VALUE.upper()}%' THEN 1 ELSE 0 END) as boys
                        FROM "{csv_file}"
                        WHERE "District Name" = '{selected_district}' AND "Academic Year" = '{selected_year_district}'
                    '''
            
                district_stats = con.execute(district_query).df()
                district_total = int(district_stats['total'].values[0]) if not district_stats.empty else 0
                district_girls = int(district_stats['girls'].values[0]) if not district_stats.empty else 0
                district_boys = int(district_stats['boys'].values[0]) if not district_stats.empty else 0
                
                # Education level counts
                if selected_year_district == "All":
                    edu_query = f'''
                        SELECT "Education Level", COUNT(*) as count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{selected_district}'
                        GROUP BY "Education Level"
                    '''
                else:
                    edu_query = f'''
                        SELECT "Education Level", COUNT(*) as count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{selected_district}' AND "Academic Year" = '{selected_year_district}'
                        GROUP BY "Education Level"
                    '''
                
                edu_breakdown = con.execute(edu_query).df()
                
                # Get individual education level counts
                district_primary = int(edu_breakdown[edu_breakdown['Education Level'] == 'Primary (1-5)']['count'].values[0]) if len(edu_breakdown[edu_breakdown['Education Level'] == 'Primary (1-5)']) > 0 else 0
                district_upper_primary = int(edu_breakdown[edu_breakdown['Education Level'] == 'Upper Primary (6-8)']['count'].values[0]) if len(edu_breakdown[edu_breakdown['Education Level'] == 'Upper Primary (6-8)']) > 0 else 0
                district_secondary = int(edu_breakdown[edu_breakdown['Education Level'] == 'Secondary (9-10)']['count'].values[0]) if len(edu_breakdown[edu_breakdown['Education Level'] == 'Secondary (9-10)']) > 0 else 0
                district_sr_secondary = int(edu_breakdown[edu_breakdown['Education Level'] == 'Sr. Secondary (11-12)']['count'].values[0]) if len(edu_breakdown[edu_breakdown['Education Level'] == 'Sr. Secondary (11-12)']) > 0 else 0
                
            except Exception as e:
                st.error(f"❌ Error: {e}")
                district_total = district_girls = district_boys = 0
                district_primary = district_upper_primary = district_secondary = district_sr_secondary = 0
                edu_breakdown = pd.DataFrame()
        
        # METRIC BOXES - 7 columns
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        
        metrics = [
            ("📊 Total Dropouts", district_total, col1, "#ff6b6b", "#ee5a6f"),
            ("👧 Girls", district_girls, col2, "#fa709a", "#fee140"),
            ("👦 Boys", district_boys, col3, "#4facfe", "#00f2fe"),
            ("🎒 Primary", district_primary, col4, "#43e97b", "#38f9d7"),
            ("📚 Upper Primary", district_upper_primary, col5, "#fa8bff", "#2bd2ff"),
            ("🎓 Secondary", district_secondary, col6, "#fccb90", "#d57eeb"),
            ("🏆 Higher Secondary", district_sr_secondary, col7, "#a8edea", "#fed6e3")
        ]
        
        for title, value, column, color1, color2 in metrics:
            with column:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, {color1}, {color2}); 
                            padding: 1.8rem; border-radius: 15px; text-align: center; 
                            box-shadow: 0 8px 16px rgba(0,0,0,0.2); height: 150px; 
                            display: flex; flex-direction: column; justify-content: center;'>
                    <h3 style='color: white; margin: 0; font-size: 1rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>{title}</h3>
                    <p style='color: white; font-size: 2.2rem; font-weight: bold; margin: 0.5rem 0 0 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{value:,}</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # TOP 10 BLOCKS
        st.markdown(f"""
        <h3 style='color: white; text-align: center; font-size: 2rem; margin-bottom: 1rem; font-weight: bold;'>
            📍 Top 10 Blocks in {selected_district}
        </h3>
        """, unsafe_allow_html=True)
        
        try:
            if selected_year_district == "All":
                block_query = f'''
                    SELECT "Block Name", COUNT(*) as "Dropout Count"
                    FROM "{csv_file}"
                    WHERE "District Name" = '{selected_district}'
                    GROUP BY "Block Name"
                    ORDER BY "Dropout Count" DESC
                    LIMIT 10
                '''
            else:
                block_query = f'''
                    SELECT "Block Name", COUNT(*) as "Dropout Count"
                    FROM "{csv_file}"
                    WHERE "District Name" = '{selected_district}' AND "Academic Year" = '{selected_year_district}'
                    GROUP BY "Block Name"
                    ORDER BY "Dropout Count" DESC
                    LIMIT 10
                '''
            
            block_counts = con.execute(block_query).df()
            
            if not block_counts.empty:
                fig_blocks = go.Figure()
                
                fig_blocks.add_trace(go.Bar(
                    x=block_counts['Block Name'],
                    y=block_counts['Dropout Count'],
                    marker=dict(
                        color=block_counts['Dropout Count'],
                        colorscale='Plasma',
                        showscale=True,
                        colorbar=dict(title=dict(text="Students", font=dict(size=14, color='white')), tickfont=dict(color='white'))
                    ),
                    text=block_counts['Dropout Count'],
                    textposition='outside',
                    texttemplate='%{text:,}',
                    textfont=dict(size=14, color='white', family='Arial Black'),
                    hovertemplate='<b>%{x}</b><br>Dropouts: %{y:,}<extra></extra>'
                ))
                
                fig_blocks.update_layout(
                    title=dict(
                        text=f"Top 10 Blocks - {selected_district} ({selected_year_district if selected_year_district != 'All' else 'All Years'})",
                        x=0.5,
                        xanchor='center',
                        font=dict(size=18, color='white', family='Arial Black')
                    ),
                    xaxis=dict(
                        title=dict(text="Block Name", font=dict(color='white', size=16)),
                        tickfont=dict(color='white', size=12),
                        showgrid=False,
                        tickangle=-45
                    ),
                    yaxis=dict(
                        title=dict(text="Dropout Students", font=dict(color='white', size=16)),
                        tickfont=dict(color='white', size=13),
                        showgrid=True,
                        gridcolor='rgba(255,255,255,0.2)'
                    ),
                    plot_bgcolor='rgba(255,255,255,0.05)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=550,
                    margin=dict(t=80, b=140, l=100, r=100),
                    hoverlabel=dict(bgcolor="white", font_size=14)
                )
                
                st.plotly_chart(fig_blocks, use_container_width=True, config={'displayModeBar': False})
        
        except Exception as e:
            st.error(f"❌ Error: {e}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # PIE CHARTS
        if not edu_breakdown.empty:
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("""
                <h3 style='color: white; text-align: center; font-size: 1.6rem; font-weight: bold;'>
                    📚 Education Level Distribution
                </h3>
                """, unsafe_allow_html=True)
                
                fig_pie = px.pie(
                    edu_breakdown,
                    values='count',
                    names='Education Level',
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig_pie.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', size=13),
                    height=450
                )
                st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
            
            with col_b:
                st.markdown("""
                <h3 style='color: white; text-align: center; font-size: 1.6rem; font-weight: bold;'>
                    📊 Gender Distribution
                </h3>
                """, unsafe_allow_html=True)
                
                gender_data = pd.DataFrame({
                    'Gender': ['Girls', 'Boys'],
                    'Count': [district_girls, district_boys]
                })
                
                fig_gender = px.pie(
                    gender_data,
                    values='Count',
                    names='Gender',
                    color_discrete_sequence=['#fa709a', '#4facfe']
                )
                fig_gender.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', size=13),
                    height=450
                )
                st.plotly_chart(fig_gender, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("👆 कृपया ऊपर से एक जिला चुनें।")

# ==================== TAB 3: BLOCK-WISE ANALYSIS ====================
if st.session_state.active_tab == 2:
    # Filters in 3 columns
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        st.markdown("### 📅 Academic Year")
        block_year = st.selectbox("Year:", ["All"] + available_years, key="block_year_filter", label_visibility="collapsed")
    
    with col_f2:
        st.markdown("### 🗺️ Select District")
        # Get districts from CSV based on year
        if block_year == "All":
            districts_query = f'SELECT DISTINCT "District Name" FROM "{csv_file}" ORDER BY "District Name"'
        else:
            districts_query = f'SELECT DISTINCT "District Name" FROM "{csv_file}" WHERE "Academic Year" = \'{block_year}\' ORDER BY "District Name"'
        
        block_districts = con.execute(districts_query).df()['District Name'].tolist()
        block_selected_district = st.selectbox("District:", ["Select"] + block_districts, key="block_district_filter", label_visibility="collapsed")
    
    with col_f3:
        st.markdown("### 🏫 Select Block")
        if block_selected_district != "Select":
            # Get blocks from CSV based on year and district
            if block_year == "All":
                blocks_query = f'SELECT DISTINCT "Block Name" FROM "{csv_file}" WHERE "District Name" = \'{block_selected_district}\' ORDER BY "Block Name"'
            else:
                blocks_query = f'SELECT DISTINCT "Block Name" FROM "{csv_file}" WHERE "District Name" = \'{block_selected_district}\' AND "Academic Year" = \'{block_year}\' ORDER BY "Block Name"'
            
            block_blocks = con.execute(blocks_query).df()['Block Name'].tolist()
            block_selected_block = st.selectbox("Block:", ["Select"] + block_blocks, key="block_block_filter", label_visibility="collapsed")
        else:
            block_selected_block = "Select"
            st.selectbox("Block:", ["Select"], key="block_block_filter_empty", label_visibility="collapsed", disabled=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if block_selected_district != "Select" and block_selected_block != "Select":
        with st.spinner('📊 Data लोड हो रहा है...'):
            try:
                # Query data from CSV for selected block
                if block_year == "All":
                    block_query = f'''
                        SELECT COUNT(*) as total_count,
                               SUM(CASE WHEN "Gender" = '{FEMALE_VALUE}' THEN 1 ELSE 0 END) as female_count,
                               SUM(CASE WHEN "Gender" = '{MALE_VALUE}' THEN 1 ELSE 0 END) as male_count,
                               SUM(CASE WHEN "Education Level" = 'Primary (1-5)' THEN 1 ELSE 0 END) as primary_count,
                               SUM(CASE WHEN "Education Level" = 'Upper Primary (6-8)' THEN 1 ELSE 0 END) as upper_primary_count,
                               SUM(CASE WHEN "Education Level" = 'Secondary (9-10)' THEN 1 ELSE 0 END) as secondary_count,
                               SUM(CASE WHEN "Education Level" = 'Sr. Secondary (11-12)' THEN 1 ELSE 0 END) as sr_secondary_count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                    '''
                else:
                    block_query = f'''
                        SELECT COUNT(*) as total_count,
                               SUM(CASE WHEN "Gender" = '{FEMALE_VALUE}' THEN 1 ELSE 0 END) as female_count,
                               SUM(CASE WHEN "Gender" = '{MALE_VALUE}' THEN 1 ELSE 0 END) as male_count,
                               SUM(CASE WHEN "Education Level" = 'Primary (1-5)' THEN 1 ELSE 0 END) as primary_count,
                               SUM(CASE WHEN "Education Level" = 'Upper Primary (6-8)' THEN 1 ELSE 0 END) as upper_primary_count,
                               SUM(CASE WHEN "Education Level" = 'Secondary (9-10)' THEN 1 ELSE 0 END) as secondary_count,
                               SUM(CASE WHEN "Education Level" = 'Sr. Secondary (11-12)' THEN 1 ELSE 0 END) as sr_secondary_count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Academic Year" = '{block_year}'
                    '''
                
                block_stats = con.execute(block_query).df().iloc[0]
                
                # Metric boxes
                col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
                
                metrics = [
                    ("📊 Total Dropouts", int(block_stats['total_count']), col1, "#ff6b6b", "#ee5a6f"),
                    ("👧 Girls", int(block_stats['female_count']), col2, "#fa709a", "#fee140"),
                    ("👦 Boys", int(block_stats['male_count']), col3, "#4facfe", "#00f2fe"),
                    ("🎒 Primary", int(block_stats['primary_count']), col4, "#43e97b", "#38f9d7"),
                    ("📚 Upper Primary", int(block_stats['upper_primary_count']), col5, "#fa8bff", "#2bd2ff"),
                    ("🎓 Secondary", int(block_stats['secondary_count']), col6, "#fccb90", "#d57eeb"),
                    ("🏆 Higher Secondary", int(block_stats['sr_secondary_count']), col7, "#a8edea", "#fed6e3")
                ]
                
                for title, value, column, color1, color2 in metrics:
                    with column:
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, {color1}, {color2}); 
                                    padding: 1.8rem; border-radius: 15px; text-align: center; 
                                    box-shadow: 0 8px 16px rgba(0,0,0,0.2); height: 150px; 
                                    display: flex; flex-direction: column; justify-content: center;'>
                            <h3 style='color: white; margin: 0; font-size: 1rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>{title}</h3>
                            <p style='color: white; font-size: 2.2rem; font-weight: bold; margin: 0.5rem 0 0 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{value:,}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                # Top 10 Schools Chart
                st.markdown("### 🏫 Top 10 Schools by Dropout Count")
                
                if block_year == "All":
                    schools_query = f'''
                        SELECT "Last School Name" as school_name, COUNT(*) as dropout_count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Last School Name" IS NOT NULL
                        AND "Last School Name" != ''
                        GROUP BY "Last School Name"
                        ORDER BY dropout_count DESC
                        LIMIT 10
                    '''
                else:
                    schools_query = f'''
                        SELECT "Last School Name" as school_name, COUNT(*) as dropout_count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Academic Year" = '{block_year}'
                        AND "Last School Name" IS NOT NULL
                        AND "Last School Name" != ''
                        GROUP BY "Last School Name"
                        ORDER BY dropout_count DESC
                        LIMIT 10
                    '''
                
                school_counts = con.execute(schools_query).df()
                
                if not school_counts.empty:
                    fig_schools = go.Figure(go.Bar(
                        x=school_counts['school_name'],
                        y=school_counts['dropout_count'],
                        marker=dict(
                            color=school_counts['dropout_count'],
                            colorscale='Turbo',
                            showscale=True,
                            colorbar=dict(title=dict(text="Students", font=dict(size=14, color='white')), tickfont=dict(color='white'))
                        ),
                        text=school_counts['dropout_count'],
                        textposition='outside',
                        textfont=dict(color='white', size=13)
                    ))
                    
                    fig_schools.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white', size=13),
                        xaxis=dict(
                            title="School Name",
                            gridcolor='rgba(255,255,255,0.1)',
                            tickfont=dict(color='white', size=11)
                        ),
                        yaxis=dict(
                            title="Dropout Count",
                            gridcolor='rgba(255,255,255,0.1)',
                            tickfont=dict(color='white')
                        ),
                        height=500,
                        autosize=True,
                        margin=dict(l=50, r=50, t=50, b=150)
                    )
                    
                    st.plotly_chart(fig_schools, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("📊 कोई स्कूल डेटा उपलब्ध नहीं है।")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    else:
        st.info("👆 कृपया ऊपर से जिला और ब्लॉक चुनें।")

# ==================== TAB 4: MIS & DOWNLOADS ====================
if st.session_state.active_tab == 3:
    st.markdown('<h2 style="color: white; text-align: center; font-size: 2.2rem; margin: 1rem 0; font-weight: bold;">📋 MIS Reports & Data Downloads</h2>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ROW 1: Coverage Metrics
    st.markdown("### 📊 Data Coverage Overview")
    
    with st.spinner('📊 Calculating coverage metrics...'):
        try:
            coverage_query = f'''
                SELECT 
                    COUNT(*) as total_students,
                    SUM(CASE WHEN "Has Aadhaar" = true THEN 1 ELSE 0 END) as has_aadhaar,
                    SUM(CASE WHEN "Has Mobile" = true THEN 1 ELSE 0 END) as has_mobile,
                    SUM(CASE WHEN "Has Aadhaar" = true AND "Has Mobile" = true THEN 1 ELSE 0 END) as has_both,
                    SUM(CASE WHEN "Has Aadhaar" = false AND "Has Mobile" = false THEN 1 ELSE 0 END) as has_neither
                FROM "{csv_file}"
            '''
            
            coverage_stats = con.execute(coverage_query).df().iloc[0]
            
            total = int(coverage_stats['total_students'])
            aadhaar_count = int(coverage_stats['has_aadhaar'])
            mobile_count = int(coverage_stats['has_mobile'])
            both_count = int(coverage_stats['has_both'])
            neither_count = int(coverage_stats['has_neither'])
            
            aadhaar_pct = (aadhaar_count / total * 100) if total > 0 else 0
            mobile_pct = (mobile_count / total * 100) if total > 0 else 0
            both_pct = (both_count / total * 100) if total > 0 else 0
            neither_pct = (neither_count / total * 100) if total > 0 else 0
            
        except Exception as e:
            st.error(f"❌ Error: {e}")
            aadhaar_count = mobile_count = both_count = neither_count = 0
            aadhaar_pct = mobile_pct = both_pct = neither_pct = 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    coverage_metrics = [
        ("🆔 Aadhaar Coverage", aadhaar_count, aadhaar_pct, col1, "#667eea", "#764ba2"),
        ("📱 Mobile Coverage", mobile_count, mobile_pct, col2, "#f093fb", "#f5576c"),
        ("✅ Both Available", both_count, both_pct, col3, "#4facfe", "#00f2fe"),
        ("⚠️ Neither Available", neither_count, neither_pct, col4, "#fa709a", "#fee140")
    ]
    
    for title, count, pct, column, color1, color2 in coverage_metrics:
        with column:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, {color1}, {color2}); 
                        padding: 2rem; border-radius: 15px; text-align: center; 
                        box-shadow: 0 8px 16px rgba(0,0,0,0.2); height: 180px; 
                        display: flex; flex-direction: column; justify-content: center;'>
                <h3 style='color: white; margin: 0; font-size: 1.1rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>{title}</h3>
                <p style='color: white; font-size: 2.5rem; font-weight: bold; margin: 0.5rem 0 0 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{count:,}</p>
                <p style='color: white; font-size: 1.2rem; margin: 0; opacity: 0.9;'>{pct:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # ROW 2: Quick Download Reports
    st.markdown("### 📥 Quick Download Reports")
    st.markdown("<p style='color: white; font-size: 1rem; opacity: 0.9;'>Click any button to generate and download the report</p>", unsafe_allow_html=True)
    
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    col_d5, col_d6, col_d7, col_d8 = st.columns(4)
    
    # Report 1: Top 50 Critical Schools
    with col_d1:
        if st.button("🏫 Top 50 Critical Schools", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    critical_query = f'''
                        SELECT "Last School Name", "District Name", "Block Name", 
                               COUNT(*) as dropout_count
                        FROM "{csv_file}"
                        WHERE "Last School Name" IS NOT NULL AND "Last School Name" != ''
                        GROUP BY "Last School Name", "District Name", "Block Name"
                        ORDER BY dropout_count DESC
                        LIMIT 50
                    '''
                    df_critical = con.execute(critical_query).df()
                    csv = df_critical.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name="top_50_critical_schools.csv",
                        mime="text/csv"
                    )
                    st.success("✅ Report generated!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    # Report 2: District Summary
    with col_d2:
        if st.button("🗺️ District Summary", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    district_summary_query = f'''
                        SELECT "District Name", 
                               COUNT(*) as total_dropouts,
                               SUM(CASE WHEN "Gender" = '{FEMALE_VALUE}' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN "Gender" = '{MALE_VALUE}' THEN 1 ELSE 0 END) as boys,
                               SUM(CASE WHEN "Has Aadhaar" = true THEN 1 ELSE 0 END) as with_aadhaar,
                               SUM(CASE WHEN "Has Mobile" = true THEN 1 ELSE 0 END) as with_mobile
                        FROM "{csv_file}"
                        GROUP BY "District Name"
                        ORDER BY total_dropouts DESC
                    '''
                    df_dist_summary = con.execute(district_summary_query).df()
                    csv = df_dist_summary.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name="district_summary.csv",
                        mime="text/csv"
                    )
                    st.success("✅ Report generated!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    # Report 3: Block Summary
    with col_d3:
        if st.button("🏘️ Block Summary", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    block_summary_query = f'''
                        SELECT "District Name", "Block Name", 
                               COUNT(*) as total_dropouts,
                               SUM(CASE WHEN "Gender" = '{FEMALE_VALUE}' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN "Gender" = '{MALE_VALUE}' THEN 1 ELSE 0 END) as boys
                        FROM "{csv_file}"
                        GROUP BY "District Name", "Block Name"
                        ORDER BY total_dropouts DESC
                    '''
                    df_block_summary = con.execute(block_summary_query).df()
                    csv = df_block_summary.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name="block_summary.csv",
                        mime="text/csv"
                    )
                    st.success("✅ Report generated!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    # Report 4: Management Type Analysis
    with col_d4:
        if st.button("🏛️ Management Type", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    mgmt_query = f'''
                        SELECT "Management Type Label", "School Management",
                               COUNT(*) as total_dropouts,
                               SUM(CASE WHEN "Gender" = '{FEMALE_VALUE}' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN "Gender" = '{MALE_VALUE}' THEN 1 ELSE 0 END) as boys
                        FROM "{csv_file}"
                        GROUP BY "Management Type Label", "School Management"
                        ORDER BY total_dropouts DESC
                    '''
                    df_mgmt = con.execute(mgmt_query).df()
                    csv = df_mgmt.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name="management_type_analysis.csv",
                        mime="text/csv"
                    )
                    st.success("✅ Report generated!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    # Report 5: Last Class Breakdown
    with col_d5:
        if st.button("📚 Last Class Breakdown", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    class_query = f'''
                        SELECT "Last Class", "Education Level",
                               COUNT(*) as total_students,
                               SUM(CASE WHEN "Gender" = '{FEMALE_VALUE}' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN "Gender" = '{MALE_VALUE}' THEN 1 ELSE 0 END) as boys
                        FROM "{csv_file}"
                        GROUP BY "Last Class", "Education Level"
                        ORDER BY "Last Class"
                    '''
                    df_class = con.execute(class_query).df()
                    csv = df_class.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name="last_class_breakdown.csv",
                        mime="text/csv"
                    )
                    st.success("✅ Report generated!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    # Report 6: Student Sub Status
    with col_d6:
        if st.button("📊 Student Sub Status", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    status_query = f'''
                        SELECT "Student Sub Status", "District Name",
                               COUNT(*) as total_students
                        FROM "{csv_file}"
                        GROUP BY "Student Sub Status", "District Name"
                        ORDER BY total_students DESC
                    '''
                    df_status = con.execute(status_query).df()
                    csv = df_status.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name="student_sub_status_report.csv",
                        mime="text/csv"
                    )
                    st.success("✅ Report generated!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    # Report 7: Year-wise Summary
    with col_d7:
        if st.button("📅 Year-wise Summary", use_container_width=True):
            with st.spinner("Generating report..."):
                try:
                    year_query = f'''
                        SELECT "Academic Year", 
                               COUNT(*) as total_dropouts,
                               SUM(CASE WHEN "Gender" = '{FEMALE_VALUE}' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN "Gender" = '{MALE_VALUE}' THEN 1 ELSE 0 END) as boys,
                               COUNT(DISTINCT "District Name") as districts_affected,
                               COUNT(DISTINCT "Block Name") as blocks_affected
                        FROM "{csv_file}"
                        GROUP BY "Academic Year"
                        ORDER BY "Academic Year" DESC
                    '''
                    df_year = con.execute(year_query).df()
                    csv = df_year.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv,
                        file_name="yearwise_summary.csv",
                        mime="text/csv"
                    )
                    st.success("✅ Report generated!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # ROW 3: Custom Report Generator
    st.markdown("### 🔧 Custom Report Generator")
    st.markdown("<p style='color: white; font-size: 1rem; opacity: 0.9;'>Create customized reports with specific filters and columns</p>", unsafe_allow_html=True)
    
    with st.expander("🔍 Build Custom Report", expanded=False):
        # Report Name
        report_name = st.text_input("Report Name:", value="custom_report", help="Enter a name for your report file")
        
        # Filters
        st.markdown("#### 📋 Select Filters")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            filter_year = st.multiselect("Academic Year:", available_years, default=[])
            
            # District filter - depends on Year
            try:
                if len(filter_year) == 0:
                    districts_query = f'SELECT DISTINCT "District Name" FROM "{csv_file}" ORDER BY "District Name"'
                else:
                    year_list = "','".join(filter_year)
                    districts_query = f'SELECT DISTINCT "District Name" FROM "{csv_file}" WHERE "Academic Year" IN (\'{year_list}\') ORDER BY "District Name"'
                districts = con.execute(districts_query).df()['District Name'].tolist()
            except:
                districts = []
            filter_district = st.multiselect("District:", districts, default=[])
            
            # Block filter - depends on District
            try:
                if len(filter_district) == 0:
                    blocks_query = f'SELECT DISTINCT "Block Name" FROM "{csv_file}" ORDER BY "Block Name" LIMIT 500'
                else:
                    dist_list = "','".join(filter_district)
                    blocks_query = f'SELECT DISTINCT "Block Name" FROM "{csv_file}" WHERE "District Name" IN (\'{dist_list}\') ORDER BY "Block Name"'
                blocks = con.execute(blocks_query).df()['Block Name'].tolist()
            except:
                blocks = []
            filter_block = st.multiselect("Block:", blocks, default=[])
        
        with col_f2:
            try:
                school_categories = con.execute(f'SELECT DISTINCT "School Category" FROM "{csv_file}" ORDER BY "School Category"').df()['School Category'].tolist()
            except:
                school_categories = []
            filter_school_category = st.multiselect("School Category:", school_categories, default=[])
            
            try:
                mgmt_types = con.execute(f'SELECT DISTINCT "Management Type Label" FROM "{csv_file}" ORDER BY "Management Type Label"').df()['Management Type Label'].tolist()
            except:
                mgmt_types = []
            filter_mgmt = st.multiselect("Management Type Label:", mgmt_types, default=[])
            
            # School filter - depends on District and Block
            try:
                school_conditions = []
                if len(filter_district) > 0:
                    dist_list = "','".join(filter_district)
                    school_conditions.append(f'"District Name" IN (\'{dist_list}\')')
                if len(filter_block) > 0:
                    block_list = "','".join(filter_block)
                    school_conditions.append(f'"Block Name" IN (\'{block_list}\')')
                
                where_clause = " AND ".join(school_conditions) if school_conditions else "1=1"
                schools_query = f'SELECT DISTINCT "Last School Name" FROM "{csv_file}" WHERE {where_clause} AND "Last School Name" IS NOT NULL AND "Last School Name" != \'\' ORDER BY "Last School Name" LIMIT 200'
                schools = con.execute(schools_query).df()['Last School Name'].tolist()
            except:
                schools = []
            filter_school = st.multiselect("Last School Name:", schools, default=[])
        
        with col_f3:
            filter_gender = st.multiselect("Gender:", ["FEMALE", "MALE"], default=[])
            
            try:
                sub_statuses = con.execute(f'SELECT DISTINCT "Student Sub Status" FROM "{csv_file}" ORDER BY "Student Sub Status"').df()['Student Sub Status'].tolist()
            except:
                sub_statuses = []
            filter_status = st.multiselect("Student Sub Status:", sub_statuses, default=[])
            
            # Last Class filter - depends on School Category (Education Level mapping)
            try:
                if len(filter_school_category) == 0:
                    classes_query = f'SELECT DISTINCT "Last Class" FROM "{csv_file}" ORDER BY "Last Class"'
                else:
                    # Map School Category to Education Level
                    edu_level_mapping = {
                        'Primary School': 'Primary (1-5)',
                        'Upper Primary School': 'Upper Primary (6-8)',
                        'Secondary School': 'Secondary (9-10)',
                        'Higher Secondary School': 'Sr. Secondary (11-12)',
                        'High School': 'Secondary (9-10)'
                    }
                    
                    # Get corresponding education levels
                    edu_levels = []
                    for cat in filter_school_category:
                        if cat in edu_level_mapping:
                            edu_levels.append(edu_level_mapping[cat])
                    
                    if edu_levels:
                        edu_list = "','".join(edu_levels)
                        classes_query = f'SELECT DISTINCT "Last Class" FROM "{csv_file}" WHERE "Education Level" IN (\'{edu_list}\') ORDER BY "Last Class"'
                    else:
                        # If no mapping found, get classes from selected categories directly
                        cat_list = "','".join(filter_school_category)
                        classes_query = f'SELECT DISTINCT "Last Class" FROM "{csv_file}" WHERE "School Category" IN (\'{cat_list}\') ORDER BY "Last Class"'
                
                classes = con.execute(classes_query).df()['Last Class'].tolist()
                classes = [str(c) for c in classes if c is not None]
            except:
                classes = []
            filter_class = st.multiselect("Last Class:", classes, default=[])
        
        # Fixed column selection - always the same columns
        st.markdown("#### 📊 Output Columns (Fixed)")
        st.info("Report will include: Academic Year, District Name, Block Name, Last UDISE Code, School Category, Last School Name, Student PEN, Student State Code, Student Name, Gender, Mobile No., Mother Name, Father Name, Student Sub Status, Last Class, Eligible Class to Import, APAAR Generated, Management Type Label, Education Level, Critical Dropout Point, Has Mobile, Has Aadhaar, Has State Code")
        
        output_columns = ["Academic Year", "District Name", "Block Name", "Last UDISE Code", "School Category", 
                         "Last School Name", "Student PEN", "Student State Code", "Student Name", "Gender", 
                         "Mobile No.", "Mother Name", "Father Name", "Student Sub Status", "Last Class", 
                         "Eligible Class to Import", "APAAR Generated", "Management Type Label", 
                         "Education Level", "Critical Dropout Point", "Has Mobile", "Has Aadhaar", "Has State Code"]
        
        # Generate Button
        if st.button("🚀 Generate Custom Report", type="primary", use_container_width=True):
            with st.spinner("Generating custom report..."):
                try:
                    # Build WHERE clause
                    where_conditions = []
                    
                    if len(filter_year) > 0:
                        year_list = "','".join(filter_year)
                        where_conditions.append(f"\"Academic Year\" IN ('{year_list}')")
                    
                    if len(filter_district) > 0:
                        dist_list = "','".join(filter_district)
                        where_conditions.append(f"\"District Name\" IN ('{dist_list}')")
                    
                    if len(filter_block) > 0:
                        block_list = "','".join(filter_block)
                        where_conditions.append(f"\"Block Name\" IN ('{block_list}')")
                    
                    if len(filter_school_category) > 0:
                        cat_list = "','".join(filter_school_category)
                        where_conditions.append(f"\"School Category\" IN ('{cat_list}')")
                    
                    if len(filter_mgmt) > 0:
                        mgmt_list = "','".join(filter_mgmt)
                        where_conditions.append(f"\"Management Type Label\" IN ('{mgmt_list}')")
                    
                    if len(filter_school) > 0:
                        school_list = "','".join(filter_school)
                        where_conditions.append(f"\"Last School Name\" IN ('{school_list}')")
                    
                    if len(filter_gender) > 0:
                        gender_list = "','".join(filter_gender)
                        where_conditions.append(f"\"Gender\" IN ('{gender_list}')")
                    
                    if len(filter_status) > 0:
                        status_list = "','".join(filter_status)
                        where_conditions.append(f"\"Student Sub Status\" IN ('{status_list}')")
                    
                    if len(filter_class) > 0:
                        class_list = "','".join(filter_class)
                        where_conditions.append(f"\"Last Class\" IN ('{class_list}')")
                    
                    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                    
                    # Build SELECT clause with fixed columns
                    select_cols = '", "'.join(output_columns)
                    
                    custom_query = f'''
                        SELECT "{select_cols}"
                        FROM "{csv_file}"
                        WHERE {where_clause}
                        LIMIT 50000
                    '''
                    
                    df_custom = con.execute(custom_query).df()
                    
                    if df_custom.empty:
                        st.warning("⚠️ No data found with the selected filters!")
                    else:
                        csv = df_custom.to_csv(index=False).encode('utf-8')
                        st.success(f"✅ Report generated with {len(df_custom):,} records!")
                        st.download_button(
                            label=f"⬇️ Download {report_name}.csv",
                            data=csv,
                            file_name=f"{report_name}.csv",
                            mime="text/csv",
                            type="primary"
                        )
                        
                        # Show preview
                        st.markdown("#### Preview (First 10 rows)")
                        st.dataframe(df_custom.head(10), use_container_width=True)
                
                except Exception as e:
                    st.error(f"❌ Error generating report: {e}")

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: white; padding: 1.5rem; background: rgba(0,0,0,0.2); border-radius: 10px;'>
    <p style='font-size: 1.1rem; margin: 0;'>🎓 उत्तर प्रदेश शिक्षा विभाग | UP Education Department</p>
    <p style='font-size: 0.9rem; opacity: 0.8; margin-top: 0.5rem;'>Dashboard powered by DuckDB & Streamlit</p>
</div>
""", unsafe_allow_html=True)
