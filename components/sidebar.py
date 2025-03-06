# components/sidebar.py
import streamlit as st
import re

def extract_number(id_str):
    """Extract numeric part from a patient ID for sorting"""
    match = re.search(r'\d+', id_str)
    return int(match.group()) if match else float('inf')

def render_sidebar():
    """Render the sidebar with improved navigation and patient selection"""
    with st.sidebar:
        st.title("Tableau de Bord des Patients")
        st.markdown("---")
        
        # PATIENT SELECTION SECTION
        st.markdown("### 👥 SÉLECTION DU PATIENT")
        
        # Patient selection with better styling
        if 'final_data' in st.session_state and not st.session_state.final_data.empty:
            # Get all patient IDs
            existing_patient_ids = st.session_state.final_data['ID'].unique().tolist()
            simulated_patient_ids = []
            
            if 'simulated_ema_data' in st.session_state and not st.session_state.simulated_ema_data.empty:
                simulated_patient_ids = st.session_state.simulated_ema_data['PatientID'].unique().tolist()
                
            all_patient_ids = sorted(list(set(existing_patient_ids + simulated_patient_ids)), key=extract_number)
            
            if all_patient_ids:
                # Patient selection dropdown with helpful tooltip
                st.session_state.selected_patient_id = st.selectbox(
                    "👤 Sélectionner un Patient", 
                    all_patient_ids,
                    help="Choisissez un patient pour voir ses données détaillées",
                    key="sidebar_patient_selector"
                )
                
                # Show patient details button
                if st.button("👁️ Voir Détails Patient", type="primary", key="sidebar_view_patient"):
                    st.session_state.sidebar_selection = "Tableau de Bord du Patient"
                    st.success(f"Patient {st.session_state.selected_patient_id} sélectionné!")
                    st.rerun()
                
                # Apply filters in a collapsible section
                with st.expander("🔍 Filtres Avancés", expanded=False):
                    # Protocol filter
                    all_protocols = st.session_state.final_data['protocol'].unique().tolist()
                    protocol_filter = st.multiselect(
                        "Protocole", 
                        options=all_protocols,
                        key="sidebar_protocol_filter"
                    )
                    
                    # Age range filter
                    min_age = int(st.session_state.final_data['age'].min())
                    max_age = int(st.session_state.final_data['age'].max())
                    age_range = st.slider(
                        "Âge", 
                        min_value=min_age, 
                        max_value=max_age, 
                        value=(min_age, max_age),
                        key="sidebar_age_filter"
                    )
                    
                    # Apply filter button
                    if st.button("Appliquer les filtres", key="apply_filters"):
                        # This would normally filter the data
                        # For now, just show a success message
                        st.success("Filtres appliqués!")
                
                # Display the number of loaded patients
                st.info(f"📊 {len(all_patient_ids)} patients disponibles")
            else:
                st.warning("Aucun patient disponible.")
        
        st.markdown("---")
        
        # NAVIGATION SECTION
        st.markdown("### 📋 NAVIGATION")
        
        # Define navigation options with descriptions
        main_options = {
            "Vue d'Ensemble": "Vue générale et statistiques",
            "Tableau de Bord du Patient": "Détails et suivi du patient sélectionné",
            "Analyse des Protocoles": "Comparaison des protocoles de traitement",
            "Entrées Infirmières": "Gestion des notes et objectifs",
            "Détails PID-5": "Analyse détaillée de l'inventaire PID-5",
            "Suivi des Effets Secondaires": "Gestion des effets secondaires"
        }
        
        # Initialize navigation selection in session state
        if 'sidebar_selection' not in st.session_state:
            st.session_state.sidebar_selection = "Vue d'Ensemble"
        
        # Create radio buttons for navigation
        selected_option = st.radio(
            "Sélectionner une page:",
            options=list(main_options.keys()),
            index=list(main_options.keys()).index(st.session_state.sidebar_selection) 
                if st.session_state.sidebar_selection in main_options else 0,
            key="sidebar_navigation"
        )
        
        # Show description of selected option
        st.info(main_options[selected_option])
        
        # Update session state if selection changed
        if selected_option != st.session_state.sidebar_selection:
            st.session_state.sidebar_selection = selected_option
            st.rerun()
        
        # Help section
        with st.expander("❓ Aide", expanded=False):
            st.markdown("""
            ### Guide d'utilisation
            
            1. **Sélectionner un patient** dans la section en haut de cette barre latérale
            2. **Naviguer** entre les différentes vues en utilisant les options de navigation
            3. **Explorer** les données et ajouter des observations
            
            Pour toute question, contactez le support technique.
            """)
        
        # Session statistics
        if 'session_started' in st.session_state:
            with st.expander("⏱️ Statistiques", expanded=False):
                from datetime import datetime
                session_duration = datetime.now() - st.session_state.session_started
                hours, remainder = divmod(session_duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                st.write(f"Durée: {hours}h {minutes}m")
                st.write(f"Patients consultés: {len(st.session_state.patient_views)}")
    
    # Return the selected page based on session state
    return st.session_state.sidebar_selection