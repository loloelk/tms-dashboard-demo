# app.py
import streamlit as st
import pandas as pd
import logging
from datetime import datetime

# Import components
from components.sidebar import render_sidebar
from components.dashboard import patient_dashboard
try:
    from components.nurse_inputs import nurse_inputs_page
except ImportError:
    from components.nurse_imputs import nurse_inputs_page # Fallback

from components.pid5_details import details_pid5_page
from components.protocol_analysis import protocol_analysis_page
from components.side_effects import side_effect_page
from components.overview import main_dashboard_page
from components.patient_journey import patient_journey_page

# Import services
from services.data_loader import load_patient_data, load_simulated_ema_data, validate_patient_data
from services.nurse_service import initialize_database

# Import utilities
from utils.logging_config import configure_logging
from utils.config_manager import load_config

# --- App Setup ---
configure_logging()
config = load_config()
st.set_page_config(
    page_title="Tableau de Bord Patients TMS",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Role Definitions and Login Check ---
# IMPORTANT: Still using hardcoded credentials for demo purposes ONLY.
VALID_CREDENTIALS = {
    "admin": {"password": "admintms", "role": "admin"},
    "MD1": {"password": "freud", "role": "md"},
    "nurse1": {"password": "nurse1", "role": "nurse"}
}

def check_login():
    """Returns `True` if the user is logged in, `False` otherwise."""
    st.session_state.setdefault('authenticated', False)
    st.session_state.setdefault('username', None)
    st.session_state.setdefault('role', None) # Add role to session state

    if st.session_state["authenticated"]:
        return True

    st.title("🔒 Connexion - Tableau de Bord TMS")
    st.write("Démonstration de connexion basée sur les rôles.")

    entered_username = st.text_input("Nom d'utilisateur")
    entered_password = st.text_input("Mot de passe", type="password")
    login_button = st.button("Se Connecter")

    if login_button:
        user_info = VALID_CREDENTIALS.get(entered_username)
        if user_info and user_info["password"] == entered_password:
            st.session_state["authenticated"] = True
            st.session_state["username"] = entered_username
            st.session_state["role"] = user_info["role"] # Store the user's role
            st.rerun()
        else:
            st.error("❌ Nom d'utilisateur ou mot de passe incorrect.")
            return False
    else:
        st.info("Comptes démo: admin / MD1 / nurse1")
        return False

# --- Main Application Logic ---
if check_login(): # Only proceed if logged in

    # Display user and role, add logout
    if st.session_state.get("username"):
         role_display = f"({st.session_state.get('role', 'N/A')})"
         st.sidebar.success(f"Utilisateur: **{st.session_state['username']}** {role_display}")
         if st.sidebar.button("Déconnexion"):
             # Clear all session state keys related to login/app state on logout
             keys_to_clear = ['authenticated', 'username', 'role', 'data_loaded',
                              'sidebar_selection', 'selected_patient_id',
                              'first_visit_after_login'] # Add others if needed
             for key in keys_to_clear:
                 if key in st.session_state:
                     del st.session_state[key]
             st.rerun()

    # --- Initialize Database ---
    @st.cache_resource
    def run_db_initialization():
        logging.info("Running database initialization check...")
        initialize_database()
        logging.info("Database initialization check complete.")
    run_db_initialization()

    # --- Load CSS ---
    try:
        with open('assets/styles.css') as f: st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        logging.info("CSS styles loaded.")
    except FileNotFoundError: logging.warning("assets/styles.css not found.")

    # --- Session State Initialization (App specific) ---
    st.session_state.setdefault('first_visit_after_login', True)
    st.session_state.setdefault('selected_patient_id', None)
    # Default sidebar selection will be determined by role in sidebar.py now
    # st.session_state.setdefault('sidebar_selection', "Vue d'Ensemble")
    if 'session_started' not in st.session_state:
         st.session_state.session_started = datetime.now()
         st.session_state.patient_views = {}

    # --- Welcome Message ---
    if st.session_state.first_visit_after_login:
        # Welcome message adjusted slightly
        st.info(f"""
        ### Bienvenue au Tableau de Bord TMS, {st.session_state.get('username', 'Utilisateur')}! ({st.session_state.get('role', '').upper()})
        1.  Sélectionnez un patient dans la barre latérale.
        2.  Naviguez entre vos vues disponibles.
        3.  Explorez les données et ajoutez des observations si applicable.
        Cliquez sur 'Fermer' pour masquer ce message.
        """)
        if st.button("Fermer Accueil"):
            st.session_state.first_visit_after_login = False
            st.rerun()

    # --- Load Main Data ---
    PATIENT_DATA_CSV = config['paths']['patient_data_with_protocol']
    SIMULATED_EMA_CSV = config['paths']['simulated_ema_data']
    st.session_state.setdefault('data_loaded', False)

    if not st.session_state.data_loaded:
        try:
            # ... (data loading logic remains the same) ...
            final_data = load_patient_data(PATIENT_DATA_CSV)
            simulated_ema_data = load_simulated_ema_data(SIMULATED_EMA_CSV)
            if final_data.empty: st.error("❌ Données patient non chargées..."); st.stop()
            validate_patient_data(final_data)
            st.session_state.final_data = final_data
            st.session_state.simulated_ema_data = simulated_ema_data
            st.session_state.data_loaded = True
            logging.info("Data loaded successfully.")
            # Set default patient ID after data load if not set
            if 'ID' in final_data.columns and st.session_state.get('selected_patient_id') is None:
                 st.session_state.selected_patient_id = final_data['ID'].iloc[0]
                 logging.info(f"Default patient set: {st.session_state.selected_patient_id}")

        # ... (error handling for data loading remains the same) ...
        except FileNotFoundError as e: st.error(f"❌ Fichier non trouvé: {e}..."); st.stop()
        except ValueError as e: st.error(f"❌ Erreur validation données: {e}"); st.stop()
        except Exception as e: st.error(f"❌ Erreur chargement données: {e}"); logging.exception("Data load error."); st.stop()

    # Ensure data is loaded before proceeding
    if not st.session_state.data_loaded or 'final_data' not in st.session_state:
         st.error("Erreur critique: Données non disponibles.")
         st.stop()


    # --- Define Constants and Mappings ---
    st.session_state.setdefault('MADRS_ITEMS_MAPPING', config['mappings']['madrs_items'])
    st.session_state.setdefault('PID5_DIMENSIONS_MAPPING', config['mappings']['pid5_dimensions'])
    st.session_state.setdefault('PASTEL_COLORS', ["#FFB6C1", "#FFD700", "#98FB98", "#87CEFA", "#DDA0DD", "#E6E6FA"])
    st.session_state.MADRS_ITEMS = [f'madrs_{i}' for i in range(1, 11)]
    st.session_state.ANXIETY_ITEMS = [f'anxiety_{i}' for i in range(1, 6)]
    st.session_state.SLEEP = 'sleep'; st.session_state.ENERGY = 'energy'; st.session_state.STRESS = 'stress'
    st.session_state.SYMPTOMS = st.session_state.MADRS_ITEMS + st.session_state.ANXIETY_ITEMS + \
                                 [st.session_state.SLEEP, st.session_state.ENERGY, st.session_state.STRESS]

    # --- Render Sidebar and Main Content ---
    # Sidebar rendering now depends on role (handled within render_sidebar)
    page_selected = render_sidebar() # This function will filter options based on role

    # Update patient view count
    if page_selected == "Tableau de Bord du Patient" and st.session_state.selected_patient_id:
         current_patient = st.session_state.selected_patient_id
         if 'patient_views' not in st.session_state: st.session_state.patient_views = {}
         st.session_state.patient_views[current_patient] = st.session_state.patient_views.get(current_patient, 0) + 1

    # --- Page Routing ---
    logging.info(f"Routing to page: {page_selected}")

    # Define which pages require a patient ID (remains the same)
    needs_patient = [
        "Tableau de Bord du Patient", "Parcours Patient", "Détails PID-5",
        "Suivi des Effets Secondaires", "Plan de Soins et Entrées Infirmières"
    ]

    # Check patient selection requirement (remains the same)
    if page_selected in needs_patient and not st.session_state.selected_patient_id:
        st.warning(f"⚠️ Veuillez sélectionner un patient pour voir '{page_selected}'.")
        # Redirect to overview if patient needed but not selected
        # Check if overview is allowed for the role first (handled in sidebar filtering)
        if "Vue d'Ensemble" in st.session_state.get('allowed_pages',[]): # allowed_pages set in sidebar
             main_dashboard_page()
        else:
             st.error("Aucune page par défaut disponible pour votre rôle.")

    else:
        # Route to the selected page function (make sure it's allowed for the role)
        # The filtering happens in the sidebar, so page_selected *should* be allowed.
        if page_selected == "Vue d'Ensemble": main_dashboard_page()
        elif page_selected == "Tableau de Bord du Patient": patient_dashboard()
        elif page_selected == "Parcours Patient": patient_journey_page()
        elif page_selected == "Analyse des Protocoles": protocol_analysis_page()
        elif page_selected == "Plan de Soins et Entrées Infirmières": nurse_inputs_page()
        elif page_selected == "Détails PID-5": details_pid5_page()
        elif page_selected == "Suivi des Effets Secondaires": side_effect_page()
        else:
            st.error(f"Page non reconnue ou non autorisée: '{page_selected}'.")
            logging.error(f"Routing failed for page: {page_selected}")
            # Attempt to show overview if allowed, else error
            if "Vue d'Ensemble" in st.session_state.get('allowed_pages',[]):
                 main_dashboard_page()
            else:
                 st.error("Erreur de routage.")