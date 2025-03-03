# app.py
import streamlit as st
import pandas as pd
import logging
from datetime import datetime

# Import components
from components.sidebar import render_sidebar
from components.dashboard import patient_dashboard
from components.nurse_inputs import nurse_inputs_page
from components.pid5_details import details_pid5_page
from components.protocol_analysis import protocol_analysis_page
from components.side_effects import side_effect_page
from components.overview import main_dashboard_page

# Import services
from services.data_loader import load_patient_data, load_simulated_ema_data, validate_patient_data
from services.nurse_service import load_nurse_data

# Import utilities
from utils.logging_config import configure_logging
from utils.config_manager import load_config

# Configure logging
configure_logging()

# Load configuration
config = load_config()

# Set page configuration
st.set_page_config(
    page_title="Tableau de Bord des Patients",
    page_icon=":hospital:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load CSS
with open('assets/styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize session state
if 'selected_patient_id' not in st.session_state:
    st.session_state.selected_patient_id = None

if 'session_started' not in st.session_state:
    st.session_state.session_started = datetime.now()
    st.session_state.patient_views = {}

# Define constants from config
PATIENT_DATA_CSV = config['paths']['patient_data_with_protocol']
NURSE_INPUTS_CSV = config['paths']['nurse_inputs']
SIMULATED_EMA_CSV = config['paths']['simulated_ema_data']

# Load data
try:
    # Load patient data
    final_data = load_patient_data(PATIENT_DATA_CSV)
    # Load simulated EMA data
    simulated_ema_data = load_simulated_ema_data(SIMULATED_EMA_CSV)
    
    if final_data.empty:
        st.error("Aucune donnée patient chargée. Veuillez vérifier le fichier CSV.")
        st.stop()
    
    validate_patient_data(final_data)
    
    # Store in session state for access by components
    st.session_state.final_data = final_data
    st.session_state.simulated_ema_data = simulated_ema_data
    st.session_state.NURSE_INPUTS_CSV = NURSE_INPUTS_CSV
    
except Exception as e:
    st.error(f"Erreur lors du chargement des données: {e}")
    st.stop()

# Load nurse data
if 'nurse_data' not in st.session_state:
    st.session_state.nurse_data = load_nurse_data(NURSE_INPUTS_CSV)

# Define symptoms (needed by multiple components)
MADRS_ITEMS = [f'madrs_{i}' for i in range(1, 11)]
ANXIETY_ITEMS = [f'anxiety_{i}' for i in range(1, 6)]
SLEEP = 'sleep'
ENERGY = 'energy'
STRESS = 'stress'
SYMPTOMS = MADRS_ITEMS + ANXIETY_ITEMS + [SLEEP, ENERGY, STRESS]

# Store in session state
st.session_state.MADRS_ITEMS = MADRS_ITEMS
st.session_state.ANXIETY_ITEMS = ANXIETY_ITEMS
st.session_state.SLEEP = SLEEP
st.session_state.ENERGY = ENERGY
st.session_state.STRESS = STRESS
st.session_state.SYMPTOMS = SYMPTOMS
# Add pastel colors to session state
st.session_state.PASTEL_COLORS = ["#FFB6C1", "#FFD700", "#98FB98", "#87CEFA", "#DDA0DD"]
# Load mappings from config into session state
st.session_state.MADRS_ITEMS_MAPPING = config['mappings']['madrs_items']
st.session_state.PID5_DIMENSIONS_MAPPING = config['mappings']['pid5_dimensions']

# Render sidebar
page = render_sidebar()

# In app.py, update the main application logic:

# Main application logic - render the selected page
if page == "Vue d'Ensemble":
    main_dashboard_page()
elif page == "Analyse des Protocoles":
    protocol_analysis_page()
elif page == "Tableau de Bord du Patient":
    patient_dashboard()
elif page == "Entrées Infirmières":
    nurse_inputs_page()
elif page == "Détails PID-5":
    details_pid5_page()
elif page == "Suivi des Effets Secondaires":
    side_effect_page()
else:
    st.error("Page non reconnue.")
# Track patient views
if st.session_state.selected_patient_id:
    if st.session_state.selected_patient_id not in st.session_state.patient_views:
        st.session_state.patient_views[st.session_state.selected_patient_id] = 1
    else:
        st.session_state.patient_views[st.session_state.selected_patient_id] += 1