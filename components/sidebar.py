# components/sidebar.py
import streamlit as st
import re

# --- Helper Function ---
def extract_number(id_str):
    """Extract numeric part from a patient ID for sorting"""
    match = re.search(r'\d+', str(id_str))
    return int(match.group()) if match else float('inf')

# --- Role-Based Page Access ---
# Define which pages each role can access
ROLE_PERMISSIONS = {
    "admin": [
        "Vue d'Ensemble", "Tableau de Bord du Patient", "Parcours Patient",
        "Analyse des Protocoles", "Plan de Soins et Entrées Infirmières",
        "Détails PID-5", "Suivi des Effets Secondaires"
    ],
    "md": [
        "Vue d'Ensemble", "Tableau de Bord du Patient", "Parcours Patient",
        "Analyse des Protocoles", #"Plan de Soins et Entrées Infirmières", # MD might not use this directly
        "Détails PID-5", "Suivi des Effets Secondaires"
    ],
    "nurse": [
        "Vue d'Ensemble", "Tableau de Bord du Patient", "Parcours Patient",
        #"Analyse des Protocoles", # Nurse might not need this
        "Plan de Soins et Entrées Infirmières",
        #"Détails PID-5", # Nurse might not need this
        "Suivi des Effets Secondaires"
    ],
    # Default: if role not found, show only overview
    "default": ["Vue d'Ensemble"]
}

# --- Main Sidebar Rendering Function ---
def render_sidebar():
    """Render the sidebar with role-based navigation and patient selection"""
    with st.sidebar:
        st.title("🧠 Tableau de Bord TMS")

        # Retrieve user role from session state (set during login in app.py)
        user_role = st.session_state.get('role', 'default') # Default if role somehow not set

        # User info is now displayed in app.py after login check
        # st.success(f"Utilisateur: **{st.session_state.get('username', 'N/A')}** ({user_role})")

        st.markdown("---")

        # --- PATIENT SELECTION SECTION ---
        st.markdown("### 👥 Sélection Patient")
        if 'final_data' not in st.session_state or st.session_state.final_data.empty:
            st.warning("Données patient non chargées.")
            patient_list = []
            selected_index = 0
        else:
            try:
                # Get patient list (same logic as before)
                existing_patient_ids = st.session_state.final_data['ID'].unique().tolist()
                patient_list = sorted(existing_patient_ids, key=extract_number)

                # Determine selected index (same logic as before)
                current_selection = st.session_state.get('selected_patient_id', None)
                if current_selection in patient_list:
                    selected_index = patient_list.index(current_selection)
                elif patient_list:
                    selected_index = 0
                    st.session_state.selected_patient_id = patient_list[0]
                else:
                    selected_index = 0
                    st.session_state.selected_patient_id = None
            except Exception as e:
                 st.error(f"Erreur liste patients: {e}")
                 patient_list = []
                 selected_index = 0
                 st.session_state.selected_patient_id = None

        # Patient selection dropdown
        if patient_list:
            st.session_state.selected_patient_id = st.selectbox(
                "👤 Sélectionner un Patient:", patient_list, index=selected_index,
                help="Choisissez un patient pour voir ses données détaillées.",
                key="sidebar_patient_selector"
            )
            # Simple display of current patient
            st.write(f"Patient sélectionné: **{st.session_state.selected_patient_id}**")
        else:
             st.error("Aucun patient disponible.")


        st.markdown("---")

        # --- NAVIGATION SECTION (ROLE-BASED) ---
        st.markdown("### 📋 Navigation")

        # Define ALL possible navigation options and descriptions
        all_main_options = {
            "Vue d'Ensemble": "Statistiques générales de la cohorte.",
            "Tableau de Bord du Patient": "Vue détaillée du patient (évaluations, plan, etc.).",
            "Parcours Patient": "Chronologie des événements clés du patient.",
            "Analyse des Protocoles": "Comparaison de l'efficacité des protocoles TMS.",
            "Plan de Soins et Entrées Infirmières": "Ajouter/modifier le plan de soins et historique.",
            "Détails PID-5": "Analyse détaillée des scores PID-5.",
            "Suivi des Effets Secondaires": "Ajouter/voir l'historique des effets secondaires."
        }

        # Filter options based on user role
        allowed_pages = ROLE_PERMISSIONS.get(user_role, ROLE_PERMISSIONS["default"])
        available_options = {page: desc for page, desc in all_main_options.items() if page in allowed_pages}
        st.session_state.allowed_pages = list(available_options.keys()) # Store for potential use in app.py fallback

        # Get current selection, ensuring it's valid for the role
        current_page = st.session_state.get('sidebar_selection', None)
        if current_page not in available_options:
             # If previous selection not allowed, default to the first available option for the role
             current_page = list(available_options.keys())[0] if available_options else None
             st.session_state.sidebar_selection = current_page

        if not available_options:
             st.warning("Aucune page disponible pour votre rôle.")
             return None # Return None if no pages are available

        # Display radio buttons ONLY for allowed pages
        selected_option = st.radio(
            "Sélectionner une page:",
            options=list(available_options.keys()),
            index=list(available_options.keys()).index(current_page) if current_page in available_options else 0,
            key="sidebar_navigation"
        )

        # Display help text for the selected option
        st.info(f"**Page Actuelle:** {selected_option}\n\n*{available_options[selected_option]}*")

        # Update session state if selection changed and rerun
        if selected_option != st.session_state.sidebar_selection:
            st.session_state.sidebar_selection = selected_option
            st.rerun()

        st.markdown("---")
        # --- Help and Stats Sections (Unchanged) ---
        with st.expander("❓ Aide"):
             st.markdown("Naviguez entre vos vues disponibles...")

        if 'session_started' in st.session_state:
            with st.expander("⏱️ Session Info"):
                # ... (session info code remains the same) ...
                from datetime import datetime
                session_duration = datetime.now() - st.session_state.session_started
                st.write(f"Durée Session: {str(session_duration).split('.')[0]}")
                st.write(f"Consultations Patient: {len(st.session_state.get('patient_views', {}))}")

    # Return the page selected by the user (which is guaranteed to be allowed for their role)
    return st.session_state.sidebar_selection