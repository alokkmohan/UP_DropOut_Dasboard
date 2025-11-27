# UP Education Department - Dropout Dashboard

## 📊 Streamlit Cloud Deployment Setup

### Step 1: Kaggle Dataset Upload
1. Upload your CSV file to Kaggle Datasets
2. Note your dataset path: `username/dataset-name`

### Step 2: Get Kaggle API Credentials
1. Go to https://www.kaggle.com/settings
2. Scroll to "API" section
3. Click "Create New API Token"
4. Download `kaggle.json` file
5. Open it to get your `username` and `key`

### Step 3: Configure Streamlit Secrets
In Streamlit Cloud dashboard:
1. Go to your app settings
2. Click on "Secrets" section
3. Add the following:

```toml
KAGGLE_USERNAME = "your-kaggle-username"
KAGGLE_KEY = "your-kaggle-api-key-here"
KAGGLE_DATASET = "your-username/your-dataset-name"
```

### Step 4: Deploy
1. Push code to GitHub
2. Connect to Streamlit Cloud
3. App will automatically download data from Kaggle on first run

## 🔒 Security Notes
- Never commit `secrets.toml` to Git
- Never share your Kaggle API key publicly
- The `.gitignore` file already excludes sensitive files

## 📦 Required Files
- `app.py` - Main dashboard code
- `requirements.txt` - Python dependencies
- `.streamlit/secrets.toml` - Your local secrets (NOT in Git)
- Excel summary files (optional, can be regenerated)

## 🚀 Local Development
1. Create `.streamlit/secrets.toml` with your credentials
2. Run: `streamlit run app.py`
3. Data will be downloaded from Kaggle automatically

## 📝 Notes
- CSV file is cached after first download
- Rerun app to refresh data from Kaggle
- Dashboard supports 11M+ records using DuckDB
