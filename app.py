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
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">UP Dropout Analysis</h1>', unsafe_allow_html=True)

# --------- Helpers for Kaggle download (FIXED secrets handling) ----------
def find_local_csv():
    for p in LOCAL_CSV_PATHS:
        if os.path.exists(p):
            return p
    return None

def download_with_kaggle_api_via_package(dataset_slug: str, file_name: str, dest_folder: str) -> str:
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
    # 1) local
    local = find_local_csv()
    if local:
        st.info(f"Using local CSV: {local}")
        return local

    st.info("CSV not found locally. Attempting Kaggle download...")

    # 2) read secrets (CORRECT NAMES)
    # Preferred for Streamlit Cloud:
    kaggle_user = None
    kaggle_key = None
    kaggle_api_token = None

    try:
        # correct secret keys: KAGGLE_USERNAME, KAGGLE_KEY, KAGGLE_API_TOKEN
        kaggle_user = st.secrets.get("KAGGLE_USERNAME")
        kaggle_key = st.secrets.get("KAGGLE_KEY")
        kaggle_api_token = st.secrets.get("KAGGLE_API_TOKEN")
    except Exception:
        kaggle_user = None
        kaggle_key = None
        kaggle_api_token = None

    # fallback to environment variables
    if not kaggle_user:
        kaggle_user = os.environ.get("KAGGLE_USERNAME")
    if not kaggle_key:
        kaggle_key = os.environ.get("KAGGLE_KEY")
    if not kaggle_api_token:
        kaggle_api_token = os.environ.get("KAGGLE_API_TOKEN")

    # show presence only (no secrets printed)
    has_user = bool(kaggle_user)
    has_key = bool(kaggle_key)
    has_token = bool(kaggle_api_token)
    st.write("Kaggle credentials found:", {"KAGGLE_USERNAME": has_user, "KAGGLE_KEY": has_key, "KAGGLE_API_TOKEN": has_token})

    # If username/key present, write kaggle.json and try package
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
            try:
                return download_with_kaggle_api_via_package(KAGGLE_DATASET, CSV_FILENAME, DATA_DIR)
            except Exception as e:
                st.warning(f"Kaggle package download failed, will try kaggle CLI as fallback: {e}")
        except Exception as e:
            st.warning(f"Could not write kaggle.json: {e}")

    # If API token present (KGAT_...), try CLI with token
    if kaggle_api_token:
        try:
            return download_with_kaggle_cli(KAGGLE_DATASET, CSV_FILENAME, DATA_DIR, kaggle_api_token=kaggle_api_token)
        except Exception as e:
            st.warning(f"kaggle CLI download with KAGGLE_API_TOKEN failed: {e}")

    # last attempt: kaggle CLI (will use ~/.kaggle if file exists)
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

# --------- Load summary excel files ----------
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

# ... (rest of your app unchanged) ...
st.success("CSV available at: " + csv_path)
