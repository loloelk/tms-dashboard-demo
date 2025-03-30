# app.py
import streamlit as st
import pandas as pd
import logging
from datetime import datetime
import os # Need os for path joining

# Import components
from components.sidebar import render_sidebar
from components.dashboard import patient_dashboard
try:
    from components.nurse_inputs import nurse_inputs_page
except ImportError:
    logging.warning("Could not import nurse_inputs_page from components.nurse_inputs, trying fallback.")
    try:
        from components.nurse_imputs import nurse_inputs_page # Original fallback
    except ImportError:
        logging.error("Failed to import nurse_inputs_page from both components.nurse_inputs and components.nurse_imputs")
        # Define a dummy page or raise a more critical error if it's essential
        def nurse_inputs_page():
            st.error("Composant de la page des entrées infirmières non trouvé.")


# --- BFI MODIFICATION START: Remove PID-5 import ---
# from components.pid5_details import details_pid5_page # REMOVED
# --- BFI MODIFICATION END ---
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
VALID_CREDENTIALS = {
    "admin": {"password": "admintms", "role": "admin"},
    "MD1": {"password": "freud", "role": "md"},
    "nurse1": {"password": "nurse1", "role": "nurse"}
}

def check_login():
    """Returns `True` if the user is logged in, `False` otherwise."""
    st.session_state.setdefault('authenticated', False)
    st.session_state.setdefault('username', None)
    st.session_state.setdefault('role', None)

    if st.session_state["authenticated"]:
        return True

    st.title("🔒 Connexion - Tableau de Bord TMS") #
    st.write("Démonstration de connexion basée sur les rôles.")

    entered_username = st.text_input("Nom d'utilisateur")
    entered_password = st.text_input("Mot de passe", type="password")
    login_button = st.button("Se Connecter")

    if login_button:
        user_info = VALID_CREDENTIALS.get(entered_username)
        if user_info and user_info["password"] == entered_password:
            st.session_state["authenticated"] = True #
            st.session_state["username"] = entered_username
            st.session_state["role"] = user_info["role"]
            st.rerun()
        else:
            st.error("❌ Nom d'utilisateur ou mot de passe incorrect.")
            return False
    else:
        st.info("Comptes démo: admin / MD1 / nurse1") #
        return False # Not authenticated yet

# --- Main Application Logic ---
if check_login():

    # Display logged-in user in the sidebar
    if st.session_state.get("username"):
         role_display = f"({st.session_state.get('role', 'N/A')})"
         st.sidebar.success(f"Utilisateur: **{st.session_state['username']}** {role_display}")
         # Simple logout button
         if st.sidebar.button("Déconnexion"):
             keys_to_clear = ['authenticated', 'username', 'role', 'data_loaded', #
                              'sidebar_selection', 'selected_patient_id',
                              'first_visit_after_login'] # Add others if needed
             for key in keys_to_clear:
                 if key in st.session_state: #
                     del st.session_state[key]
             st.rerun()


    # --- Initialize Database (only if logged in) ---
    @st.cache_resource
    def run_db_initialization():
        logging.info("Running database initialization check...")
        initialize_database()
        logging.info("Database initialization check complete.") #
    run_db_initialization()

    # --- Load CSS (only if logged in) ---
    try:
        css_path = os.path.join('assets', 'styles.css')
        if os.path.exists(css_path):
            with open(css_path) as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
            logging.info("CSS styles loaded.") #
        else:
             logging.warning(f"{css_path} not found. Skipping CSS loading.") #

    except Exception as e:
        logging.error(f"Error loading CSS: {e}")


    # --- Session State Initialization (App specific, after login) ---
    st.session_state.setdefault('first_visit_after_login', True)
    st.session_state.setdefault('selected_patient_id', None)
    # Default sidebar selection will be determined by role in sidebar.py now #
    # st.session_state.setdefault('sidebar_selection', "Vue d'Ensemble")
    if 'session_started' not in st.session_state:
         st.session_state.session_started = datetime.now()
         st.session_state.patient_views = {} # Initialize patient view counter


    # --- Welcome Message (Show only once after successful login) ---
    if st.session_state.first_visit_after_login:
        st.info(f"""
        ### Bienvenue au Tableau de Bord TMS, {st.session_state.get('username', 'Utilisateur')}! ({st.session_state.get('role', '').upper()})
        1.  Sélectionnez un patient dans la barre latérale.
        2.  Naviguez entre vos vues disponibles.
        3.  Explorez les données et ajoutez des observations si applicable.
        Cliquez sur 'Fermer' pour masquer ce message.
        """) #
        if st.button("Fermer Accueil"):
            st.session_state.first_visit_after_login = False
            st.rerun()

    # --- Load Main Data (Only if logged in) ---
    # Use paths from loaded config
    PATIENT_DATA_CSV = config.get('paths', {}).get('patient_data_with_protocol', 'data/patient_data_with_protocol_simulated.csv')
    SIMULATED_EMA_CSV = config.get('paths', {}).get('simulated_ema_data', 'data/simulated_ema_data.csv')


    st.session_state.setdefault('data_loaded', False) #
    if not st.session_state.data_loaded:
        try:
            final_data = load_patient_data(PATIENT_DATA_CSV)
            simulated_ema_data = load_simulated_ema_data(SIMULATED_EMA_CSV)
            if final_data.empty:
                st.error("❌ Aucune donnée patient principale chargée...")
                st.stop()
            validate_patient_data(final_data) # Validate the loaded data #
            st.session_state.final_data = final_data
            st.session_state.simulated_ema_data = simulated_ema_data
            st.session_state.data_loaded = True # Mark data as loaded
            logging.info("Data loaded successfully.")

            # Set default patient ID after data load if not set
            if 'ID' in final_data.columns and not final_data.empty and st.session_state.get('selected_patient_id') is None: #
                 st.session_state.selected_patient_id = final_data['ID'].iloc[0]
                 logging.info(f"Default patient set: {st.session_state.selected_patient_id}")

        except FileNotFoundError as e:
             st.error(f"❌ Erreur: Fichier de données non trouvé - {e}...")
             st.stop() #
        except ValueError as e: # Catch validation errors
             st.error(f"❌ Erreur de validation des données patient: {e}")
             st.stop()
        except Exception as e:
            st.error(f"❌ Erreur inattendue lors du chargement des données: {e}")
            logging.exception("Data load error.")
            st.stop() #
    # Ensure data is available before proceeding
    elif 'final_data' not in st.session_state or 'simulated_ema_data' not in st.session_state:
         st.error("Erreur critique: Données non chargées en session.")
         st.stop()


    # --- Define Constants and Mappings (Only if logged in & data loaded) ---
    # Load mappings from config, provide defaults
    st.session_state.setdefault('MADRS_ITEMS_MAPPING', config.get('mappings', {}).get('madrs_items', {}))
    # --- BFI MODIFICATION START: Remove PID-5 mapping setup ---
    # st.session_state.setdefault('PID5_DIMENSIONS_MAPPING', config.get('mappings', {}).get('pid5_dimensions', {})) # REMOVED
    # --- BFI MODIFICATION END ---
    st.session_state.setdefault('PASTEL_COLORS', ["#FFB6C1", "#FFD700", "#98FB98", "#87CEFA", "#DDA0DD", "#E6E6FA"])

    # Define symptom lists dynamically if needed, or keep fixed if structure is stable
    st.session_state.setdefault('MADRS_ITEMS', [f'madrs_{i}' for i in range(1, 11)]) #
    st.session_state.setdefault('ANXIETY_ITEMS', [f'anxiety_{i}' for i in range(1, 6)])
    st.session_state.setdefault('SLEEP', 'sleep')
    st.session_state.setdefault('ENERGY', 'energy')
    st.session_state.setdefault('STRESS', 'stress')
    # Combine symptom lists
    st.session_state['SYMPTOMS'] = st.session_state.MADRS_ITEMS + st.session_state.ANXIETY_ITEMS + \
                                   [st.session_state.SLEEP, st.session_state.ENERGY, st.session_state.STRESS]


    # --- Render Sidebar and Main Content (Only if logged in & data loaded) ---
    page_selected = render_sidebar() # Sidebar determines allowed pages based on role

    # Update patient view count (if tracking is desired)
    if page_selected == "Tableau de Bord du Patient" and st.session_state.selected_patient_id: #
         current_patient = st.session_state.selected_patient_id
         if 'patient_views' not in st.session_state: st.session_state.patient_views = {}
         st.session_state.patient_views[current_patient] = st.session_state.patient_views.get(current_patient, 0) + 1

    # --- Page Routing (Only if logged in & data loaded) ---
    logging.info(f"Routing to page: {page_selected}")

    # --- BFI MODIFICATION START: Remove "Détails PID-5" from needs_patient ---
    needs_patient = [
        "Tableau de Bord du Patient", "Parcours Patient", #"Détails PID-5", REMOVED
        "Suivi des Effets Secondaires", "Plan de Soins et Entrées Infirmières"
    ]
    # --- BFI MODIFICATION END ---

    # Check if a page was actually selected
    if page_selected is None:
        st.error("Aucune page disponible pour votre rôle.")
    # Check patient selection requirement
    elif page_selected in needs_patient and not st.session_state.selected_patient_id: #
        st.warning(f"⚠️ Veuillez sélectionner un patient pour voir '{page_selected}'.")
        # Redirect to overview if allowed
        if "Vue d'Ensemble" in st.session_state.get('allowed_pages',[]):
             main_dashboard_page()
        else:
             st.error("Aucune page par défaut disponible pour votre rôle.") #

    else:
        # Route to the selected page function
        # --- BFI MODIFICATION START: Remove PID-5 routing ---
        if page_selected == "Vue d'Ensemble": main_dashboard_page() #
        elif page_selected == "Tableau de Bord du Patient": patient_dashboard()
        elif page_selected == "Parcours Patient": patient_journey_page()
        elif page_selected == "Analyse des Protocoles": protocol_analysis_page()
        elif page_selected == "Plan de Soins et Entrées Infirmières": nurse_inputs_page()
        # elif page_selected == "Détails PID-5": details_pid5_page() # REMOVED
        elif page_selected == "Suivi des Effets Secondaires": side_effect_page()
        # --- BFI MODIFICATION END ---
        else:
            st.error(f"Page non reconnue ou non autorisée: '{page_selected}'.") #
            logging.error(f"Routing failed for page: {page_selected}")
            # Attempt to show overview if allowed, else error
            if "Vue d'Ensemble" in st.session_state.get('allowed_pages',[]):
                 main_dashboard_page()
            else: #
                 st.error("Erreur de routage.")

# If check_login() returns False, the script stops here, showing only the login form.