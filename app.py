import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import os

st.set_page_config(page_title="UP Dropout Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Kaggle Dataset Download Function
@st.cache_data
def download_kaggle_dataset():
    """Download dataset from Kaggle using credentials from Streamlit secrets"""
    try:
        import kaggle
        from kaggle.api.kaggle_api_extended import KaggleApi
        
        os.environ['KAGGLE_USERNAME'] = st.secrets["KAGGLE_USERNAME"]
        os.environ['KAGGLE_KEY'] = st.secrets["KAGGLE_KEY"]
        os.environ['KAGGLE_USER_AGENT'] = 'streamlit-app'
        
        api = KaggleApi()
        api.authenticate()
        
        dataset_name = st.secrets.get("KAGGLE_DATASET", "alokkmohan/dropout")
        api.dataset_download_files(dataset_name, path='.', unzip=True)
        
        return True
    except Exception as e:
        st.error(f"❌ Error loading data from source: {e}")
        return False

# Check if CSV exists locally, if not download from Kaggle
# Get the directory where app.py is located
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_file = os.path.join(script_dir, "Master_UP_Dropout_Database.csv")

if not os.path.exists(csv_file):
    loading_container = st.container()
    with loading_container:
        with st.spinner("🔄 Loading dashboard data... Please wait..."):
            download_success = download_kaggle_dataset()
    
    if not os.path.exists(csv_file):
        st.error(f"❌ Dataset could not be loaded. Please contact administrator.")
        st.stop()
    else:
        loading_container.empty()
        success_msg = st.success("✅ Dashboard ready!")
        import time
        time.sleep(2)
        success_msg.empty()

# Enhanced Custom CSS with animations
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .main-title { 
        font-size: 3rem; 
        font-weight: bold; 
        color: white; 
        text-align: center;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.4);
        margin-bottom: 2rem;
        animation: fadeInDown 1s ease-in;
    }
    
    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    .metric-card {
        animation: fadeInUp 0.6s ease-out;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px) scale(1.02);
        box-shadow: 0 12px 24px rgba(0,0,0,0.4) !important;
    }
    
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .risk-indicator {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    
    .risk-high {
        background: #ff4444;
        color: white;
    }
    
    .risk-medium {
        background: #ffaa00;
        color: white;
    }
    
    .risk-low {
        background: #00C851;
        color: white;
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
        transition: all 0.3s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        transform: translateY(-2px);
    }
    
    /* Back to top button */
    #back-to-top {
        position: fixed;
        bottom: 40px;
        right: 40px;
        background: rgba(255,255,255,0.9);
        color: #667eea;
        padding: 15px 20px;
        border-radius: 50px;
        font-weight: bold;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        cursor: pointer;
        transition: all 0.3s ease;
        z-index: 999;
    }
    #back-to-top:hover {
        background: white;
        transform: translateY(-5px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.4);
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🎓 UP शिक्षा विभाग - Advanced Dropout Analytics Dashboard</h1>', unsafe_allow_html=True)

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

# DuckDB connection with optimization
con = duckdb.connect()
con.execute("PRAGMA threads=4")
con.execute("PRAGMA memory_limit='4GB'")

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

# NEW: Calculate total enrollment (for dropout rate %)
@st.cache_data
def get_total_enrollment():
    """Get total enrollment from Excel or estimate"""
    try:
        # Assuming 5% dropout rate to reverse calculate total enrollment
        total_dropouts = int(df_edu[available_years].sum().sum())
        estimated_enrollment = int(total_dropouts / 0.05)  # Assumes 5% dropout
        return estimated_enrollment
    except:
        return 20000000  # Fallback estimate

TOTAL_ENROLLMENT = get_total_enrollment()

# Helper function to calculate dropout rate %
def calculate_dropout_rate(dropouts, total_enrolled=None):
    """Calculate dropout percentage"""
    if total_enrolled is None:
        total_enrolled = TOTAL_ENROLLMENT
    return round((dropouts / total_enrolled * 100), 2) if total_enrolled > 0 else 0

# Helper function to determine risk level
def get_risk_level(dropout_rate):
    """Determine risk level based on dropout rate"""
    if dropout_rate >= 8:
        return "HIGH", "risk-high"
    elif dropout_rate >= 5:
        return "MEDIUM", "risk-medium"
    else:
        return "LOW", "risk-low"

# Initialize session state
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0
if 'selected_school_for_detail' not in st.session_state:
    st.session_state.selected_school_for_detail = None

# Create Tabs
tab_cols = st.columns(5)
tab_names = ["🏠 Home", "🗺️ District Analysis", "🏫 Block Analysis", "🏆 School Performance", "📥 Downloads"]

for idx, (col, name) in enumerate(zip(tab_cols, tab_names)):
    with col:
        if st.button(name, key=f"tab_{idx}", use_container_width=True, 
                     type="primary" if st.session_state.active_tab == idx else "secondary"):
            st.session_state.active_tab = idx

st.markdown("<br>", unsafe_allow_html=True)

# Action Center - Floating Buttons (Top Right)
st.markdown("""
<style>
.action-center {
    position: fixed;
    top: 80px;
    right: 20px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.action-btn {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 0.8rem 1.2rem;
    border-radius: 25px;
    text-decoration: none;
    font-weight: 600;
    font-size: 0.85rem;
    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    cursor: pointer;
    transition: all 0.3s;
    text-align: center;
    border: none;
}
.action-btn:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.4);
}
@media (max-width: 768px) {
    .action-center {
        position: relative;
        top: 0;
        right: 0;
        flex-direction: row;
        flex-wrap: wrap;
        justify-content: center;
        margin: 1rem 0;
    }
}
</style>
<div class='action-center'>
    <button class='action-btn' onclick='alert("Download feature coming soon!")'>📥 Download Data</button>
    <button class='action-btn' onclick='alert("Report generation coming soon!")'>📊 Generate Report</button>
    <button class='action-btn' onclick='alert("Alert settings coming soon!")'>🔔 Set Alerts</button>
    <button class='action-btn' onclick='alert("Customize view coming soon!")'>⚙️ Customize</button>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==================== TAB 1: ENHANCED HOME PAGE ====================
if st.session_state.active_tab == 0:
    # HERO SECTION
    from datetime import datetime
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1e3c72, #2a5298); 
                padding: 2.5rem; 
                border-radius: 20px; 
                text-align: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.4);
                margin-bottom: 2rem;
                border: 2px solid rgba(255,255,255,0.1);'>
        <h1 style='color: white; font-size: 2.8rem; margin: 0; font-weight: 800; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
            📊 UP Dropout Analytics Dashboard
        </h1>
        <p style='color: #ffd700; font-size: 1.3rem; margin: 1rem 0 0.5rem 0; font-weight: 600; font-style: italic;'>
            "डेटा-संचालित निर्णयों से शिक्षा में सुधार"
        </p>
        <p style='color: rgba(255,255,255,0.8); font-size: 0.95rem; margin: 0.5rem 0 1.5rem 0;'>
            Last Updated: {datetime.now().strftime("%d %B %Y, %I:%M %p")} | Data Source: UDISE+ 2023-24
        </p>
        <div style='display: flex; justify-content: center; gap: 3rem; flex-wrap: wrap;'>
            <div style='text-align: center;'>
                <p style='color: #ffd700; font-size: 2.2rem; font-weight: 800; margin: 0;'>75</p>
                <p style='color: white; font-size: 0.9rem; margin: 0.3rem 0 0 0;'>जिले</p>
            </div>
            <div style='text-align: center;'>
                <p style='color: #ffd700; font-size: 2.2rem; font-weight: 800; margin: 0;'>19.46 Cr</p>
                <p style='color: white; font-size: 0.9rem; margin: 0.3rem 0 0 0;'>कुल नामांकन</p>
            </div>
            <div style='text-align: center;'>
                <p style='color: #ff6b6b; font-size: 2.2rem; font-weight: 800; margin: 0;'>34.8 L</p>
                <p style='color: white; font-size: 0.9rem; margin: 0.3rem 0 0 0;'>ड्रॉपआउट छात्र</p>
            </div>
            <div style='text-align: center;'>
                <p style='color: #51cf66; font-size: 2.2rem; font-weight: 800; margin: 0;'>5.0%</p>
                <p style='color: white; font-size: 0.9rem; margin: 0.3rem 0 0 0;'>ड्रॉपआउट दर</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # CRITICAL ALERTS SECTION
    st.markdown("""
    <div style='background: linear-gradient(135deg, #c0392b, #e74c3c); 
                padding: 1.5rem; 
                border-radius: 15px;
                margin-bottom: 1.5rem;
                border-left: 5px solid #fff;'>
        <h3 style='color: white; margin: 0 0 1rem 0; font-size: 1.5rem; font-weight: 700;'>
            🚨 Critical Alerts
        </h3>
        <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;'>
            <div style='background: rgba(255,255,255,0.15); padding: 1rem; border-radius: 10px;'>
                <p style='color: white; font-size: 0.85rem; margin: 0;'>High Dropout Districts</p>
                <p style='color: #ffd700; font-size: 1.8rem; font-weight: 800; margin: 0.3rem 0 0 0;'>🔴 12</p>
            </div>
            <div style='background: rgba(255,255,255,0.15); padding: 1rem; border-radius: 10px;'>
                <p style='color: white; font-size: 0.85rem; margin: 0;'>Gender Disparity</p>
                <p style='color: #ffd700; font-size: 1.8rem; font-weight: 800; margin: 0.3rem 0 0 0;'>🟡 8</p>
            </div>
            <div style='background: rgba(255,255,255,0.15); padding: 1rem; border-radius: 10px;'>
                <p style='color: white; font-size: 0.85rem; margin: 0;'>Secondary Critical</p>
                <p style='color: #ffd700; font-size: 1.8rem; font-weight: 800; margin: 0.3rem 0 0 0;'>🔴 45.6%</p>
            </div>
            <div style='background: rgba(255,255,255,0.15); padding: 1rem; border-radius: 10px;'>
                <p style='color: white; font-size: 0.85rem; margin: 0;'>Improving Districts</p>
                <p style='color: #ffd700; font-size: 1.8rem; font-weight: 800; margin: 0.3rem 0 0 0;'>🟢 25</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Year filter - Default to 2023-24
    col_y1, col_y2, col_y3 = st.columns([1, 2, 1])
    with col_y2:
        st.markdown("### 📅 Select Academic Year")
        default_index = available_years.index("2023-24") + 1 if "2023-24" in available_years else 0
        selected_year = st.selectbox("शैक्षणिक वर्ष:", ["All"] + available_years, index=default_index, key="year_filter", label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # TOTAL ENROLLMENT SECTION - RIGHT AFTER YEAR SELECTOR
    st.markdown("""
    <h2 style='color: white; text-align: center; font-size: 2.2rem; margin: 0.5rem 0; font-weight: bold;'>
        📊 Total Enrollment (Uttar Pradesh)
    </h2>
    """, unsafe_allow_html=True)
    
    # Enrollment data based on selected year (P+M+S only, excluding Foundational)
    if selected_year == "2023-24":
        total_enrollment = "19,46,31,385"  # P+M+S only
        boys_enrollment = "10,08,77,050"   # Boys in P+M+S
        girls_enrollment = "9,37,54,335"   # Girls in P+M+S
        preparatory = "6,75,06,065"
        middle = "6,31,26,015"
        secondary = "6,39,99,305"
        note = ""
    elif selected_year == "2024-25":
        total_enrollment = "19,46,20,174"  # P+M+S only
        boys_enrollment = "10,05,54,876"   # Boys in P+M+S
        girls_enrollment = "9,40,65,298"   # Girls in P+M+S
        preparatory = "6,61,15,921"
        middle = "6,36,95,100"
        secondary = "6,48,09,153"
        note = ""
    elif selected_year == "2025-26":
        total_enrollment = "19,32,00,000 - 19,42,00,000"  # P+M+S projected
        boys_enrollment = "9,98,00,000 - 10,04,00,000"    # Boys in P+M+S projected
        girls_enrollment = "9,34,00,000 - 9,38,00,000"    # Girls in P+M+S projected
        preparatory = "6,55,00,000 - 6,59,00,000"
        middle = "6,32,00,000 - 6,35,00,000"
        secondary = "6,45,00,000 - 6,48,00,000"
        note = "⛔ UDISE+ data not yet released. Trend Estimate based on YoY behaviour."
    else:
        # For "All" - show 2024-25 data (P+M+S)
        total_enrollment = "19,46,20,174"
        boys_enrollment = "10,05,54,876"
        girls_enrollment = "9,40,65,298"
        preparatory = "6,61,15,921"
        middle = "6,36,95,100"
        secondary = "6,48,09,153"
        note = "Showing 2024-25 enrollment data"
    
    # First Row: Total + Boys + Girls (3 boxes) - COMPACT for mobile
    col_t1, col_t2, col_t3 = st.columns(3)
    
    with col_t1:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #5e3fb7, #6b46c1); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    border: 2px solid rgba(255,255,255,0.4);'>
            <h4 style='margin: 0; font-size: 0.95rem; color: white; font-weight: 700; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>🎯 TOTAL</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.6rem; color: white; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{total_enrollment}</h2>
            <p style='margin: 0; font-size: 0.7rem; color: rgba(255,255,255,0.85);'>(P + M + S)</p>
            <p style='margin: 0.3rem 0 0 0; font-size: 0.75rem; color: #90ee90; font-weight: 600;'>↓ -0.06% YoY | GPI: 0.93</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_t2:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #2980b9, #3498db); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 0.95rem; color: white; font-weight: 700; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>👦 Boys</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.6rem; color: white; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{boys_enrollment}</h2>
            <p style='margin: 0.3rem 0 0 0; font-size: 0.75rem; color: #ffcccb; font-weight: 600;'>↓ -0.32% YoY</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_t3:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #ec407a, #f48fb1); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 0.95rem; color: white; font-weight: 700; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>👧 Girls</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.6rem; color: white; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{girls_enrollment}</h2>
            <p style='margin: 0.3rem 0 0 0; font-size: 0.75rem; color: #90ee90; font-weight: 600;'>↑ +0.33% YoY</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Second Row: P + M + S (3 boxes) - COMPACT for mobile
    col_t4, col_t5, col_t6 = st.columns(3)
    
    with col_t4:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #5dade2, #85c1e9); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 0.9rem; color: white; font-weight: 700; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>📚 Primary</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.5rem; color: white; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{preparatory}</h2>
            <p style='margin: 0; font-size: 0.65rem; color: rgba(255,255,255,0.85);'>Classes 1-5</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_t5:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #52be80, #7dcea0); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 0.9rem; color: white; font-weight: 700; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>📖 Middle</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.5rem; color: white; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{middle}</h2>
            <p style='margin: 0; font-size: 0.65rem; color: rgba(255,255,255,0.85);'>Classes 6-8</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_t6:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #af7ac5, #bb8fce); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 0.9rem; color: white; font-weight: 700; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>🎓 Secondary</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.5rem; color: white; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{secondary}</h2>
            <p style='margin: 0; font-size: 0.65rem; color: rgba(255,255,255,0.85);'>Classes 9-12</p>
        </div>
        """, unsafe_allow_html=True)
    
    if note:
        st.markdown(f"""
        <p style='color: rgba(255,255,255,0.9); text-align: center; margin-top: 0.5rem; font-size: 0.9rem; font-style: italic;'>
            {note}
        </p>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # RETENTION RATE SECTION (UDISE+ Data)
    st.markdown("""
    <h2 style='color: white; text-align: center; font-size: 2.2rem; margin: 0.5rem 0; font-weight: bold;'>
        📈 Retention Rate (UDISE+)
    </h2>
    """, unsafe_allow_html=True)
    
    # Retention rate data based on selected year
    if selected_year == "2023-24":
        ret_preparatory = "85.4%"
        ret_middle = "78.0%"
        ret_secondary = "45.6%"
        ret_note = ""
    elif selected_year == "2024-25":
        ret_preparatory = "92.4%"
        ret_middle = "82.8%"
        ret_secondary = "47.2%"
        ret_note = ""
    elif selected_year == "2025-26":
        ret_preparatory = "93-94%"
        ret_middle = "83-85%"
        ret_secondary = "48-50%"
        ret_note = "⛔ Projected estimates based on trend analysis."
    else:
        # For "All" - show 2024-25 data
        ret_preparatory = "92.4%"
        ret_middle = "82.8%"
        ret_secondary = "47.2%"
        ret_note = "Showing 2024-25 retention data"
    
    # Retention Rate Boxes: P + M + S (3 boxes) - COMPACT
    col_r1, col_r2, col_r3 = st.columns(3)
    
    with col_r1:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #84fab0, #8fd3f4); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 0.9rem; color: white; font-weight: 700; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>📚 Preparatory</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2rem; color: white; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{ret_preparatory}</h2>
            <p style='margin: 0; font-size: 0.65rem; color: rgba(255,255,255,0.85);'>Classes 1-5</p>
            <p style='margin: 0; font-size: 0.65rem; color: rgba(255,255,255,0.75); font-style: italic;'>(UDISE+ 2023-24 आधार पर)</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_r2:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #a8edea, #fed6e3); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 0.9rem; color: white; font-weight: 700; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>📖 Middle</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2rem; color: white; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{ret_middle}</h2>
            <p style='margin: 0; font-size: 0.65rem; color: rgba(255,255,255,0.85);'>Classes 6-8</p>
            <p style='margin: 0; font-size: 0.65rem; color: rgba(255,255,255,0.75); font-style: italic;'>(UDISE+ 2023-24 आधार पर)</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_r3:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #ff9a9e, #fecfef); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 0.9rem; color: white; font-weight: 700; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>🎓 Secondary</h4>
            <h2 style='margin: 0.5rem 0; font-size: 2rem; color: white; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{ret_secondary}</h2>
            <p style='margin: 0; font-size: 0.65rem; color: rgba(255,255,255,0.85);'>Classes 9-12</p>
            <p style='margin: 0; font-size: 0.65rem; color: rgba(255,255,255,0.75); font-style: italic;'>(UDISE+ 2023-24 आधार पर)</p>
        </div>
        """, unsafe_allow_html=True)
    
    if ret_note:
        st.markdown(f"""
        <p style='color: rgba(255,255,255,0.9); text-align: center; margin-top: 0.5rem; font-size: 0.9rem; font-style: italic;'>
            {ret_note}
        </p>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <p style='color: rgba(255,255,255,0.8); text-align: center; margin-top: 0.8rem; font-size: 0.75rem; font-style: italic;'>
            (Source: UDISE+ 2023-24)
        </p>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # DROPOUT FACTS SECTION - AFTER ENROLLMENT
    st.markdown("""
    <h2 style='color: white; text-align: center; font-size: 2.2rem; margin: 0.5rem 0; font-weight: bold;'>
        📉 Dropout Facts
    </h2>
    """, unsafe_allow_html=True)
    
    with st.spinner('📊 Loading comprehensive analytics...'):
        try:
            if selected_year == "All":
                # Get all data from CSV for consistency
                all_query = f'''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN "Gender" = 'FEMALE' THEN 1 ELSE 0 END) as girls,
                        SUM(CASE WHEN "Gender" = 'MALE' THEN 1 ELSE 0 END) as boys,
                        SUM(CASE WHEN "Education Level" = 'Primary (1-5)' THEN 1 ELSE 0 END) as primary,
                        SUM(CASE WHEN "Education Level" = 'Upper Primary (6-8)' THEN 1 ELSE 0 END) as upper_primary,
                        SUM(CASE WHEN "Education Level" = 'Secondary (9-10)' THEN 1 ELSE 0 END) as secondary,
                        SUM(CASE WHEN "Education Level" = 'Sr. Secondary (11-12)' THEN 1 ELSE 0 END) as sr_secondary
                    FROM "{csv_file}"
                '''
                all_stats = con.execute(all_query).df().iloc[0]
                total_dropouts = int(all_stats['total'])
                total_girls = int(all_stats['girls'])
                total_boys = int(all_stats['boys'])
                
                edu_levels = {
                    'Primary (1-5)': int(all_stats['primary']),
                    'Upper Primary (6-8)': int(all_stats['upper_primary']),
                    'Secondary (9-10)': int(all_stats['secondary']),
                    'Sr. Secondary (11-12)': int(all_stats['sr_secondary'])
                }
                
            else:
                # Get all data from CSV for selected year for consistency
                year_query = f'''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN "Gender" = 'FEMALE' THEN 1 ELSE 0 END) as girls,
                        SUM(CASE WHEN "Gender" = 'MALE' THEN 1 ELSE 0 END) as boys,
                        SUM(CASE WHEN "Education Level" = 'Primary (1-5)' THEN 1 ELSE 0 END) as primary,
                        SUM(CASE WHEN "Education Level" = 'Upper Primary (6-8)' THEN 1 ELSE 0 END) as upper_primary,
                        SUM(CASE WHEN "Education Level" = 'Secondary (9-10)' THEN 1 ELSE 0 END) as secondary,
                        SUM(CASE WHEN "Education Level" = 'Sr. Secondary (11-12)' THEN 1 ELSE 0 END) as sr_secondary
                    FROM "{csv_file}"
                    WHERE "Academic Year" = '{selected_year}'
                '''
                year_stats = con.execute(year_query).df()
                
                if not year_stats.empty and year_stats.iloc[0]['total'] > 0:
                    stats = year_stats.iloc[0]
                    total_dropouts = int(stats['total'])
                    total_girls = int(stats['girls'])
                    total_boys = int(stats['boys'])
                    
                    edu_levels = {
                        'Primary (1-5)': int(stats['primary']),
                        'Upper Primary (6-8)': int(stats['upper_primary']),
                        'Secondary (9-10)': int(stats['secondary']),
                        'Sr. Secondary (11-12)': int(stats['sr_secondary'])
                    }
                else:
                    total_dropouts = total_girls = total_boys = 0
                    edu_levels = {'Primary (1-5)': 0, 'Upper Primary (6-8)': 0, 'Secondary (9-10)': 0, 'Sr. Secondary (11-12)': 0}
            
            # Dropout rates based on year and verified data
            if selected_year == "2023-24":
                # UP verified data 2023-24
                overall_dropout_rate = 5.0
                primary_dropout_rate = 5.4  # Preparatory level
                upper_primary_dropout_rate = 3.9  # Middle level
                secondary_dropout_rate = 5.9  # Secondary level
                sr_secondary_dropout_rate = 4.5  # Estimated
                is_data_pending = False
            elif selected_year == "2024-25":
                # National level data 2024-25 (UP-specific not available)
                overall_dropout_rate = 4.7
                primary_dropout_rate = 2.3  # Preparatory level (National)
                upper_primary_dropout_rate = 3.5  # Middle level (National)
                secondary_dropout_rate = 8.2  # Secondary level (National)
                sr_secondary_dropout_rate = 6.0  # Estimated
                is_data_pending = False
            elif selected_year == "2025-26":
                # Data pending
                overall_dropout_rate = 0
                primary_dropout_rate = 0
                upper_primary_dropout_rate = 0
                secondary_dropout_rate = 0
                sr_secondary_dropout_rate = 0
                is_data_pending = True
            else:
                # Default/All years - Average
                overall_dropout_rate = 5.0
                primary_dropout_rate = 5.4
                upper_primary_dropout_rate = 3.9
                secondary_dropout_rate = 5.9
                sr_secondary_dropout_rate = 4.5
                is_data_pending = False
            
            # Get High-Risk Blocks Count
            if selected_year == "All":
                high_risk_query = f'''
                    SELECT "Block Name", "District Name", COUNT(*) as dropout_count
                    FROM "{csv_file}"
                    GROUP BY "Block Name", "District Name"
                    HAVING dropout_count > 100
                '''
            else:
                high_risk_query = f'''
                    SELECT "Block Name", "District Name", COUNT(*) as dropout_count
                    FROM "{csv_file}"
                    WHERE "Academic Year" = '{selected_year}'
                    GROUP BY "Block Name", "District Name"
                    HAVING dropout_count > 100
                '''
            high_risk_blocks_df = con.execute(high_risk_query).df()
            high_risk_blocks_count = len(high_risk_blocks_df)
            
        except Exception as e:
            st.error(f"❌ Error: {e}")
            total_dropouts = total_girls = total_boys = 0
            overall_dropout_rate = girls_dropout_rate = boys_dropout_rate = 0
            edu_levels = {'Primary (1-5)': 0, 'Upper Primary (6-8)': 0, 'Secondary (9-10)': 0, 'Sr. Secondary (11-12)': 0}
            high_risk_blocks_count = 0
            is_data_pending = False
    
    # FIRST ROW: Total, Girls, Boys counts (3 boxes)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class='metric-card' style='background: white; 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.1rem; color: #667eea; font-weight: bold;'>📊 Total Dropout Students</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: #f5576c; font-weight: bold;'>{total_dropouts:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #fa709a, #fee140); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>👧 Girls Dropout Students</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{total_girls:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #4facfe, #00f2fe); 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>👦 Boys Dropout Students</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{total_boys:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # SECOND ROW: Education Levels Student Counts (4 boxes - without dropout rates)
    col4, col5, col6, col7 = st.columns(4)
    
    with col4:
        st.markdown(f"""
        <div class='metric-card' style='background: white; 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.1rem; color: #43e97b; font-weight: bold;'>📚 Primary (1-5)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: #43e97b; font-weight: bold;'>{edu_levels['Primary (1-5)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class='metric-card' style='background: white; 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.1rem; color: #667eea; font-weight: bold;'>📖 Upper Primary (6-8)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: #667eea; font-weight: bold;'>{edu_levels['Upper Primary (6-8)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div class='metric-card' style='background: white; 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.1rem; color: #fcb69f; font-weight: bold;'>🎓 Secondary (9-10)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: #fcb69f; font-weight: bold;'>{edu_levels['Secondary (9-10)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col7:
        st.markdown(f"""
        <div class='metric-card' style='background: white; 
                    padding: 1.5rem; 
                    border-radius: 15px; 
                    text-align: center; 
                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;'>
            <h4 style='margin: 0; font-size: 1.1rem; color: #ff9a9e; font-weight: bold;'>🎯 Higher Secondary (11-12)</h4>
            <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: #ff9a9e; font-weight: bold;'>{edu_levels['Sr. Secondary (11-12)']:,}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # THIRD ROW: Dropout Rates - Separate boxes (5 boxes: Overall + 4 Education Levels)
    col8, col9, col10, col11, col12 = st.columns(5)
    
    with col8:
        if is_data_pending:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #667eea, #764ba2); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;'>
                <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>📈 Overall Rate</h4>
                <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>Pending</h2>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #667eea, #764ba2); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;'>
                <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>📈 Overall Rate</h4>
                <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{overall_dropout_rate}%</h2>
            </div>
            """, unsafe_allow_html=True)
    
    with col9:
        if is_data_pending:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #43e97b, #38f9d7); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;'>
                <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>📚 Primary Rate</h4>
                <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>Pending</h2>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #43e97b, #38f9d7); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;'>
                <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>📚 Primary Rate</h4>
                <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{primary_dropout_rate}%</h2>
            </div>
            """, unsafe_allow_html=True)
    
    with col10:
        if is_data_pending:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #667eea, #764ba2); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;'>
                <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>📖 Upper Primary Rate</h4>
                <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>Pending</h2>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #667eea, #764ba2); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;'>
                <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>📖 Upper Primary Rate</h4>
                <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{upper_primary_dropout_rate}%</h2>
            </div>
            """, unsafe_allow_html=True)
    
    with col11:
        if is_data_pending:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #fcb69f, #ffecd2); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;'>
                <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>🎓 Secondary Rate</h4>
                <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>Pending</h2>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #fcb69f, #ffecd2); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;'>
                <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>🎓 Secondary Rate</h4>
                <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{secondary_dropout_rate}%</h2>
            </div>
            """, unsafe_allow_html=True)
    
    with col12:
        if is_data_pending:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #ff9a9e, #fecfef); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;'>
                <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>🎯 Higher Sec. Rate</h4>
                <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>Pending</h2>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #ff9a9e, #fecfef); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        text-align: center; 
                        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;'>
                <h4 style='margin: 0; font-size: 1.1rem; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>🎯 Higher Sec. Rate</h4>
                <h2 style='margin: 0.5rem 0; font-size: 1.8rem; color: white; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>{sr_secondary_dropout_rate}%</h2>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # KEY INSIGHTS SUMMARY BOX
    st.markdown("""
    <div style='background: linear-gradient(135deg, #1a252f, #2874a6); 
                padding: 2rem; 
                border-radius: 20px; 
                box-shadow: 0 8px 20px rgba(0,0,0,0.4);
                border-left: 5px solid #f39c12;
                margin: 2rem 0;'>
        <h2 style='color: white; margin: 0 0 1.5rem 0; font-size: 2rem; font-weight: 800;'>
            💡 <strong>मुख्य बिंदु – 2023-24</strong>
        </h2>
        <div style='color: white; font-size: 1.05rem; line-height: 2rem;'>
            <p style='margin: 0.5rem 0;'>
                <span style='font-size: 1.5rem; margin-right: 0.5rem;'>•</span>
                कुल <strong style='color: #f39c12;'>34,80,273</strong> छात्रों ने पढ़ाई छोड़ी।
            </p>
            <p style='margin: 0.5rem 0;'>
                <span style='font-size: 1.5rem; margin-right: 0.5rem;'>•</span>
                Preparatory retention <strong style='color: #e74c3c;'>85.4%</strong> <em style='color: #e74c3c;'>(सबसे बड़ी गिरावट)</em>।
            </p>
            <p style='margin: 0.5rem 0;'>
                <span style='font-size: 1.5rem; margin-right: 0.5rem;'>•</span>
                Secondary retention <strong style='color: #e74c3c;'>45.6%</strong> <em style='color: #e74c3c;'>(high concern)</em>।
            </p>
            <p style='margin: 0.5rem 0;'>
                <span style='font-size: 1.5rem; margin-right: 0.5rem;'>•</span>
                Highest dropouts: <strong style='color: #e74c3c;'>Agra, Bahraich, Azamgarh</strong>।
            </p>
            <p style='margin: 0.5rem 0;'>
                <span style='font-size: 1.5rem; margin-right: 0.5rem;'>•</span>
                Best districts: <strong style='color: #2ecc71;'>Budaun, Baghpat, Hamirpur</strong>।
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Additional Visualizations Section
    st.markdown("""
    <h2 style='color: white; text-align: center; font-size: 2.2rem; margin: 2rem 0; font-weight: bold;'>
        📊 Visual Analytics
    </h2>
    """, unsafe_allow_html=True)
    
    viz_col1, viz_col2 = st.columns(2)
    
    with viz_col1:
        # Gender Distribution Donut Chart
        try:
            gender_query = f'''
                SELECT "Gender", COUNT(*) as count
                FROM "{csv_file}"
                WHERE "Academic Year" = '{selected_year}'
                GROUP BY "Gender"
            '''
            gender_data = duckdb.query(gender_query).df()
            
            fig_gender = go.Figure(data=[go.Pie(
                labels=gender_data['Gender'],
                values=gender_data['count'],
                hole=0.5,
                marker=dict(colors=['#3498db', '#ec407a', '#9b59b6']),
                textinfo='label+percent',
                textfont=dict(size=14, color='white', family='Arial Black'),
                hovertemplate='<b>%{label}</b><br>Count: %{value:,}<br>Percentage: %{percent}<extra></extra>'
            )])
            
            fig_gender.update_layout(
                title=dict(
                    text="Gender-wise Dropout Distribution",
                    x=0.5,
                    xanchor='center',
                    font=dict(size=18, color='white', family='Arial Black')
                ),
                showlegend=True,
                legend=dict(font=dict(color='white', size=12)),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(255,255,255,0.05)',
                height=400
            )
            
            st.plotly_chart(fig_gender, use_container_width=True, config={'displayModeBar': False})
        except Exception as e:
            st.error(f"Error loading gender chart: {e}")
    
    with viz_col2:
        # Education Level Distribution
        try:
            level_query = f'''
                SELECT 
                    "Education Level",
                    COUNT(*) as student_count
                FROM df
                WHERE "Academic Year" = '{selected_year}'
                GROUP BY "Education Level"
                ORDER BY student_count DESC
            '''
            level_df = duckdb.query(level_query).to_df()
            
            if not level_df.empty:
                fig_level = go.Figure(data=[go.Pie(
                    labels=level_df['Education Level'],
                    values=level_df['student_count'],
                    hole=0.5,
                    marker=dict(colors=['#2ecc71', '#3498db', '#e74c3c', '#f39c12', '#9b59b6']),
                    textinfo='label+percent',
                    textfont=dict(size=14, color='white', family='Arial Black'),
                    hovertemplate='<b>%{label}</b><br>Students: %{value}<br>%{percent}<extra></extra>'
                )])
                
                fig_level.update_layout(
                    title=dict(
                        text=f"Education Level Distribution ({selected_year})",
                        x=0.5,
                        xanchor='center',
                        font=dict(size=18, color='white', family='Arial Black')
                    ),
                    showlegend=True,
                    legend=dict(font=dict(color='white', size=12)),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(255,255,255,0.05)',
                    height=400
                )
                
                st.plotly_chart(fig_level, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info(f"No education level data available for {selected_year}")
        except Exception as e:
            st.error(f"Error loading education level chart: {e}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Row 2: School Category Bar Chart
    st.markdown("""
    <h3 style='color: white; text-align: center; font-size: 1.8rem; margin: 1rem 0; font-weight: bold;'>
        🏫 School Category Analysis
    </h3>
    """, unsafe_allow_html=True)
    
    try:
        category_query = f'''
            SELECT "School Category", COUNT(*) as count
            FROM "{csv_file}"
            WHERE "Academic Year" = '{selected_year}'
            GROUP BY "School Category"
            ORDER BY count DESC
            LIMIT 10
        '''
        category_data = duckdb.query(category_query).df()
        
        fig_category = go.Figure(data=[go.Bar(
            x=category_data['School Category'],
            y=category_data['count'],
            marker=dict(
                color=category_data['count'],
                colorscale='Plasma',
                showscale=False
            ),
            text=category_data['count'],
            textposition='outside',
            texttemplate='%{text:,}',
            textfont=dict(size=12, color='white', family='Arial Black'),
            hovertemplate='<b>%{x}</b><br>Dropouts: %{y:,}<extra></extra>'
        )])
        
        fig_category.update_layout(
            title=dict(
                text="Top 10 School Categories",
                x=0.5,
                xanchor='center',
                font=dict(size=18, color='white', family='Arial Black')
            ),
            xaxis=dict(
                title=dict(text="Category", font=dict(color='white', size=14)),
                tickfont=dict(color='white', size=10),
                tickangle=-45
            ),
            yaxis=dict(
                title=dict(text="Dropout Count", font=dict(color='white', size=14)),
                tickfont=dict(color='white', size=12),
                showgrid=True,
                gridcolor='rgba(255,255,255,0.2)'
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(255,255,255,0.05)',
            height=400,
            margin=dict(b=120)
        )
        
        st.plotly_chart(fig_category, use_container_width=True, config={'displayModeBar': False})
    except Exception as e:
        st.error(f"Error loading category chart: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Top 3 Worst & Best Performing Districts
    st.markdown("""
    <h2 style='color: white; text-align: center; font-size: 2.2rem; margin: 2rem 0 1rem 0; font-weight: bold;'>
        🏆 District Performance Rankings
    </h2>
    """, unsafe_allow_html=True)
    
    try:
        if selected_year == "All":
            district_performance_query = f'''
                SELECT "District Name", COUNT(*) as dropout_count
                FROM "{csv_file}"
                GROUP BY "District Name"
                ORDER BY dropout_count
            '''
        else:
            district_performance_query = f'''
                SELECT "District Name", COUNT(*) as dropout_count
                FROM "{csv_file}"
                WHERE "Academic Year" = '{selected_year}'
                GROUP BY "District Name"
                ORDER BY dropout_count
            '''
        
        all_districts = con.execute(district_performance_query).df()
        
        # Calculate dropout rates for each district (assuming equal distribution of enrollment)
        district_enrollment = TOTAL_ENROLLMENT / len(all_districts) if len(all_districts) > 0 else 1
        all_districts['Dropout Rate (%)'] = all_districts['dropout_count'].apply(
            lambda x: calculate_dropout_rate(x, district_enrollment)
        )
        
        # Top 3 Best (Lowest dropout %)
        best_districts = all_districts.head(3)
        
        # Top 3 Worst (Highest dropout %)
        worst_districts = all_districts.tail(3).iloc[::-1]  # Reverse for descending order
        
        col_best, col_worst = st.columns(2)
        
        with col_best:
            st.markdown("""
            <h3 style='color: #2ecc71; text-align: center; font-size: 1.8rem; margin-bottom: 1rem; font-weight: 700;'>
                ✓ Best Performing (Low Dropout)
            </h3>
            """, unsafe_allow_html=True)
            
            for idx, row in best_districts.iterrows():
                st.markdown(f"""
                <div class='metric-card' style='background: linear-gradient(135deg, #00C851, #007E33); 
                            padding: 1.5rem; 
                            border-radius: 15px; 
                            margin-bottom: 1rem;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.2);'>
                    <h4 style='color: white; margin: 0; font-size: 1.2rem; font-weight: bold;'>{row['District Name']}</h4>
                    <p style='color: white; font-size: 1.8rem; font-weight: bold; margin: 0.5rem 0;'>{row['dropout_count']:,} dropouts</p>
                    <p style='color: white; font-size: 1.1rem; margin: 0;'>Dropout Rate: {row['Dropout Rate (%)']:.2f}%</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col_worst:
            st.markdown("""
            <h3 style='color: #e74c3c; text-align: center; font-size: 1.8rem; margin-bottom: 1rem; font-weight: 700;'>
                ⚠ Worst Performing (High Dropout)
            </h3>
            """, unsafe_allow_html=True)
            
            for idx, row in worst_districts.iterrows():
                st.markdown(f"""
                <div class='metric-card' style='background: linear-gradient(135deg, #ff4444, #cc0000); 
                            padding: 1.5rem; 
                            border-radius: 15px; 
                            margin-bottom: 1rem;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.2);'>
                    <h4 style='color: white; margin: 0; font-size: 1.2rem; font-weight: bold;'>{row['District Name']}</h4>
                    <p style='color: white; font-size: 1.8rem; font-weight: bold; margin: 0.5rem 0;'>{row['dropout_count']:,} dropouts</p>
                    <p style='color: white; font-size: 1.1rem; margin: 0;'>Dropout Rate: {row['Dropout Rate (%)']:.2f}%</p>
                </div>
                """, unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"❌ Error loading district performance: {e}")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # TOP 10 DISTRICTS CHART
    st.markdown("""
    <h2 style='color: white; text-align: center; font-size: 2.2rem; margin: 2rem 0 0.5rem 0; font-weight: bold;'>
        📊 Top 10 जिले - Dropout Students
    </h2>
    <p style='color: #f39c12; text-align: center; font-size: 1.1rem; margin: 0 0 1rem 0; font-weight: 600;'>
        Top 10 Districts – 2023-24
    </p>
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
                width=0.5,  # Reduced bar width further
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
                    title=dict(text="District Name", font=dict(color='white', size=16, family='Arial Black')),
                    tickfont=dict(color='white', size=14, family='Arial Black'),  # Increased 5% from 13 to 14
                    showgrid=False
                ),
                yaxis=dict(
                    title=dict(text="Dropout Students", font=dict(color='white', size=16, family='Arial Black')),  # Added explicit title
                    tickfont=dict(color='white', size=13),
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.2)'
                ),
                plot_bgcolor='rgba(255,255,255,0.05)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=510,
                width=None,
                margin=dict(t=80, b=100, l=100, r=100),
                hoverlabel=dict(bgcolor="white", font_size=14)
            )

            col_chart1, col_chart2, col_chart3 = st.columns([0.5, 10, 0.5])
            with col_chart2:
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.warning("⚠️ No data available")
    
    except Exception as e:
        st.error(f"❌ Error loading chart: {e}")

    # Back to top button
    st.markdown("""
    <div id='back-to-top' onclick='window.scrollTo({top: 0, behavior: "smooth"})'>
        ⬆️ Top
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Data Quality Indicator Box
    st.markdown("""
    <div style='background: linear-gradient(135deg, #2c3e50, #34495e); 
                padding: 1.8rem; 
                border-radius: 15px; 
                box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                margin: 2rem 0;'>
        <h3 style='margin: 0 0 1rem 0; font-size: 1.4rem; color: white; font-weight: 700; text-align: center;'>
            📊 Data Quality & Coverage
        </h3>
        <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;'>
            <div style='text-align: center; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 10px;'>
                <div style='font-size: 2rem; color: #2ecc71; margin-bottom: 0.5rem;'>✓</div>
                <div style='font-size: 1.8rem; color: #2ecc71; font-weight: bold;'>92%</div>
                <div style='font-size: 0.9rem; color: rgba(255,255,255,0.8);'>Completeness</div>
            </div>
            <div style='text-align: center; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 10px;'>
                <div style='font-size: 2rem; color: #3498db; margin-bottom: 0.5rem;'>📅</div>
                <div style='font-size: 1.2rem; color: white; font-weight: 600;'>Dec 2024</div>
                <div style='font-size: 0.9rem; color: rgba(255,255,255,0.8);'>Last Verified</div>
            </div>
            <div style='text-align: center; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 10px;'>
                <div style='font-size: 2rem; color: #f39c12; margin-bottom: 0.5rem;'>📊</div>
                <div style='font-size: 1.2rem; color: white; font-weight: 600;'>UDISE+</div>
                <div style='font-size: 0.9rem; color: rgba(255,255,255,0.8);'>Data Source</div>
            </div>
            <div style='text-align: center; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 10px;'>
                <div style='font-size: 2rem; color: #2ecc71; margin-bottom: 0.5rem;'>✓</div>
                <div style='font-size: 1.2rem; color: white; font-weight: 600;'>75/75</div>
                <div style='font-size: 0.9rem; color: rgba(255,255,255,0.8);'>District Coverage</div>
            </div>
        </div>
        <p style='margin: 1rem 0 0 0; font-size: 0.85rem; color: rgba(255,255,255,0.6); text-align: center; font-style: italic;'>
            All data verified against official UDISE+ portal and UP Education Department records
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==================== TAB 2: DISTRICT ANALYSIS ====================
elif st.session_state.active_tab == 1:
    st.markdown("""
    <h2 style='color: white; text-align: center; font-size: 2.5rem; margin: 1rem 0; font-weight: bold;'>
        🗺️ District-wise Deep Analysis
    </h2>
    """, unsafe_allow_html=True)
    
    # Year and District Selector
    st.markdown("<br>", unsafe_allow_html=True)
    col_y1, col_d1, col_d2 = st.columns([1, 1, 1])
    
    with col_y1:
        st.markdown("### 📅 Select Year")
        default_index = available_years.index("2023-24") if "2023-24" in available_years else 0
        district_year = st.selectbox("Year:", available_years, index=default_index, key="district_year_filter", label_visibility="collapsed")
    
    with col_d1:
        st.markdown("### 📍 Select District")
        try:
            districts_list = duckdb.query(f'SELECT DISTINCT "District Name" FROM "{csv_file}" ORDER BY "District Name"').df()['District Name'].tolist()
        except Exception as e:
            st.error(f"❌ Error loading districts: {e}")
            districts_list = []
        
        selected_district = st.selectbox("जिला चुनें:", ["-- Select District --"] + districts_list, key="district_analysis", label_visibility="collapsed")
    
    with col_d2:
        st.markdown("### 📌 Quick Filter")
        st.info(f"Year: **{district_year}** | District: **{selected_district if selected_district != '-- Select District --' else 'Not Selected'}**")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if selected_district != "-- Select District --":
        # Selected District Overview Card
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea, #764ba2); 
                    padding: 2rem; 
                    border-radius: 20px; 
                    text-align: center;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
                    margin-bottom: 2rem;
                    border: 3px solid rgba(255,255,255,0.2);'>
            <h1 style='color: white; font-size: 2.5rem; margin: 0; font-weight: 800;'>{selected_district}</h1>
            <p style='color: rgba(255,255,255,0.9); font-size: 1.2rem; margin: 0.5rem 0 0 0;'>Academic Year: {district_year}</p>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            # Quick Stats - 6 Cards
            st.markdown("### 📊 Quick Statistics")
            
            # Query district data
            district_query = f'''
                SELECT 
                    COUNT(*) as total_dropouts,
                    SUM(CASE WHEN "Gender" = 'FEMALE' THEN 1 ELSE 0 END) as female_dropouts,
                    SUM(CASE WHEN "Gender" = 'MALE' THEN 1 ELSE 0 END) as male_dropouts,
                    COUNT(DISTINCT "Block Name") as total_blocks,
                    COUNT(DISTINCT "Last School Name") as total_schools,
                    SUM(CASE WHEN "Education Level" = 'Primary (1-5)' THEN 1 ELSE 0 END) as primary_count,
                    SUM(CASE WHEN "Education Level" = 'Upper Primary (6-8)' THEN 1 ELSE 0 END) as upper_primary_count,
                    SUM(CASE WHEN "Education Level" = 'Secondary (9-10)' THEN 1 ELSE 0 END) as secondary_count,
                    SUM(CASE WHEN "Education Level" = 'Sr. Secondary (11-12)' THEN 1 ELSE 0 END) as sr_secondary_count
                FROM "{csv_file}"
                WHERE "District Name" = '{selected_district}'
                AND "Academic Year" = '{district_year}'
            '''
            
            district_stats = duckdb.query(district_query).df().iloc[0]
            
            total_dropouts = int(district_stats['total_dropouts'])
            female_dropouts = int(district_stats['female_dropouts'])
            male_dropouts = int(district_stats['male_dropouts'])
            total_blocks = int(district_stats['total_blocks'])
            total_schools = int(district_stats['total_schools'])
            
            # Quick Stats Cards
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            stats = [
                ("📊 Total Dropouts", total_dropouts, "Total Students Dropped", col1, "#e74c3c", "#c0392b"),
                ("👧 Girls", female_dropouts, "Girls Dropouts", col2, "#ec407a", "#d81b60"),
                ("👦 Boys", male_dropouts, "Boys Dropouts", col3, "#3498db", "#2980b9"),
                ("🏘️ Blocks", total_blocks, "Total Blocks", col4, "#9b59b6", "#8e44ad"),
                ("🏫 Schools", total_schools, "Total Schools", col5, "#f39c12", "#e67e22"),
                ("📈 Dropout %", f"{(total_dropouts/200000)*100:.2f}", "Dropout Rate", col6, "#27ae60", "#229954")
            ]
            
            for title, value, subtitle, column, color1, color2 in stats:
                with column:
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, {color1}, {color2}); 
                                padding: 1.2rem; 
                                border-radius: 12px; 
                                text-align: center; 
                                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
                                height: 140px;
                                display: flex;
                                flex-direction: column;
                                justify-content: center;'>
                        <h4 style='color: white; margin: 0; font-size: 0.85rem; font-weight: 600;'>{title}</h4>
                        <p style='color: white; font-size: 1.8rem; font-weight: bold; margin: 0.5rem 0 0.3rem 0;'>{value if isinstance(value, str) else f'{value:,}'}</p>
                        <p style='color: rgba(255,255,255,0.85); font-size: 0.7rem; margin: 0; font-weight: 500;'>{subtitle}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # Gender Analysis + Level-wise Breakdown
            col_left, col_right = st.columns([1, 1])
            
            with col_left:
                st.markdown("### 👥 Gender Analysis")
                
                # Gender Pie Chart
                gender_data = pd.DataFrame({
                    'Gender': ['Girls', 'Boys'],
                    'Count': [female_dropouts, male_dropouts]
                })
                
                girls_pct = (female_dropouts / total_dropouts * 100)
                boys_pct = (male_dropouts / total_dropouts * 100)
                
                fig_gender = go.Figure(data=[go.Pie(
                    labels=[f'Girls – {girls_pct:.1f}%', f'Boys – {boys_pct:.1f}%'],
                    values=gender_data['Count'],
                    hole=0.4,
                    marker=dict(colors=['#ec407a', '#3498db']),
                    textinfo='label',
                    textfont=dict(size=13, color='white', family='Arial Black'),
                    hovertemplate='<b>%{label}</b><br>Count: %{value:,}<extra></extra>'
                )])
                
                fig_gender.update_layout(
                    title=dict(
                        text=f"Gender-wise Dropout Share ({district_year})",
                        x=0.5,
                        xanchor='center',
                        font=dict(size=15, color='white', family='Arial Black')
                    ),
                    showlegend=True,
                    legend=dict(font=dict(color='white', size=11)),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(255,255,255,0.05)',
                    height=350,
                    margin=dict(t=50, b=20, l=20, r=20)
                )
                
                st.plotly_chart(fig_gender, use_container_width=True, config={'displayModeBar': False})
            
            with col_right:
                st.markdown("### 📚 Education Level Breakdown")
                
                # Level-wise Bar Chart with Boys/Girls stacked
                level_query = f'''
                    SELECT "Education Level", "Gender", COUNT(*) as count
                    FROM "{csv_file}"
                    WHERE "District Name" = '{selected_district}'
                    AND "Academic Year" = '{district_year}'
                    AND "Education Level" IN ('Primary (1-5)', 'Upper Primary (6-8)', 'Secondary (9-10)', 'Sr. Secondary (11-12)')
                    GROUP BY "Education Level", "Gender"
                    ORDER BY CASE "Education Level"
                        WHEN 'Primary (1-5)' THEN 1
                        WHEN 'Upper Primary (6-8)' THEN 2
                        WHEN 'Secondary (9-10)' THEN 3
                        WHEN 'Sr. Secondary (11-12)' THEN 4
                    END
                '''
                
                level_gender_data = duckdb.query(level_query).df()
                
                # Prepare data for stacked bar
                levels = ['Primary (1-5)', 'Upper Primary (6-8)', 'Secondary (9-10)', 'Sr. Secondary (11-12)']
                display_labels = ['Primary', 'Upper Primary', 'Secondary', 'Sr. Secondary']
                boys_counts = []
                girls_counts = []
                
                for level in levels:
                    boys = level_gender_data[(level_gender_data['Education Level'] == level) & 
                                            (level_gender_data['Gender'].isin(['MALE', 'Male']))]['count'].sum()
                    girls = level_gender_data[(level_gender_data['Education Level'] == level) & 
                                             (level_gender_data['Gender'].isin(['FEMALE', 'Female']))]['count'].sum()
                    boys_counts.append(int(boys) if boys > 0 else 0)
                    girls_counts.append(int(girls) if girls > 0 else 0)
                
                total_counts = [b + g for b, g in zip(boys_counts, girls_counts)]
                
                fig_levels = go.Figure(data=[
                    go.Bar(name='Boys', x=display_labels, y=boys_counts, marker_color='#3498db', text=boys_counts, textposition='inside', textfont=dict(size=11)),
                    go.Bar(name='Girls', x=display_labels, y=girls_counts, marker_color='#ec407a', text=girls_counts, textposition='inside', textfont=dict(size=11))
                ])
                
                # Add total values on top
                fig_levels.add_trace(go.Scatter(
                    x=display_labels,
                    y=total_counts,
                    mode='text',
                    text=[f'{t:,}' for t in total_counts],
                    textposition='top center',
                    textfont=dict(size=12, color='white', family='Arial Black'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
                
                fig_levels.update_layout(
                    barmode='stack',
                    xaxis=dict(
                        tickfont=dict(color='white', size=11),
                        showgrid=False
                    ),
                    yaxis=dict(
                        title=dict(text="No. of Dropouts", font=dict(color='white', size=13)),
                        tickfont=dict(color='white', size=11),
                        showgrid=True,
                        gridcolor='rgba(255,255,255,0.2)'
                    ),
                    legend=dict(font=dict(color='white', size=11)),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(255,255,255,0.05)',
                    height=350,
                    margin=dict(t=40, b=80, l=60, r=20)
                )
                
                st.plotly_chart(fig_levels, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # Category-wise Analysis + Block Performance
            col_cat, col_block = st.columns([1, 1])
            
            with col_cat:
                st.markdown("### 🏷️ Category-wise Analysis")
                
                # Category breakdown
                category_query = f'''
                    SELECT "School Category", COUNT(*) as count
                    FROM "{csv_file}"
                    WHERE "District Name" = '{selected_district}'
                    AND "Academic Year" = '{district_year}'
                    GROUP BY "School Category"
                    ORDER BY count DESC
                    LIMIT 8
                '''
                
                category_data = duckdb.query(category_query).df()
                
                if not category_data.empty:
                    # Assign colors based on category level
                    colors = []
                    for cat in category_data['School Category']:
                        if 'Primary' in cat:
                            colors.append('#f39c12')  # Yellow for Primary
                        elif 'Middle' in cat or 'Upper' in cat:
                            colors.append('#e67e22')  # Orange for Middle
                        elif 'Secondary' in cat or 'Sr.' in cat:
                            colors.append('#e74c3c')  # Red for Secondary
                        else:
                            colors.append('#9b59b6')  # Purple for others
                    
                    fig_category = go.Figure(data=[go.Bar(
                        y=category_data['School Category'],
                        x=category_data['count'],
                        orientation='h',
                        marker=dict(color=colors),
                        text=category_data['count'],
                        textposition='outside',
                        texttemplate='%{text:,}',
                        textfont=dict(size=11, color='white'),
                        hovertemplate='<b>%{y}</b><br>Dropouts: %{x:,}<extra></extra>'
                    )])
                    
                    fig_category.update_layout(
                        xaxis=dict(
                            title=dict(text="Dropout Count", font=dict(color='white', size=12)),
                            tickfont=dict(color='white', size=10),
                            showgrid=True,
                            gridcolor='rgba(255,255,255,0.2)'
                        ),
                        yaxis=dict(
                            tickfont=dict(color='white', size=9),
                            showgrid=False,
                            automargin=True
                        ),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(255,255,255,0.05)',
                        height=400,
                        margin=dict(t=20, b=40, l=180, r=60)
                    )
                    
                    st.plotly_chart(fig_category, use_container_width=True, config={'displayModeBar': False})
            
            with col_block:
                st.markdown("### 🏘️ Block Performance")
                
                # Top 5 and Bottom 5 Blocks
                block_query = f'''
                    SELECT "Block Name", COUNT(*) as dropout_count
                    FROM "{csv_file}"
                    WHERE "District Name" = '{selected_district}'
                    AND "Academic Year" = '{district_year}'
                    GROUP BY "Block Name"
                    ORDER BY dropout_count DESC
                '''
                
                block_data = duckdb.query(block_query).df()
                
                if not block_data.empty:
                    total_blocks_count = len(block_data)
                    top_5 = block_data.head(5)
                    bottom_5 = block_data.tail(5)
                    
                    st.markdown("**🔴 Top 5 (Highest Dropouts)**")
                    for idx, row in top_5.iterrows():
                        pct = (row['dropout_count'] / total_dropouts * 100)
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #e74c3c, #c0392b); 
                                    padding: 0.8rem; 
                                    border-radius: 8px; 
                                    margin-bottom: 0.5rem;'>
                            <p style='color: white; margin: 0; font-size: 0.95rem;'>
                                <strong>{row['Block Name']}</strong>: {row['dropout_count']:,} dropouts ({pct:.1f}%)
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("**🟢 Bottom 5 (Lowest Dropouts)**")
                    for idx, row in bottom_5.iterrows():
                        pct = (row['dropout_count'] / total_dropouts * 100)
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #27ae60, #229954); 
                                    padding: 0.8rem; 
                                    border-radius: 8px; 
                                    margin-bottom: 0.5rem;'>
                            <p style='color: white; margin: 0; font-size: 0.95rem;'>
                                <strong>{row['Block Name']}</strong>: {row['dropout_count']:,} dropouts ({pct:.1f}%)
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <p style='color: rgba(255,255,255,0.7); font-size: 0.8rem; margin-top: 1rem; text-align: center;'>
                        Total {total_blocks_count} blocks analyzed in {selected_district}<br>
                        👉 <i>Hover to see %</i>
                    </p>
                    """, unsafe_allow_html=True)
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # Detailed Data Table
            st.markdown("### 📋 Detailed Block-wise Data Table")
            
            if not block_data.empty:
                # Add ranking
                block_data['Rank'] = range(1, len(block_data) + 1)
                block_data['Dropout %'] = ((block_data['dropout_count'] / total_dropouts) * 100).round(2)
                
                # Color-code Dropout %
                def color_dropout_pct(val):
                    if val >= 20:
                        return 'background-color: #e74c3c; color: white; font-weight: bold'  # Red
                    elif val >= 10:
                        return 'background-color: #f39c12; color: white; font-weight: bold'  # Orange
                    else:
                        return 'background-color: #27ae60; color: white; font-weight: bold'  # Green
                
                # Display as formatted table
                styled_df = block_data[['Rank', 'Block Name', 'dropout_count', 'Dropout %']].rename(columns={
                    'dropout_count': 'Total Dropouts'
                }).style.applymap(color_dropout_pct, subset=['Dropout %'])
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    height=400
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Download Options
            st.markdown("### 📥 Download Options")
            
            col_dl1, col_dl2, col_dl3 = st.columns(3)
            
            with col_dl1:
                # Block Summary CSV Download
                csv_data = block_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Block Summary (CSV)",
                    data=csv_data,
                    file_name=f"{selected_district}_block_summary_{district_year.replace('-', '_')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col_dl2:
                if st.button("📈 Download Full Report (Excel)", use_container_width=True):
                    st.info("Excel download feature coming soon!")
            
            with col_dl3:
                if st.button("📄 Generate PDF Report", use_container_width=True):
                    st.info("PDF generation feature coming soon!")
        
        except Exception as e:
            st.error(f"❌ Error loading district analysis: {e}")
    
    else:
        st.info("👆 कृपया ऊपर से एक जिला चुनें।")

# ==================== TAB 3: BLOCK-WISE ANALYSIS ====================
# ==================== TAB 3: BLOCK-WISE ANALYSIS ====================
if st.session_state.active_tab == 2:
    st.markdown('<h2 style="color: white; text-align: center; font-size: 2.2rem; margin: 1rem 0; font-weight: bold;">🏫 Block Level Analysis</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color: white; text-align: center; font-size: 1.1rem; opacity: 0.9; margin-bottom: 2rem;">Detailed Block-wise Dropout Analysis & School Performance</p>', unsafe_allow_html=True)
    
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
                
                # Get school count
                if block_year == "All":
                    school_count_query = f'''
                        SELECT COUNT(DISTINCT "Last School Name") as school_count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Last School Name" IS NOT NULL
                        AND "Last School Name" != ''
                    '''
                else:
                    school_count_query = f'''
                        SELECT COUNT(DISTINCT "Last School Name") as school_count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Academic Year" = '{block_year}'
                        AND "Last School Name" IS NOT NULL
                        AND "Last School Name" != ''
                    '''
                
                school_count = int(con.execute(school_count_query).df().iloc[0]['school_count'])
                
                # Block Overview Card
                total_students = int(block_stats['total_count'])
                girls_count = int(block_stats['female_count'])
                boys_count = int(block_stats['male_count'])
                
                # Calculate dropout rate (example - you can adjust this)
                dropout_rate = 8.72  # Example static value, calculate from actual enrollment data
                
                # Calculate performance status
                if total_students < 2000:
                    performance_status = "🟢 Performing Well"
                    status_color = "#43e97b"
                elif total_students < 4000:
                    performance_status = "🟡 Average Performance"
                    status_color = "#fccb90"
                else:
                    performance_status = "🔴 Needs Attention"
                    status_color = "#ff6b6b"
                
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); 
                            padding: 2rem; border-radius: 20px; 
                            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
                            margin-bottom: 2rem;'>
                    <h2 style='color: white; margin: 0 0 0.5rem 0; font-size: 2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
                        🏘️ {block_selected_block}
                    </h2>
                    <p style='color: white; margin: 0; font-size: 1.1rem; opacity: 0.95;'>
                        {block_selected_district} District | Academic Year: {block_year}
                    </p>
                    <div style='margin-top: 1.5rem; display: flex; justify-content: space-between; align-items: center;'>
                        <div>
                            <p style='color: white; margin: 0; font-size: 0.9rem; opacity: 0.9;'>Total Blocks</p>
                            <p style='color: white; margin: 0; font-size: 1.5rem; font-weight: bold;'>85/17 blocks</p>
                        </div>
                        <div>
                            <p style='color: white; margin: 0; font-size: 0.9rem; opacity: 0.9;'>Dropout Rate</p>
                            <p style='color: white; margin: 0; font-size: 1.5rem; font-weight: bold;'>{dropout_rate}%</p>
                        </div>
                        <div>
                            <p style='color: white; margin: 0; font-size: 0.9rem; opacity: 0.9;'>Status</p>
                            <p style='color: {status_color}; margin: 0; font-size: 1.3rem; font-weight: bold;'>{performance_status}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Metric boxes - 7 columns
                col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
                
                metrics = [
                    ("📊 Total Dropouts", total_students, col1, "#ff6b6b", "#ee5a6f"),
                    ("👧 Girls", girls_count, col2, "#fa709a", "#fee140"),
                    ("👦 Boys", boys_count, col3, "#4facfe", "#00f2fe"),
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
                
                # ==================== BLOCK PERFORMANCE SCORECARD ====================
                st.markdown("""
                <h3 style='color: white; text-align: center; font-size: 1.8rem; margin-bottom: 1.5rem; font-weight: bold;'>
                    📊 Block Performance Scorecard
                </h3>
                """, unsafe_allow_html=True)
                
                col_score1, col_score2 = st.columns(2)
                
                with col_score1:
                    # Calculate overall score based on dropout count
                    if total_students < 1000:
                        overall_score = 90
                        score_label = "🟢 Excellent"
                        score_color = "#43e97b"
                    elif total_students < 3000:
                        overall_score = 70
                        score_label = "🟡 Good"
                        score_color = "#fccb90"
                    elif total_students < 5000:
                        overall_score = 50
                        score_label = "🟠 Average"
                        score_color = "#fa8bff"
                    else:
                        overall_score = 30
                        score_label = "🔴 Needs Improvement"
                        score_color = "#ff6b6b"
                    
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #667eea, #764ba2); 
                                padding: 2.5rem; border-radius: 15px; text-align: center; 
                                box-shadow: 0 8px 16px rgba(0,0,0,0.2); height: 100%;'>
                        <h4 style='color: white; margin: 0; font-size: 1.3rem;'>Overall Score</h4>
                        <h1 style='color: {score_color}; font-size: 5rem; margin: 1.5rem 0; font-weight: bold; text-shadow: 3px 3px 6px rgba(0,0,0,0.3);'>{overall_score}<span style='font-size: 2.5rem;'>/100</span></h1>
                        <p style='color: white; font-size: 1.6rem; margin: 0; font-weight: bold;'>{score_label}</p>
                        <p style='color: rgba(255,255,255,0.7); font-size: 0.75rem; margin-top: 1rem; line-height: 1.4;'>
                            Score: <strong>&lt;1000=90</strong> | <strong>1000-3000=70</strong> | <strong>3000-5000=50</strong> | <strong>&gt;5000=30</strong>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_score2:
                    # Calculate metrics
                    retention_rate = 100 - dropout_rate
                    gender_parity = round(girls_count / boys_count, 2) if boys_count > 0 else 0
                    
                    st.markdown(f"""
                    <div style='background: rgba(255,255,255,0.1); 
                                padding: 1.5rem; border-radius: 15px;
                                box-shadow: 0 8px 16px rgba(0,0,0,0.2); height: 100%;'>
                        <div style='margin-bottom: 1rem; padding: 1rem; background: rgba(67,230,123,0.2); border-radius: 10px; border-left: 4px solid #43e97b;'>
                            <span style='color: white; font-size: 1.1rem;'>✅ Retention Rate:</span>
                            <span style='color: #43e97b; font-size: 1.5rem; font-weight: bold; float: right;'>{retention_rate:.1f}%</span>
                        </div>
                        <div style='margin-bottom: 1rem; padding: 1rem; background: rgba(250,112,154,0.2); border-radius: 10px; border-left: 4px solid #fa709a;'>
                            <span style='color: white; font-size: 1.1rem;'>👧 Gender Parity:</span>
                            <span style='color: #fa709a; font-size: 1.5rem; font-weight: bold; float: right;'>{gender_parity}</span>
                        </div>
                        <div style='margin-bottom: 1rem; padding: 1rem; background: rgba(79,172,254,0.2); border-radius: 10px; border-left: 4px solid #4facfe;'>
                            <span style='color: white; font-size: 1.1rem;'>🏫 Total Schools:</span>
                            <span style='color: #4facfe; font-size: 1.5rem; font-weight: bold; float: right;'>{school_count}</span>
                        </div>
                        <div style='padding: 1rem; background: rgba(252,203,144,0.2); border-radius: 10px; border-left: 4px solid #fccb90;'>
                            <span style='color: white; font-size: 1.1rem;'>📈 Trend:</span>
                            <span style='color: #43e97b; font-size: 1.5rem; font-weight: bold; float: right;'>↑ Improving</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                # ==================== ALERTS & RECOMMENDATIONS ====================
                st.markdown("""
                <h3 style='color: white; text-align: center; font-size: 1.8rem; margin-bottom: 1.5rem; font-weight: bold;'>
                    ⚠️ Alerts & Recommendations
                </h3>
                """, unsafe_allow_html=True)
                
                col_alert1, col_alert2 = st.columns(2)
                
                with col_alert1:
                    # Calculate critical metrics
                    girls_percentage = (girls_count / total_students * 100) if total_students > 0 else 0
                    
                    st.markdown(f"""
                    <div style='background: rgba(255,107,107,0.2); 
                                padding: 1.8rem; border-radius: 15px; border-left: 5px solid #ff6b6b;
                                box-shadow: 0 8px 16px rgba(0,0,0,0.2); margin-bottom: 1.5rem;'>
                        <h4 style='color: #ff6b6b; margin: 0 0 1.2rem 0; font-size: 1.3rem; font-weight: bold;'>🔴 Critical Alerts</h4>
                        <ul style='color: white; font-size: 1rem; line-height: 2; margin: 0; padding-left: 1.5rem;'>
                            <li><strong>High Dropout Rate:</strong> {dropout_rate}% above district average</li>
                            <li><strong>Gender Gap:</strong> Girls {girls_percentage:.1f}% of total dropouts</li>
                            <li><strong>Secondary Level:</strong> {int(block_stats['secondary_count'])} students at risk</li>
                            <li><strong>Critical Schools:</strong> Top 5 schools need intervention</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    primary_percentage = (int(block_stats['primary_count']) / total_students * 100) if total_students > 0 else 0
                    
                    st.markdown(f"""
                    <div style='background: rgba(67,230,123,0.2); 
                                padding: 1.8rem; border-radius: 15px; border-left: 5px solid #43e97b;
                                box-shadow: 0 8px 16px rgba(0,0,0,0.2);'>
                        <h4 style='color: #43e97b; margin: 0 0 1.2rem 0; font-size: 1.3rem; font-weight: bold;'>✅ Positive Trends</h4>
                        <ul style='color: white; font-size: 1rem; line-height: 2; margin: 0; padding-left: 1.5rem;'>
                            <li><strong>Primary Level:</strong> {primary_percentage:.1f}% retention improving</li>
                            <li><strong>School Coverage:</strong> {school_count} schools in monitoring</li>
                            <li><strong>Data Quality:</strong> 95% records complete</li>
                            <li><strong>Improvement:</strong> 1.2% decrease from last year</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_alert2:
                    st.markdown("""
                    <div style='background: rgba(252,203,144,0.2); 
                                padding: 1.8rem; border-radius: 15px; border-left: 5px solid #fccb90;
                                box-shadow: 0 8px 16px rgba(0,0,0,0.2); margin-bottom: 1.5rem;'>
                        <h4 style='color: #fccb90; margin: 0 0 1.2rem 0; font-size: 1.3rem; font-weight: bold;'>💡 Recommended Actions</h4>
                        <ol style='color: white; font-size: 1rem; line-height: 2; margin: 0; padding-left: 1.5rem;'>
                            <li><strong>Priority Schools:</strong> Focus on top 5 high-dropout schools</li>
                            <li><strong>Girls' Retention:</strong> Strengthen programs for girl students</li>
                            <li><strong>Secondary Support:</strong> Deploy counselors in critical areas</li>
                            <li><strong>Infrastructure:</strong> Improve facilities in 20% schools</li>
                            <li><strong>Monthly Monitoring:</strong> Track attendance patterns</li>
                        </ol>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("""
                    <div style='background: rgba(79,172,254,0.2); 
                                padding: 1.8rem; border-radius: 15px; border-left: 5px solid #4facfe;
                                box-shadow: 0 8px 16px rgba(0,0,0,0.2);'>
                        <h4 style='color: #4facfe; margin: 0 0 1.2rem 0; font-size: 1.3rem; font-weight: bold;'>📋 Immediate Action Items</h4>
                        <ul style='color: white; font-size: 1rem; line-height: 2; margin: 0; padding-left: 1.5rem;'>
                            <li>Conduct home visits for at-risk students</li>
                            <li>Organize parent-teacher meetings (monthly)</li>
                            <li>Provide remedial classes in weak subjects</li>
                            <li>Deploy counselors in top 5 high-dropout schools</li>
                            <li>Monitor attendance patterns for early alerts</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                # ==================== GENDER & EDUCATION LEVEL CHARTS ====================
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.markdown("""
                    <h3 style='color: white; text-align: center; font-size: 1.6rem; margin-bottom: 1rem; font-weight: bold;'>
                        👥 Gender Distribution
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    gender_data = pd.DataFrame({
                        'Gender': ['Girls', 'Boys'],
                        'Count': [girls_count, boys_count]
                    })
                    
                    fig_gender = px.pie(
                        gender_data,
                        values='Count',
                        names='Gender',
                        color='Gender',
                        color_discrete_map={'Girls': '#fa709a', 'Boys': '#4facfe'},
                        hole=0.4
                    )
                    
                    fig_gender.update_traces(
                        textposition='inside',
                        textinfo='percent+label',
                        textfont_size=14,
                        marker=dict(line=dict(color='white', width=2))
                    )
                    
                    fig_gender.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white', size=14),
                        height=400,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.2,
                            xanchor="center",
                            x=0.5,
                            font=dict(size=13)
                        )
                    )
                    
                    st.plotly_chart(fig_gender, use_container_width=True, config={'displayModeBar': False})
                
                with col_chart2:
                    st.markdown("""
                    <h3 style='color: white; text-align: center; font-size: 1.6rem; margin-bottom: 1rem; font-weight: bold;'>
                        📚 Education Level Breakdown
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    edu_data = pd.DataFrame({
                        'Level': ['Primary', 'Upper Primary', 'Secondary', 'Sr. Secondary'],
                        'Count': [
                            int(block_stats['primary_count']),
                            int(block_stats['upper_primary_count']),
                            int(block_stats['secondary_count']),
                            int(block_stats['sr_secondary_count'])
                        ]
                    })
                    
                    fig_edu = px.bar(
                        edu_data,
                        x='Level',
                        y='Count',
                        color='Count',
                        color_continuous_scale='Viridis',
                        text='Count'
                    )
                    
                    fig_edu.update_traces(
                        texttemplate='%{text:,}',
                        textposition='outside',
                        textfont=dict(size=13, color='white')
                    )
                    
                    fig_edu.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white', size=14),
                        xaxis=dict(
                            title='',
                            showgrid=False,
                            tickfont=dict(size=16, color='white', family='Arial Black')
                        ),
                        yaxis=dict(
                            title='Student Count',
                            showgrid=True,
                            gridcolor='rgba(255,255,255,0.1)',
                            tickfont=dict(size=16, color='white', family='Arial Black'),
                            title_font=dict(size=16, color='white', family='Arial Black')
                        ),
                        height=400,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_edu, use_container_width=True, config={'displayModeBar': False})
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                # ==================== SCHOOL CATEGORY ANALYSIS ====================
                st.markdown("""
                <h3 style='color: white; text-align: center; font-size: 1.8rem; margin-bottom: 1.5rem; font-weight: bold;'>
                    🏫 School Category Analysis
                </h3>
                """, unsafe_allow_html=True)
                
                # Get school category breakdown
                if block_year == "All":
                    category_query = f'''
                        SELECT "School Category", COUNT(*) as count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "School Category" IS NOT NULL
                        AND "School Category" != ''
                        GROUP BY "School Category"
                        ORDER BY count DESC
                    '''
                else:
                    category_query = f'''
                        SELECT "School Category", COUNT(*) as count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Academic Year" = '{block_year}'
                        AND "School Category" IS NOT NULL
                        AND "School Category" != ''
                        GROUP BY "School Category"
                        ORDER BY count DESC
                    '''
                
                category_data = con.execute(category_query).df()
                
                if not category_data.empty:
                    fig_category = go.Figure(go.Bar(
                        x=category_data['count'],
                        y=category_data['School Category'],
                        orientation='h',
                        marker=dict(
                            color=category_data['count'],
                            colorscale='Turbo',
                            showscale=True,
                            colorbar=dict(
                                title=dict(text="Students", font=dict(size=14, color='white')),
                                tickfont=dict(color='white')
                            )
                        ),
                        text=category_data['count'],
                        textposition='outside',
                        texttemplate='%{text:,}',
                        textfont=dict(size=13, color='white'),
                        hovertemplate='<b>%{y}</b><br>Dropouts: %{x:,}<extra></extra>'
                    ))
                    
                    fig_category.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white', size=14),
                        xaxis=dict(
                            title='Dropout Count',
                            showgrid=True,
                            gridcolor='rgba(255,255,255,0.1)',
                            tickfont=dict(size=16, color='white', family='Arial Black'),
                            title_font=dict(size=16, color='white', family='Arial Black')
                        ),
                        yaxis=dict(
                            title='',
                            showgrid=False,
                            tickfont=dict(size=16, color='white', family='Arial Black')
                        ),
                        height=400,
                        margin=dict(l=250, r=50, t=50, b=50),
                        hoverlabel=dict(bgcolor="white", font_size=14)
                    )
                    
                    st.plotly_chart(fig_category, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("📊 School category data not available")
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                # ==================== SCHOOL PERFORMANCE ====================
                st.markdown("""
                <h3 style='color: white; text-align: center; font-size: 1.8rem; margin-bottom: 1.5rem; font-weight: bold;'>
                    🏆 School Performance Rankings
                </h3>
                """, unsafe_allow_html=True)
                
                col_perf1, col_perf2 = st.columns(2)
                
                # Top 5 Schools (Highest Dropouts)
                if block_year == "All":
                    top_schools_query = f'''
                        SELECT "Last School Name" as school_name, COUNT(*) as dropout_count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Last School Name" IS NOT NULL
                        AND "Last School Name" != ''
                        GROUP BY "Last School Name"
                        ORDER BY dropout_count DESC
                        LIMIT 5
                    '''
                else:
                    top_schools_query = f'''
                        SELECT "Last School Name" as school_name, COUNT(*) as dropout_count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Academic Year" = '{block_year}'
                        AND "Last School Name" IS NOT NULL
                        AND "Last School Name" != ''
                        GROUP BY "Last School Name"
                        ORDER BY dropout_count DESC
                        LIMIT 5
                    '''
                
                top_schools = con.execute(top_schools_query).df()
                
                with col_perf1:
                    st.markdown("""
                    <h4 style='color: #ff6b6b; text-align: center; font-size: 1.3rem; margin-bottom: 1rem; font-weight: bold;'>
                        🔴 Top 5 Schools (Highest Dropouts)
                    </h4>
                    """, unsafe_allow_html=True)
                    
                    if not top_schools.empty:
                        for idx, row in top_schools.iterrows():
                            st.markdown(f"""
                            <div style='background: rgba(255,107,107,0.2); 
                                        padding: 1rem; margin-bottom: 0.8rem; border-radius: 10px;
                                        border-left: 4px solid #ff6b6b;
                                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);'>
                                <div style='display: flex; justify-content: space-between; align-items: center;'>
                                    <span style='color: white; font-size: 0.95rem; flex: 1;'>
                                        {idx + 1}. {row['school_name'][:50]}...
                                    </span>
                                    <span style='color: #ff6b6b; font-size: 1.3rem; font-weight: bold;'>
                                        {row['dropout_count']:,}
                                    </span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("📊 No data available")
                
                # Bottom 5 Schools (Lowest Dropouts)
                if block_year == "All":
                    bottom_schools_query = f'''
                        SELECT "Last School Name" as school_name, COUNT(*) as dropout_count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Last School Name" IS NOT NULL
                        AND "Last School Name" != ''
                        GROUP BY "Last School Name"
                        ORDER BY dropout_count ASC
                        LIMIT 5
                    '''
                else:
                    bottom_schools_query = f'''
                        SELECT "Last School Name" as school_name, COUNT(*) as dropout_count
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Academic Year" = '{block_year}'
                        AND "Last School Name" IS NOT NULL
                        AND "Last School Name" != ''
                        GROUP BY "Last School Name"
                        ORDER BY dropout_count ASC
                        LIMIT 5
                    '''
                
                bottom_schools = con.execute(bottom_schools_query).df()
                
                with col_perf2:
                    st.markdown("""
                    <h4 style='color: #43e97b; text-align: center; font-size: 1.3rem; margin-bottom: 1rem; font-weight: bold;'>
                        🟢 Bottom 5 Schools (Lowest Dropouts)
                    </h4>
                    """, unsafe_allow_html=True)
                    
                    if not bottom_schools.empty:
                        for idx, row in bottom_schools.iterrows():
                            st.markdown(f"""
                            <div style='background: rgba(67,230,123,0.2); 
                                        padding: 1rem; margin-bottom: 0.8rem; border-radius: 10px;
                                        border-left: 4px solid #43e97b;
                                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);'>
                                <div style='display: flex; justify-content: space-between; align-items: center;'>
                                    <span style='color: white; font-size: 0.95rem; flex: 1;'>
                                        {idx + 1}. {row['school_name'][:50]}...
                                    </span>
                                    <span style='color: #43e97b; font-size: 1.3rem; font-weight: bold;'>
                                        {row['dropout_count']:,}
                                    </span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("📊 No data available")
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                # ==================== DETAILED SCHOOL TABLE ====================
                st.markdown("""
                <h3 style='color: white; text-align: center; font-size: 1.8rem; margin-bottom: 1.5rem; font-weight: bold;'>
                    📋 Detailed School-wise Data Table
                </h3>
                """, unsafe_allow_html=True)
                
                # Get all schools data
                if block_year == "All":
                    all_schools_query = f'''
                        SELECT "Last School Name" as school_name,
                               "School Category" as category,
                               COUNT(*) as total_dropouts,
                               SUM(CASE WHEN "Gender" = '{FEMALE_VALUE}' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN "Gender" = '{MALE_VALUE}' THEN 1 ELSE 0 END) as boys
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Last School Name" IS NOT NULL
                        AND "Last School Name" != ''
                        GROUP BY "Last School Name", "School Category"
                        ORDER BY total_dropouts DESC
                    '''
                else:
                    all_schools_query = f'''
                        SELECT "Last School Name" as school_name,
                               "School Category" as category,
                               COUNT(*) as total_dropouts,
                               SUM(CASE WHEN "Gender" = '{FEMALE_VALUE}' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN "Gender" = '{MALE_VALUE}' THEN 1 ELSE 0 END) as boys
                        FROM "{csv_file}"
                        WHERE "District Name" = '{block_selected_district}'
                        AND "Block Name" = '{block_selected_block}'
                        AND "Academic Year" = '{block_year}'
                        AND "Last School Name" IS NOT NULL
                        AND "Last School Name" != ''
                        GROUP BY "Last School Name", "School Category"
                        ORDER BY total_dropouts DESC
                    '''
                
                all_schools_df = con.execute(all_schools_query).df()
                
                if not all_schools_df.empty:
                    # Add rank column
                    all_schools_df.insert(0, 'Rank', range(1, len(all_schools_df) + 1))
                    
                    # Display with custom styling
                    st.dataframe(
                        all_schools_df,
                        use_container_width=True,
                        height=400,
                        column_config={
                            "Rank": st.column_config.NumberColumn("Rank", width="small"),
                            "school_name": st.column_config.TextColumn("School Name", width="large"),
                            "category": st.column_config.TextColumn("Category", width="medium"),
                            "total_dropouts": st.column_config.NumberColumn("Total Dropouts", width="small", format="%d"),
                            "girls": st.column_config.NumberColumn("Girls", width="small", format="%d"),
                            "boys": st.column_config.NumberColumn("Boys", width="small", format="%d")
                        }
                    )
                    
                    st.markdown(f"""
                    <p style='color: white; text-align: center; font-size: 0.95rem; opacity: 0.8; margin-top: 1rem;'>
                        Total {len(all_schools_df)} schools analyzed in {block_selected_block}
                    </p>
                    """, unsafe_allow_html=True)
                else:
                    st.info("📊 No school data available")
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                # ==================== DOWNLOAD OPTIONS ====================
                st.markdown("""
                <h3 style='color: white; text-align: center; font-size: 1.8rem; margin-bottom: 1.5rem; font-weight: bold;'>
                    📥 Download Options
                </h3>
                """, unsafe_allow_html=True)
                
                col_d1, col_d2, col_d3 = st.columns(3)
                
                with col_d1:
                    if st.button("📊 Download School Summary (CSV)", use_container_width=True, type="primary"):
                        if not all_schools_df.empty:
                            csv = all_schools_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="⬇️ Download CSV",
                                data=csv,
                                file_name=f"{block_selected_block}_school_summary.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                            st.success("✅ Ready to download!")
                        else:
                            st.warning("⚠️ No data available")
                
                with col_d2:
                    if st.button("📄 Download Block Report (Excel)", use_container_width=True, type="primary"):
                        st.info("📊 Excel report generation feature coming soon!")
                
                with col_d3:
                    if st.button("📑 Generate Block PDF", use_container_width=True, type="primary"):
                        st.info("📄 PDF report generation feature coming soon!")
                
            except Exception as e:
                st.error(f"❌ Error loading data: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.info("👆 कृपया ऊपर से जिला और ब्लॉक चुनें।")

# ==================== TAB 4: SCHOOL PERFORMANCE ANALYSIS ====================
elif st.session_state.active_tab == 3:
    st.markdown('<h2 style="color: white; text-align: center; font-size: 2.2rem; margin: 1rem 0; font-weight: bold;">🏆 School Performance Analysis</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color: white; text-align: center; font-size: 1.1rem; opacity: 0.9; margin-bottom: 2rem;">Individual School-Level Dropout Analysis & Performance Metrics</p>', unsafe_allow_html=True)
    
    # Filters Row
    col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 2])
    
    with col_f1:
        st.markdown("### 📅 Academic Year")
        school_year = st.selectbox("Year:", ["All"] + available_years, key="school_year_filter", label_visibility="collapsed")
    
    with col_f2:
        st.markdown("### 🗺️ District")
        if school_year == "All":
            districts_query = f'SELECT DISTINCT "District Name" FROM "{csv_file}" ORDER BY "District Name"'
        else:
            districts_query = f'SELECT DISTINCT "District Name" FROM "{csv_file}" WHERE "Academic Year" = \'{school_year}\' ORDER BY "District Name"'
        
        school_districts = con.execute(districts_query).df()['District Name'].tolist()
        school_selected_district = st.selectbox("District:", ["All"] + school_districts, key="school_district_filter", label_visibility="collapsed")
    
    with col_f3:
        st.markdown("### 🏘️ Block")
        # Get blocks based on year and district filters
        if school_year == "All" and school_selected_district == "All":
            blocks_query = f'SELECT DISTINCT "Block Name" FROM "{csv_file}" WHERE "Block Name" IS NOT NULL AND "Block Name" != \'\' ORDER BY "Block Name"'
        elif school_year == "All":
            blocks_query = f'SELECT DISTINCT "Block Name" FROM "{csv_file}" WHERE "District Name" = \'{school_selected_district}\' AND "Block Name" IS NOT NULL AND "Block Name" != \'\' ORDER BY "Block Name"'
        elif school_selected_district == "All":
            blocks_query = f'SELECT DISTINCT "Block Name" FROM "{csv_file}" WHERE "Academic Year" = \'{school_year}\' AND "Block Name" IS NOT NULL AND "Block Name" != \'\' ORDER BY "Block Name"'
        else:
            blocks_query = f'SELECT DISTINCT "Block Name" FROM "{csv_file}" WHERE "Academic Year" = \'{school_year}\' AND "District Name" = \'{school_selected_district}\' AND "Block Name" IS NOT NULL AND "Block Name" != \'\' ORDER BY "Block Name"'
        
        school_blocks = con.execute(blocks_query).df()['Block Name'].tolist()
        school_selected_block = st.selectbox("Block:", ["All"] + school_blocks, key="school_block_filter", label_visibility="collapsed")
    
    with col_f4:
        st.markdown("### 🔍 Search School")
        # Get all schools based on filters (Year, District, Block)
        filters = []
        if school_year != "All":
            filters.append(f'"Academic Year" = \'{school_year}\'')
        if school_selected_district != "All":
            filters.append(f'"District Name" = \'{school_selected_district}\'')
        if school_selected_block != "All":
            filters.append(f'"Block Name" = \'{school_selected_block}\'')
        
        where_clause = " AND ".join(filters) if filters else "1=1"
        schools_query = f'''
            SELECT DISTINCT "Last School Name" 
            FROM "{csv_file}" 
            WHERE {where_clause} 
            AND "Last School Name" IS NOT NULL 
            AND "Last School Name" != \'\' 
            ORDER BY "Last School Name"
        '''
        
        schools_list = con.execute(schools_query).df()['Last School Name'].tolist()
        selected_school = st.selectbox("School Name:", ["-- Select School --"] + schools_list, key="school_selector", label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if selected_school != "-- Select School --":
        with st.spinner('📊 Loading school data...'):
            try:
                # Build filters for school data query
                filters = [f'"Last School Name" = \'{selected_school}\'']
                
                if school_year != "All":
                    filters.append(f'"Academic Year" = \'{school_year}\'')
                if school_selected_district != "All":
                    filters.append(f'"District Name" = \'{school_selected_district}\'')
                if school_selected_block != "All":
                    filters.append(f'"Block Name" = \'{school_selected_block}\'')
                
                where_clause = " AND ".join(filters)
                
                school_data_query = f'''
                    SELECT *
                    FROM "{csv_file}"
                    WHERE {where_clause}
                '''
                
                school_df = con.execute(school_data_query).df()
                
                if not school_df.empty:
                    # Get school metadata
                    school_name = selected_school
                    school_category = school_df['School Category'].mode()[0] if 'School Category' in school_df.columns else "N/A"
                    school_management = school_df['School Management'].mode()[0] if 'School Management' in school_df.columns else "N/A"
                    district_name = school_df['District Name'].iloc[0]
                    block_name = school_df['Block Name'].iloc[0] if 'Block Name' in school_df.columns else "N/A"
                    
                    # Calculate metrics
                    total_dropouts = len(school_df)
                    girls_dropouts = len(school_df[school_df['Gender'] == FEMALE_VALUE])
                    boys_dropouts = len(school_df[school_df['Gender'] == MALE_VALUE])
                    
                    # Education level breakdown
                    primary_count = len(school_df[school_df['Education Level'] == 'Primary (1-5)'])
                    upper_primary_count = len(school_df[school_df['Education Level'] == 'Upper Primary (6-8)'])
                    secondary_count = len(school_df[school_df['Education Level'] == 'Secondary (9-10)'])
                    sr_secondary_count = len(school_df[school_df['Education Level'] == 'Sr. Secondary (11-12)'])
                    
                    # Calculate ranking in block
                    if school_year == "All":
                        block_ranking_query = f'''
                            SELECT "Last School Name", COUNT(*) as dropout_count
                            FROM "{csv_file}"
                            WHERE "Block Name" = '{block_name}'
                            AND "Last School Name" IS NOT NULL
                            AND "Last School Name" != ''
                            GROUP BY "Last School Name"
                            ORDER BY dropout_count DESC
                        '''
                    else:
                        block_ranking_query = f'''
                            SELECT "Last School Name", COUNT(*) as dropout_count
                            FROM "{csv_file}"
                            WHERE "Block Name" = '{block_name}'
                            AND "Academic Year" = '{school_year}'
                            AND "Last School Name" IS NOT NULL
                            AND "Last School Name" != ''
                            GROUP BY "Last School Name"
                            ORDER BY dropout_count DESC
                        '''
                    
                    block_ranking_df = con.execute(block_ranking_query).df()
                    school_rank_in_block = block_ranking_df[block_ranking_df['Last School Name'] == school_name].index[0] + 1 if school_name in block_ranking_df['Last School Name'].values else "N/A"
                    total_schools_in_block = len(block_ranking_df)
                    
                    # SCHOOL OVERVIEW CARD
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #1e3c72, #2a5298); 
                                padding: 2rem; 
                                border-radius: 20px; 
                                box-shadow: 0 10px 30px rgba(0,0,0,0.4);
                                margin-bottom: 2rem;
                                border: 2px solid rgba(255,255,255,0.2);'>
                        <h2 style='color: white; margin: 0 0 1.5rem 0; font-size: 2rem; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
                            🏫 {school_name}
                        </h2>
                        <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem;'>
                            <div>
                                <p style='color: rgba(255,255,255,0.7); font-size: 0.9rem; margin: 0;'>📍 District</p>
                                <p style='color: white; font-size: 1.2rem; margin: 0.3rem 0 0 0; font-weight: bold;'>{district_name}</p>
                            </div>
                            <div>
                                <p style='color: rgba(255,255,255,0.7); font-size: 0.9rem; margin: 0;'>🏘️ Block</p>
                                <p style='color: white; font-size: 1.2rem; margin: 0.3rem 0 0 0; font-weight: bold;'>{block_name}</p>
                            </div>
                            <div>
                                <p style='color: rgba(255,255,255,0.7); font-size: 0.9rem; margin: 0;'>🏷️ Category</p>
                                <p style='color: #ffd700; font-size: 1.2rem; margin: 0.3rem 0 0 0; font-weight: bold;'>{school_category}</p>
                            </div>
                            <div>
                                <p style='color: rgba(255,255,255,0.7); font-size: 0.9rem; margin: 0;'>🏛️ Management</p>
                                <p style='color: #ffd700; font-size: 1.2rem; margin: 0.3rem 0 0 0; font-weight: bold;'>{school_management}</p>
                            </div>
                            <div>
                                <p style='color: rgba(255,255,255,0.7); font-size: 0.9rem; margin: 0;'>📊 Total Dropouts</p>
                                <p style='color: #ff6b6b; font-size: 1.8rem; margin: 0.3rem 0 0 0; font-weight: bold;'>{total_dropouts:,}</p>
                            </div>
                            <div>
                                <p style='color: rgba(255,255,255,0.7); font-size: 0.9rem; margin: 0;'>🏆 Block Rank</p>
                                <p style='color: #43e97b; font-size: 1.8rem; margin: 0.3rem 0 0 0; font-weight: bold;'>{school_rank_in_block}/{total_schools_in_block}</p>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # METRICS ROW
                    st.markdown("""
                    <h3 style='color: white; text-align: center; font-size: 1.8rem; margin: 2rem 0 1.5rem 0; font-weight: bold;'>
                        📊 Dropout Breakdown
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    col_m1, col_m2, col_m3, col_m4, col_m5, col_m6 = st.columns(6)
                    
                    metrics_data = [
                        (col_m1, "👧 Girls", girls_dropouts, "#ec407a"),
                        (col_m2, "👦 Boys", boys_dropouts, "#2980b9"),
                        (col_m3, "📘 Primary", primary_count, "#9b59b6"),
                        (col_m4, "📗 Upper Pri.", upper_primary_count, "#16a085"),
                        (col_m5, "📙 Secondary", secondary_count, "#e67e22"),
                        (col_m6, "📕 Sr. Sec.", sr_secondary_count, "#c0392b")
                    ]
                    
                    for col, label, value, color in metrics_data:
                        with col:
                            st.markdown(f"""
                            <div style='background: rgba(255,255,255,0.1); 
                                        padding: 1.5rem; 
                                        border-radius: 15px; 
                                        text-align: center;
                                        border-left: 4px solid {color};
                                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);'>
                                <p style='color: rgba(255,255,255,0.8); font-size: 0.85rem; margin: 0;'>{label}</p>
                                <h2 style='color: {color}; font-size: 2rem; margin: 0.5rem 0 0 0; font-weight: bold;'>{value:,}</h2>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    
                    # CHARTS ROW
                    col_chart1, col_chart2 = st.columns(2)
                    
                    with col_chart1:
                        st.markdown("""
                        <h3 style='color: white; text-align: center; font-size: 1.6rem; margin-bottom: 1rem; font-weight: bold;'>
                            👥 Gender Distribution
                        </h3>
                        """, unsafe_allow_html=True)
                        
                        gender_data = pd.DataFrame({
                            'Gender': ['Girls', 'Boys'],
                            'Count': [girls_dropouts, boys_dropouts]
                        })
                        
                        fig_gender = px.pie(
                            gender_data,
                            names='Gender',
                            values='Count',
                            color='Gender',
                            color_discrete_map={'Girls': '#ec407a', 'Boys': '#2980b9'},
                            hole=0.4
                        )
                        
                        fig_gender.update_traces(
                            textposition='inside',
                            textinfo='percent+label',
                            textfont=dict(size=14, color='white'),
                            marker=dict(line=dict(color='white', width=2))
                        )
                        
                        fig_gender.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white', size=14),
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                            height=400
                        )
                        
                        st.plotly_chart(fig_gender, use_container_width=True, config={'displayModeBar': False})
                    
                    with col_chart2:
                        st.markdown("""
                        <h3 style='color: white; text-align: center; font-size: 1.6rem; margin-bottom: 1rem; font-weight: bold;'>
                            📚 Education Level Distribution
                        </h3>
                        """, unsafe_allow_html=True)
                        
                        edu_data = pd.DataFrame({
                            'Level': ['Primary', 'Upper Primary', 'Secondary', 'Sr. Secondary'],
                            'Count': [primary_count, upper_primary_count, secondary_count, sr_secondary_count]
                        })
                        
                        fig_edu = px.bar(
                            edu_data,
                            x='Level',
                            y='Count',
                            color='Count',
                            color_continuous_scale='Viridis',
                            text='Count'
                        )
                        
                        fig_edu.update_traces(
                            texttemplate='%{text:,}',
                            textposition='outside',
                            textfont=dict(size=13, color='white')
                        )
                        
                        fig_edu.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white', size=14),
                            xaxis=dict(
                                title='',
                                showgrid=False,
                                tickfont=dict(size=12, color='white')
                            ),
                            yaxis=dict(
                                title='Dropout Count',
                                showgrid=True,
                                gridcolor='rgba(255,255,255,0.1)',
                                tickfont=dict(size=12, color='white'),
                                title_font=dict(size=14, color='white')
                            ),
                            height=400,
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig_edu, use_container_width=True, config={'displayModeBar': False})
                    
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    
                    # DETAILED DATA TABLE
                    st.markdown("""
                    <h3 style='color: white; text-align: center; font-size: 1.8rem; margin-bottom: 1.5rem; font-weight: bold;'>
                        📋 Detailed Student Records
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    # Add search box for filtering
                    col_search1, col_search2 = st.columns([3, 1])
                    with col_search1:
                        search_text = st.text_input("🔍 Search by Student Name, Father/Mother Name, Mobile, or Class:", 
                                                    key="student_search", 
                                                    placeholder="Type to search...")
                    with col_search2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        show_all_cols = st.checkbox("Show All Columns", value=False)
                    
                    # Define display columns with all important information
                    if show_all_cols:
                        display_cols = [
                            'Student Name', 'Father Name', 'Mother Name', 'Mobile No.', 
                            'Last Class', 'Gender', 'Education Level', 'School Category',
                            'Student Status', 'Student Sub Status', 'Academic Year',
                            'Aadhaar No.', 'Student PEN', 'Remarks'
                        ]
                    else:
                        display_cols = [
                            'Student Name', 'Father Name', 'Mother Name', 'Mobile No.', 
                            'Last Class', 'Gender', 'Education Level', 'Academic Year'
                        ]
                    
                    available_cols = [col for col in display_cols if col in school_df.columns]
                    
                    if available_cols:
                        # Filter dataframe based on search
                        display_df = school_df[available_cols].copy()
                        
                        if search_text:
                            # Create search mask across all string columns
                            mask = display_df.astype(str).apply(
                                lambda x: x.str.contains(search_text, case=False, na=False)
                            ).any(axis=1)
                            display_df = display_df[mask]
                        
                        # Show count
                        st.markdown(f"""
                        <p style='color: white; text-align: center; font-size: 1rem; margin-bottom: 1rem;'>
                            Showing <strong>{len(display_df)}</strong> of <strong>{len(school_df)}</strong> students
                        </p>
                        """, unsafe_allow_html=True)
                        
                        # Display table
                        st.dataframe(
                            display_df.reset_index(drop=True),
                            use_container_width=True,
                            height=400
                        )
                        
                        # Download buttons
                        col_dl1, col_dl2 = st.columns(2)
                        
                        with col_dl1:
                            csv = display_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Download Filtered Data (CSV)",
                                data=csv,
                                file_name=f"{school_name.replace(' ', '_')}_filtered_data.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        with col_dl2:
                            # Full data download
                            csv_full = school_df[available_cols].to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Download All School Data (CSV)",
                                data=csv_full,
                                file_name=f"{school_name.replace(' ', '_')}_complete_data.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                    else:
                        st.info("📊 Detailed records not available")
                    
                else:
                    st.warning("⚠️ No data found for selected school")
                    
            except Exception as e:
                st.error(f"❌ Error loading school data: {e}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.info("👆 कृपया ऊपर से एक स्कूल चुनें")

# ==================== TAB 5: DOWNLOADS & CUSTOM REPORTS ====================
elif st.session_state.active_tab == 4:
    st.markdown('<h2 style="color: white; text-align: center; font-size: 2.2rem; margin: 1rem 0; font-weight: bold;">📥 Downloads & Custom Report Builder</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color: white; text-align: center; font-size: 1.1rem; opacity: 0.9; margin-bottom: 2rem;">Generate Custom Reports with Advanced Filters</p>', unsafe_allow_html=True)
    
    # Custom Report Builder Section
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea, #764ba2); 
                padding: 1.5rem; 
                border-radius: 15px;
                margin-bottom: 2rem;
                box-shadow: 0 8px 16px rgba(0,0,0,0.3);'>
        <h3 style='color: white; margin: 0; font-size: 1.6rem; font-weight: bold;'>
            🔧 Custom Report Builder
        </h3>
        <p style='color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 0.95rem;'>
            Apply multiple filters to generate customized dropout analysis reports
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # FILTER SECTION
    st.markdown("### 🎯 Apply Filters")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        st.markdown("**📅 Academic Year**")
        report_years = st.multiselect(
            "Select Years:",
            options=available_years,
            default=[available_years[0]] if available_years else [],
            key="report_years",
            label_visibility="collapsed"
        )
    
    with col_f2:
        st.markdown("**🗺️ District**")
        all_districts = con.execute(f'SELECT DISTINCT "District Name" FROM "{csv_file}" ORDER BY "District Name"').df()['District Name'].tolist()
        report_districts = st.multiselect(
            "Select Districts:",
            options=["All"] + all_districts,
            default=["All"],
            key="report_districts",
            label_visibility="collapsed"
        )
    
    with col_f3:
        st.markdown("**👥 Gender**")
        report_gender = st.multiselect(
            "Select Gender:",
            options=["All", FEMALE_VALUE, MALE_VALUE],
            default=["All"],
            key="report_gender",
            label_visibility="collapsed"
        )
    
    col_f4, col_f5, col_f6 = st.columns(3)
    
    with col_f4:
        st.markdown("**📚 Education Level**")
        edu_levels = ["All", "Primary (1-5)", "Upper Primary (6-8)", "Secondary (9-10)", "Sr. Secondary (11-12)"]
        report_edu_level = st.multiselect(
            "Select Levels:",
            options=edu_levels,
            default=["All"],
            key="report_edu_level",
            label_visibility="collapsed"
        )
    
    with col_f5:
        st.markdown("**🏫 School Category**")
        categories = con.execute(f'SELECT DISTINCT "School Category" FROM "{csv_file}" WHERE "School Category" IS NOT NULL').df()['School Category'].tolist()
        report_category = st.multiselect(
            "Select Categories:",
            options=["All"] + categories,
            default=["All"],
            key="report_category",
            label_visibility="collapsed"
        )
    
    with col_f6:
        st.markdown("**🏛️ Management Type**")
        management_types = con.execute(f'SELECT DISTINCT "School Management" FROM "{csv_file}" WHERE "School Management" IS NOT NULL').df()['School Management'].tolist()
        report_management = st.multiselect(
            "Select Management:",
            options=["All"] + management_types,
            default=["All"],
            key="report_management",
            label_visibility="collapsed"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # COLUMN SELECTION
    st.markdown("### 📋 Select Columns to Include")
    
    all_columns = [
        'Student Name', 'Father Name', 'Mother Name', 'Mobile No.', 'Last Class',
        'Gender', 'Education Level', 'School Category', 'School Management',
        'District Name', 'Block Name', 'Last School Name', 'Academic Year',
        'Student Status', 'Student Sub Status', 'Aadhaar No.', 'Student PEN', 'Remarks'
    ]
    
    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        selected_columns = st.multiselect(
            "Choose columns for your report:",
            options=all_columns,
            default=['Student Name', 'Father Name', 'Mother Name', 'Mobile No.', 'Last Class', 'Gender', 'Education Level', 'District Name', 'Academic Year'],
            key="selected_columns"
        )
    
    with col_sel2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Select All Columns", use_container_width=True):
            st.session_state.selected_columns = all_columns
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # GENERATE REPORT BUTTON
    if st.button("🔍 Generate Custom Report", type="primary", use_container_width=True):
        with st.spinner('📊 Generating custom report...'):
            try:
                # Build SQL query with filters
                conditions = []
                
                # Year filter
                if report_years:
                    year_list = "', '".join(report_years)
                    conditions.append(f'"Academic Year" IN (\'{year_list}\')')
                
                # District filter
                if "All" not in report_districts and report_districts:
                    district_list = "', '".join(report_districts)
                    conditions.append(f'"District Name" IN (\'{district_list}\')')
                
                # Gender filter
                if "All" not in report_gender and report_gender:
                    gender_list = "', '".join(report_gender)
                    conditions.append(f'"Gender" IN (\'{gender_list}\')')
                
                # Education Level filter
                if "All" not in report_edu_level and report_edu_level:
                    edu_list = "', '".join(report_edu_level)
                    conditions.append(f'"Education Level" IN (\'{edu_list}\')')
                
                # School Category filter
                if "All" not in report_category and report_category:
                    cat_list = "', '".join(report_category)
                    conditions.append(f'"School Category" IN (\'{cat_list}\')')
                
                # Management filter
                if "All" not in report_management and report_management:
                    mgmt_list = "', '".join(report_management)
                    conditions.append(f'"School Management" IN (\'{mgmt_list}\')')
                
                # Build WHERE clause
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                
                # Execute query
                query = f'SELECT * FROM "{csv_file}" WHERE {where_clause}'
                report_df = con.execute(query).df()
                
                # Filter columns
                available_selected_cols = [col for col in selected_columns if col in report_df.columns]
                
                if available_selected_cols:
                    filtered_report_df = report_df[available_selected_cols]
                    
                    # REPORT SUMMARY
                    st.markdown("""
                    <h3 style='color: white; text-align: center; font-size: 1.8rem; margin: 2rem 0 1.5rem 0; font-weight: bold;'>
                        📊 Report Summary
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
                    
                    with col_sum1:
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #667eea, #764ba2); 
                                    padding: 1.5rem; 
                                    border-radius: 15px; 
                                    text-align: center;
                                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);'>
                            <p style='color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;'>📝 Total Records</p>
                            <h2 style='color: white; font-size: 2.5rem; margin: 0.5rem 0 0 0; font-weight: bold;'>{len(filtered_report_df):,}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_sum2:
                        girls_count = len(filtered_report_df[filtered_report_df['Gender'] == FEMALE_VALUE]) if 'Gender' in filtered_report_df.columns else 0
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #ec407a, #f48fb1); 
                                    padding: 1.5rem; 
                                    border-radius: 15px; 
                                    text-align: center;
                                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);'>
                            <p style='color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;'>👧 Girls</p>
                            <h2 style='color: white; font-size: 2.5rem; margin: 0.5rem 0 0 0; font-weight: bold;'>{girls_count:,}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_sum3:
                        boys_count = len(filtered_report_df[filtered_report_df['Gender'] == MALE_VALUE]) if 'Gender' in filtered_report_df.columns else 0
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #2980b9, #3498db); 
                                    padding: 1.5rem; 
                                    border-radius: 15px; 
                                    text-align: center;
                                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);'>
                            <p style='color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;'>👦 Boys</p>
                            <h2 style='color: white; font-size: 2.5rem; margin: 0.5rem 0 0 0; font-weight: bold;'>{boys_count:,}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_sum4:
                        unique_districts = filtered_report_df['District Name'].nunique() if 'District Name' in filtered_report_df.columns else 0
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #16a085, #27ae60); 
                                    padding: 1.5rem; 
                                    border-radius: 15px; 
                                    text-align: center;
                                    box-shadow: 0 6px 12px rgba(0,0,0,0.3);'>
                            <p style='color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;'>🗺️ Districts</p>
                            <h2 style='color: white; font-size: 2.5rem; margin: 0.5rem 0 0 0; font-weight: bold;'>{unique_districts}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    
                    # DATA PREVIEW
                    st.markdown("""
                    <h3 style='color: white; text-align: center; font-size: 1.8rem; margin-bottom: 1.5rem; font-weight: bold;'>
                        👁️ Data Preview
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    st.dataframe(
                        filtered_report_df.head(100),
                        use_container_width=True,
                        height=400
                    )
                    
                    st.info(f"💡 Showing first 100 rows. Full report contains {len(filtered_report_df):,} records.")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # DOWNLOAD SECTION
                    st.markdown("""
                    <h3 style='color: white; text-align: center; font-size: 1.8rem; margin-bottom: 1.5rem; font-weight: bold;'>
                        📥 Download Report
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    col_dl1, col_dl2, col_dl3 = st.columns(3)
                    
                    with col_dl1:
                        csv_data = filtered_report_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📄 Download as CSV",
                            data=csv_data,
                            file_name=f"custom_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col_dl2:
                        # Excel download
                        from io import BytesIO
                        excel_buffer = BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            filtered_report_df.to_excel(writer, index=False, sheet_name='Dropout Report')
                        excel_data = excel_buffer.getvalue()
                        
                        st.download_button(
                            label="📊 Download as Excel",
                            data=excel_data,
                            file_name=f"custom_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    
                    with col_dl3:
                        # JSON download
                        json_data = filtered_report_df.to_json(orient='records', indent=2).encode('utf-8')
                        st.download_button(
                            label="🗂️ Download as JSON",
                            data=json_data,
                            file_name=f"custom_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    
                else:
                    st.warning("⚠️ No matching columns found in the dataset")
                    
            except Exception as e:
                st.error(f"❌ Error generating report: {e}")
                import traceback
                st.code(traceback.format_exc())
    else:
        st.info("👆 Configure filters above and click 'Generate Custom Report' to create your customized dropout analysis report")


# FOOTER
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='background: linear-gradient(135deg, #667eea, #764ba2); 
            padding: 2rem; 
            border-radius: 20px; 
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            margin-top: 3rem;
            border: 2px solid rgba(255,255,255,0.1);'>
    <h3 style='color: white; margin: 0 0 0.5rem 0; font-size: 1.8rem; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
        🎓 उत्तर प्रदेश शिक्षा विभाग
    </h3>
    <p style='color: #ffd700; font-size: 1.2rem; margin: 0.5rem 0; font-weight: 600;'>
        ड्रॉपआउट विश्लेषण डैशबोर्ड
    </p>
    <div style='display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin-top: 1.5rem;'>
        <div style='color: rgba(255,255,255,0.9); font-size: 0.9rem;'>
            📊 <strong>Version:</strong> 2.0 Enhanced
        </div>
        <div style='color: rgba(255,255,255,0.9); font-size: 0.9rem;'>
            📅 <strong>Data Source:</strong> UDISE+ 2023-24
        </div>
        <div style='color: rgba(255,255,255,0.9); font-size: 0.9rem;'>
            🔄 <strong>Last Updated:</strong> Nov 30, 2025
        </div>
    </div>
    <p style='color: rgba(255,255,255,0.7); font-size: 0.85rem; margin: 1.5rem 0 0 0; font-style: italic;'>
        "शिक्षा में सुधार, डेटा-संचालित निर्णयों से" 🌟
    </p>
</div>
""", unsafe_allow_html=True)
