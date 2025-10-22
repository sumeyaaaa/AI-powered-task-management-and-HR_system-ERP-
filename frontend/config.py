# frontend/config.py
import os
import streamlit as st

# Check if running in Streamlit Cloud
def is_streamlit_cloud():
    return "HOSTNAME" in os.environ and "render.com" not in os.environ.get("HOSTNAME", "")

class Config:
    if is_streamlit_cloud():
        # Use Streamlit Secrets (deployed)
        BACKEND_URL = st.secrets.get("BACKEND_URL")
        SUPERADMIN_EMAIL = st.secrets.get("SUPERADMIN_EMAIL")
        SUPERADMIN_PASSWORD = st.secrets.get("SUPERADMIN_PASSWORD")
    else:
        # Use .env (local development)
        from dotenv import load_dotenv
        load_dotenv()
        BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
        SUPERADMIN_EMAIL = os.getenv('SUPERADMIN_EMAIL')
        SUPERADMIN_PASSWORD = os.getenv('SUPERADMIN_PASSWORD')

config = Config()