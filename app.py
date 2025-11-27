import os
import zipfile
import subprocess
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb

# --------- Config ----------
CSV_FILENAME = "Master_UP_Dropout_Database.csv"
KAGGLE_DATASET = "alokkmohan/dropout"  # owner/dataset
DATA_DIR = "data"
LOCAL_CSV_PATHS = [
    CSV_FILENAME,
    os.path.join(DATA_DIR, CSV_FILENAME),
]

os.makedirs(DATA_DIR, exist_ok=True)

# --------- UI / Page config ----------
st.set_page_config(page_title="UP Dropout Analysis", layout="wide")
# Custom CSS (kept from your original)
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
    .chart-container {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem auto;
        max-width: 1200px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">UP Dropout Analysis</h1>', unsafe_allow_html=True)

# --------- Helpers for Kaggle download ----------
def find_local_csv():
    for p in LOCAL_CSV_PATHS:
        if os.path.exists(p):
            return p
    return None

def download_with_kaggle_api_via_package(dataset_slug: str, file_name: str, dest_folder: str) -> str:
    """Try to download using kaggle python package (KaggleApi). Requires kaggle creds in ~/.kaggle/kaggle.json or env vars."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except Exception as e:
        raise RuntimeError("kaggle package not available. Ensure 'kaggle' is in requirements.") from e

    api = KaggleApi()
    api.authenticate()
    api.dataset_download_file(dataset_slug, file_name, path=dest_folder, force=False)
    zipped = os.path.join(dest_folder, file_name + ".zip")
    out_path = os.path.join(dest_folder, file_name)
    if os.path.exists(zipped):
        with zipfile.ZipFile(zipped, 'r') as zf:
            if file_name in zf.namelist():
                zf.extract(file_name, path=dest_folder)
            else:
                zf.extractall(path=dest_folder)
        try:
            os.remove(zipped)
        except:
            pass
    if os.path.exists(out_path):
        return out_path
    for f in os.listdir(dest_folder):
        if f.lower() == file_name.lower():
            return os.path.join(dest_folder, f)
    raise FileNotFoundError(f"Could not find {file_name} after Kaggle download in {dest_folder}")

def download_with_kaggle_cli(dataset_slug: str, file_name: str, dest_folder: str, kaggle_api_token: str = None) -> str:
    """
    Use kaggle CLI to download. If kaggle_api_token provided, set environment variable KAGGLE_API_TOKEN for the subprocess.
    """
    env = os.environ.copy()
    if kaggle_api_token:
        env["KAGGLE_API_TOKEN"] = kaggle_api_token

    cmd = ["kaggle", "datasets", "download", "-d", dataset_slug, "-f", file_name, "-p", dest_folder, "--force"]
    proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"kaggle CLI failed: {proc.stderr.strip()}")
    zipped = os.path.join(dest_folder, file_name + ".zip")
    out_path = os.path.join(dest_folder, file_name)
    if os.path.exists(zipped):
        with zipfile.ZipFile(zipped, 'r') as zf:
            if file_name in zf.namelist():
                zf.extract(file_name, path=dest_folder)
            else:
                zf.extractall(path=dest_folder)
        try:
            os.remove(zipped)
        except:
            pass
    if os.path.exists(out_path):
        return out_path
    for f in os.listdir(dest_folder):
        if f.lower() == file_name.lower():
            return os.path.join(dest_folder, f)
    raise FileNotFoundError(f"Could not find {file_name} after kaggle CLI download in {dest_folder}")

def ensure_csv_available():
    # 1) if local present, use it
    local = find_local_csv()
    if local:
        st.info(f"Using local CSV: {local}")
        return local

    st.info("CSV not found locally. Attempting Kaggle download...")

    # 2) Check for credentials in Streamlit secrets (preferred for Cloud)
    kaggle_user = None
    kaggle_key = None
    kaggle_api_token = None

    # Streamlit secrets may contain KAGGLE_USERNAME & KAGGLE_KEY or KAGGLE_API_TOKEN
    try:
        kaggle_user = st.secrets.get("alokkmohan")
        kaggle_key = st.secrets.get("KGAT_17ce0406750ab83eefc0b8244dca6adf")
    except Exception:
        kaggle_user = None
        kaggle_key = None

    try:
        kaggle_api_token = st.secrets.get("kaggle competitions list")
    except Exception:
        kaggle_api_token = None

    # fallback to environment variables (if set)
    if not kaggle_user:
        kaggle_user = os.environ.get("alokkmohan")
    if not kaggle_key:
        kaggle_key = os.environ.get("KGAT_17ce0406750ab83eefc0b8244dca6adf")
    if not kaggle_api_token:
        kaggle_api_token = os.environ.get("kaggle competitions list")

    # If username/key present, write kaggle.json so KaggleApi can use it
    if kaggle_user and kaggle_key:
        try:
            import json
            kaggle_dir = os.path.join(os.path.expanduser("~"), ".kaggle")
            os.makedirs(kaggle_dir, exist_ok=True)
            kaggle_json = os.path.join(kaggle_dir, "kaggle.json")
            with open(kaggle_json, "w", encoding="utf-8") as f:
                json.dump({"username": kaggle_user, "key": kaggle_key}, f)
            try:
                os.chmod(kaggle_json, 0o600)
            except Exception:
                pass
            # Try package-based download first
            try:
                return download_with_kaggle_api_via_package(KAGGLE_DATASET, CSV_FILENAME, DATA_DIR)
            except Exception as e:
                st.warning(f"Kaggle package download failed, will try kaggle CLI as fallback: {e}")
        except Exception as e:
            st.warning(f"Could not write kaggle.json: {e}")

    # If KAGGLE_API_TOKEN present, try CLI with token in env
    if kaggle_api_token:
        try:
            return download_with_kaggle_cli(KAGGLE_DATASET, CSV_FILENAME, DATA_DIR, kaggle_api_token=kaggle_api_token)
        except Exception as e:
            st.warning(f"kaggle CLI download with KAGGLE_API_TOKEN failed: {e}")

    # As last attempt, try kaggle CLI without token env (it may pick up ~/.kaggle)
    try:
        return download_with_kaggle_cli(KAGGLE_DATASET, CSV_FILENAME, DATA_DIR, kaggle_api_token=None)
    except Exception as e:
        st.error(
            "Failed to download CSV from Kaggle. Please ensure Kaggle credentials are available.\n\n"
            "- For Streamlit Cloud: add secrets KAGGLE_USERNAME & KAGGLE_KEY OR KAGGLE_API_TOKEN.\n"
            "- For local testing: add ~/.kaggle/kaggle.json or set env vars KAGGLE_USERNAME/KAGGLE_KEY.\n\n"
            f"Error: {e}"
        )
        st.stop()

# --------- Load summary excel files (your originals) ----------
@st.cache_data
def load_summary_excel():
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

df_edu, df_district = load_summary_excel()

# --------- Ensure main CSV available ----------
csv_path = ensure_csv_available()

# Connect to duckdb (in-memory)
@st.cache_resource
def get_duckdb_conn():
    return duckdb.connect()

con = get_duckdb_conn()

# Helper to detect gender values in CSV via duckdb
@st.cache_data
def detect_gender_values(csv_p):
    try:
        q = f"SELECT DISTINCT \"Gender\" FROM read_csv_auto('{csv_p}') LIMIT 50"
        df = con.execute(q).df()
        vals = [str(v).upper() for v in df['Gender'].dropna().tolist()]
        female_val = next((v for v in vals if v in ['FEMALE', 'F', 'GIRL']), 'FEMALE')
        male_val = next((v for v in vals if v in ['MALE', 'M', 'BOY']), 'MALE')
        return female_val, male_val
    except Exception:
        return 'FEMALE', 'MALE'

FEMALE_VALUE, MALE_VALUE = detect_gender_values(csv_path)

# Available years from your summary df_edu (keeps same logic)
available_years = [col for col in df_edu.columns if col != 'Education Level']

# Session state / tabs (kept from your original)
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

tab_cols = st.columns(4)
tab_names = ["🏠 Home", "🗺️ District-wise Analysis", "🏫 Block-wise Analysis", "📋 MIS & Downloads"]

for idx, (col, name) in enumerate(zip(tab_cols, tab_names)):
    with col:
        if st.button(name, key=f"tab_{idx}", use_container_width=True,
                     type="primary" if st.session_state.active_tab == idx else "secondary"):
            st.session_state.active_tab = idx

st.markdown("<br>", unsafe_allow_html=True)

# ---------- HOME TAB (Condensed: uses your calculations) ----------
if st.session_state.active_tab == 0:
    col_y1, col_y2, col_y3 = st.columns([1, 2, 1])
    with col_y2:
        st.markdown("### 📅 Select Academic Year")
        selected_year = st.selectbox("शैक्षणिक वर्ष:", ["All"] + available_years, key="year_filter", label_visibility="collapsed")

    with st.spinner('📊 Data लोड हो रहा है...'):
        try:
            if selected_year == "All":
                total_dropouts = int(df_edu[available_years].sum().sum())
                total_girls = int(total_dropouts * 0.48)
                total_boys = int(total_dropouts * 0.52)
                edu_levels = {}
                for level in ['Primary (1-5)','Upper Primary (6-8)','Secondary (9-10)','Sr. Secondary (11-12)']:
                    row = df_edu[df_edu['Education Level'] == level]
                    edu_levels[level] = int(row[available_years].sum().sum()) if not row.empty else 0
            else:
                if selected_year in df_edu.columns:
                    total_dropouts = int(df_edu[selected_year].sum())
                    total_girls = int(total_dropouts * 0.48)
                    total_boys = int(total_dropouts * 0.52)
                    edu_levels = {}
                    for level in ['Primary (1-5)','Upper Primary (6-8)','Secondary (9-10)','Sr. Secondary (11-12)']:
                        row = df_edu[df_edu['Education Level'] == level]
                        edu_levels[level] = int(row[selected_year].values[0]) if not row.empty else 0
                else:
                    total_dropouts = total_girls = total_boys = 0
                    edu_levels = {k:0 for k in ['Primary (1-5)','Upper Primary (6-8)','Secondary (9-10)','Sr. Secondary (11-12)']}
        except Exception as e:
            st.error(f"❌ Error: {e}")
            total_dropouts = total_girls = total_boys = 0
            edu_levels = {k:0 for k in ['Primary (1-5)','Upper Primary (6-8)','Secondary (9-10)','Sr. Secondary (11-12)']}

    # Display top metrics and Top 10 districts (kept original plotting logic)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div style='background: white; padding: 2rem; border-radius: 12px; text-align:center;'><h4>Total Dropouts</h4><h2>{total_dropouts:,}</h2></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div style='background: white; padding: 2rem; border-radius: 12px; text-align:center;'><h4>Total Girls</h4><h2>{total_girls:,}</h2></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div style='background: white; padding: 2rem; border-radius: 12px; text-align:center;'><h4>Total Boys</h4><h2>{total_boys:,}</h2></div>", unsafe_allow_html=True)

    st.markdown("<br>")

    # Top 10 districts via DuckDB reading CSV (fast)
    try:
        if selected_year == "All":
            q = f'''
                SELECT "District Name", COUNT(*) AS DropoutCount
                FROM read_csv_auto('{csv_path}')
                GROUP BY "District Name"
                ORDER BY DropoutCount DESC
                LIMIT 10
            '''
        else:
            q = f'''
                SELECT "District Name", COUNT(*) AS DropoutCount
                FROM read_csv_auto('{csv_path}')
                WHERE "Academic Year" = '{selected_year}'
                GROUP BY "District Name"
                ORDER BY DropoutCount DESC
                LIMIT 10
            '''
        top_df = con.execute(q).df()
        if not top_df.empty:
            fig = go.Figure(go.Bar(
                x=top_df['District Name'],
                y=top_df['DropoutCount'],
                marker=dict(color=top_df['DropoutCount'], colorscale='Viridis'),
                text=top_df['DropoutCount'],
                textposition='outside'
            ))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("No district data available")
    except Exception as e:
        st.error(f"Error generating top districts chart: {e}")

# ---------- DISTRICT TAB (kept your logic) ----------
elif st.session_state.active_tab == 1:
    st.markdown('<h2 style="color: white;">🗺️ District-wise Detailed Analysis</h2>', unsafe_allow_html=True)
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        selected_year_district = st.selectbox("शैक्षणिक वर्ष:", ["All"] + available_years, key="year_filter_district", label_visibility="collapsed")
    with col_filter2:
        try:
            districts_list = con.execute(f'SELECT DISTINCT "District Name" FROM read_csv_auto(\'{csv_path}\') ORDER BY "District Name"').df()['District Name'].tolist()
        except Exception as e:
            st.error(f"❌ Error: {e}")
            districts_list = []
        selected_district = st.selectbox("जिला चुनें:", ["-- Select District --"] + districts_list, key="district_filter", label_visibility="collapsed")

    if selected_district != "-- Select District --":
        with st.spinner(f'Loading {selected_district}...'):
            try:
                if selected_year_district == "All":
                    district_query = f'''
                        SELECT COUNT(*) as total,
                               SUM(CASE WHEN UPPER("Gender") LIKE '%{FEMALE_VALUE.upper()}%' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN UPPER("Gender") LIKE '%{MALE_VALUE.upper()}%' THEN 1 ELSE 0 END) as boys
                        FROM read_csv_auto('{csv_path}')
                        WHERE "District Name" = '{selected_district}'
                    '''
                else:
                    district_query = f'''
                        SELECT COUNT(*) as total,
                               SUM(CASE WHEN UPPER("Gender") LIKE '%{FEMALE_VALUE.upper()}%' THEN 1 ELSE 0 END) as girls,
                               SUM(CASE WHEN UPPER("Gender") LIKE '%{MALE_VALUE.upper()}%' THEN 1 ELSE 0 END) as boys
                        FROM read_csv_auto('{csv_path}')
                        WHERE "District Name" = '{selected_district}' AND "Academic Year" = '{selected_year_district}'
                    '''
                district_stats = con.execute(district_query).df().iloc[0]
                district_total = int(district_stats['total'])
                district_girls = int(district_stats['girls'])
                district_boys = int(district_stats['boys'])
            except Exception as e:
                st.error(f"❌ Error: {e}")
                district_total = district_girls = district_boys = 0

        # Display small metrics (kept concise)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", f"{district_total:,}")
        c2.metric("Girls", f"{district_girls:,}")
        c3.metric("Boys", f"{district_boys:,}")

# ---------- BLOCK TAB (kept your logic but simplified) ----------
elif st.session_state.active_tab == 2:
    st.markdown('<h2 style="color: white;">🏫 Block-wise Analysis</h2>', unsafe_allow_html=True)
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        block_year = st.selectbox("Year:", ["All"] + available_years, key="block_year_filter", label_visibility="collapsed")
    with col_f2:
        if block_year == "All":
            districts_query = f'SELECT DISTINCT "District Name" FROM read_csv_auto(\'{csv_path}\') ORDER BY "District Name"'
        else:
            districts_query = f'SELECT DISTINCT "District Name" FROM read_csv_auto(\'{csv_path}\') WHERE "Academic Year" = \'{block_year}\' ORDER BY "District Name"'
        block_districts = con.execute(districts_query).df()['District Name'].tolist()
        block_selected_district = st.selectbox("District:", ["Select"] + block_districts, key="block_district_filter", label_visibility="collapsed")
    with col_f3:
        if block_selected_district != "Select":
            if block_year == "All":
                blocks_query = f'SELECT DISTINCT "Block Name" FROM read_csv_auto(\'{csv_path}\') WHERE "District Name" = \'{block_selected_district}\' ORDER BY "Block Name"'
            else:
                blocks_query = f'SELECT DISTINCT "Block Name" FROM read_csv_auto(\'{csv_path}\') WHERE "District Name" = \'{block_selected_district}\' AND "Academic Year" = \'{block_year}\' ORDER BY "Block Name"'
            block_blocks = con.execute(blocks_query).df()['Block Name'].tolist()
            block_selected_block = st.selectbox("Block:", ["Select"] + block_blocks, key="block_block_filter", label_visibility="collapsed")
        else:
            block_selected_block = "Select"
            st.selectbox("Block:", ["Select"], key="block_block_filter_empty", label_visibility="collapsed", disabled=True)

    if block_selected_district != "Select" and block_selected_block != "Select":
        with st.spinner('Loading block data...'):
            try:
                # Query for block summary (kept your original aggregated fields)
                block_query = f'''
                    SELECT COUNT(*) as total_count,
                           SUM(CASE WHEN UPPER("Gender") LIKE '%{FEMALE_VALUE.upper()}%' THEN 1 ELSE 0 END) as female_count,
                           SUM(CASE WHEN UPPER("Gender") LIKE '%{MALE_VALUE.upper()}%' THEN 1 ELSE 0 END) as male_count
                    FROM read_csv_auto('{csv_path}')
                    WHERE "District Name" = '{block_selected_district}'
                    AND "Block Name" = '{block_selected_block}'
                    {'AND "Academic Year" = \'' + block_year + '\'' if block_year != "All" else ''}
                '''
                block_stats = con.execute(block_query).df().iloc[0]
                st.metric("Total", int(block_stats['total_count']))
                st.metric("Girls", int(block_stats['female_count']))
                st.metric("Boys", int(block_stats['male_count']))
            except Exception as e:
                st.error(f"Error: {e}")

# ---------- MIS & DOWNLOADS TAB (kept your logic, safe downloads) ----------
elif st.session_state.active_tab == 3:
    st.markdown('<h2 style="color: white;">📋 MIS Reports & Data Downloads</h2>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Example quick report: Top 50 critical schools (kept original query)
    if st.button("🏫 Generate Top 50 Critical Schools Report", use_container_width=True):
        with st.spinner("Generating report..."):
            try:
                critical_query = f'''
                    SELECT "Last School Name", "District Name", "Block Name", COUNT(*) as dropout_count
                    FROM read_csv_auto('{csv_path}')
                    WHERE "Last School Name" IS NOT NULL AND "Last School Name" != ''
                    GROUP BY "Last School Name", "District Name", "Block Name"
                    ORDER BY dropout_count DESC
                    LIMIT 50
                '''
                df_critical = con.execute(critical_query).df()
                if df_critical.empty:
                    st.warning("No data found for this report.")
                else:
                    csv_bytes = df_critical.to_csv(index=False).encode('utf-8')
                    st.download_button("⬇️ Download Top 50 Critical Schools", data=csv_bytes, file_name="top_50_critical_schools.csv", mime="text/csv")
                    st.success(f"Report ready ({len(df_critical):,} rows).")
            except Exception as e:
                st.error(f"Error generating report: {e}")

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: white; padding: 1.5rem; background: rgba(0,0,0,0.2); border-radius: 10px;'>
    <p style='font-size: 1.1rem; margin: 0;'> Educate Girls</p>
    <p style='font-size: 0.9rem; opacity: 0.8; margin-top: 0.5rem;'>Dashboard powered by Alok Mohan</p>
</div>
""", unsafe_allow_html=True)
