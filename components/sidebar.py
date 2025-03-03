# components/sidebar.py (revised)
import streamlit as st
import re

def extract_number(id_str):
    """Extract numeric part from a patient ID for sorting"""
    match = re.search(r'\d+', id_str)
    return int(match.group()) if match else float('inf')

def render_sidebar():
    """Render the sidebar with hierarchical navigation"""
    with st.sidebar:
        st.title("Tableau de Bord des Patients")
        st.markdown("---")
        
        # Main navigation tabs
        st.header("Navigation")
        main_tab = st.radio("Vue principale", [
            "Vue d'Ensemble",
            "Tableau de Bord du Patient"
        ])
        
        # Sub-tabs based on main selection
        if main_tab == "Vue d'Ensemble":
            st.subheader("Sections d'analyse globale")
            overview_subtab = st.radio("Sélectionner", [
                "Résumé Général",
                "Analyse des Protocoles"
            ])
            
            # Determine the page based on subtab
            if overview_subtab == "Résumé Général":
                page = "Vue d'Ensemble"
            else:
                page = "Analyse des Protocoles"
                
        else:  # Tableau de Bord du Patient
            st.subheader("Sections patient")
            patient_subtab = st.radio("Sélectionner", [
                "Aperçu Patient",
                "Entrées Infirmières",
                "Détails PID-5",
                "Suivi des Effets Secondaires"
            ])
            
            # Determine the page based on subtab
            if patient_subtab == "Aperçu Patient":
                page = "Tableau de Bord du Patient"
            elif patient_subtab == "Entrées Infirmières":
                page = "Entrées Infirmières"
            elif patient_subtab == "Détails PID-5":
                page = "Détails PID-5"
            else:
                page = "Suivi des Effets Secondaires"

        st.markdown("---")
        st.header("Sélectionner un Patient")
        
        # Patient selection - This remains mostly unchanged
        if 'final_data' in st.session_state and not st.session_state.final_data.empty:
            # Filter options
            st.subheader("Filtres")
            
            # Protocol filter
            all_protocols = st.session_state.final_data['protocol'].unique().tolist()
            protocol_filter = st.multiselect("Protocole", options=all_protocols)
            
            # Age range filter
            min_age = int(st.session_state.final_data['age'].min())
            max_age = int(st.session_state.final_data['age'].max())
            age_range = st.slider("Âge", min_value=min_age, max_value=max_age, value=(min_age, max_age))
            
            # Apply filters
            filtered_data = st.session_state.final_data.copy()
            
            if protocol_filter:
                filtered_data = filtered_data[filtered_data['protocol'].isin(protocol_filter)]
            
            filtered_data = filtered_data[
                (filtered_data['age'] >= age_range[0]) & 
                (filtered_data['age'] <= age_range[1])
            ]
            
            # Combine existing and simulated patient IDs
            existing_patient_ids = filtered_data['ID'].unique().tolist()
            simulated_patient_ids = []
            
            if 'simulated_ema_data' in st.session_state and not st.session_state.simulated_ema_data.empty:
                simulated_patient_ids = st.session_state.simulated_ema_data['PatientID'].unique().tolist()
                
            all_patient_ids = sorted(list(set(existing_patient_ids + simulated_patient_ids)), key=extract_number)
            
            if all_patient_ids:
                st.session_state.selected_patient_id = st.selectbox(
                    "Sélectionner l'ID du Patient", 
                    all_patient_ids
                )
                
                # Display the number of loaded patients
                st.write(f"Nombre de patients chargés : {len(all_patient_ids)}")
            else:
                st.warning("Aucun patient ne correspond aux critères de filtrage.")

        # Help section
        with st.expander("Aide"):
            st.markdown("""
            **Comment utiliser ce tableau de bord:**
            
            1. Sélectionnez une vue principale dans le menu de navigation
            2. Choisissez une section spécifique dans le sous-menu
            3. Pour analyser un patient spécifique, sélectionnez-le dans la liste
            4. Utilisez les filtres pour affiner la liste des patients
            
            Pour obtenir de l'aide supplémentaire, contactez le support technique.
            """)
            
        # Session statistics (unchanged)
        if 'session_started' in st.session_state:
            with st.expander("Statistiques de Session"):
                from datetime import datetime
                session_duration = datetime.now() - st.session_state.session_started
                hours, remainder = divmod(session_duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                st.write(f"Durée de session: {hours}h {minutes}m")
                st.write(f"Patients consultés: {len(st.session_state.patient_views)}")
    
    return page