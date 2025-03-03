# components/nurse_inputs.py
import streamlit as st
from services.nurse_service import get_nurse_inputs, save_nurse_inputs, load_nurse_data

def nurse_inputs_page():
    """Page for nurse inputs and management"""
    if not st.session_state.get("selected_patient_id"):
        st.warning("Aucun patient sélectionné.")
        return

    st.header("Entrées Infirmières")
    nurse_inputs = get_nurse_inputs(st.session_state.selected_patient_id, st.session_state.nurse_data)
    
    with st.form(key='nursing_inputs_form_page'):
        col1, col2 = st.columns(2)
        with col1:
            objectives_input = st.text_area(
                "Objectifs SMART", 
                height=150, 
                value=nurse_inputs.get("objectives", ""),
                placeholder="Entrez des objectifs Spécifiques, Mesurables, Atteignables, Réalistes et Temporels"
            )
        with col2:
            tasks_input = st.text_area(
                "Tâches d'Activation Comportementale", 
                height=150, 
                value=nurse_inputs.get("tasks", ""),
                placeholder="Entrez les tâches recommandées au patient"
            )
        
        comments_input = st.text_area(
            "Commentaires", 
            height=100, 
            value=nurse_inputs.get("comments", ""),
            placeholder="Observations cliniques, changements notables, etc."
        )
        
        submit_button = st.form_submit_button(label='Sauvegarder')
        
        if submit_button:
            # Validate inputs
            errors = validate_nurse_inputs(objectives_input, tasks_input, comments_input)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                try:
                    st.session_state.nurse_data = save_nurse_inputs(
                        st.session_state.selected_patient_id, 
                        objectives_input, 
                        tasks_input, 
                        comments_input, 
                        st.session_state.nurse_data, 
                        st.session_state.NURSE_INPUTS_CSV
                    )
                    st.success("Entrées infirmières sauvegardées avec succès.")
                except Exception as e:
                    st.error(f"Erreur lors de la sauvegarde des entrées infirmières: {e}")

    st.markdown("---")

    # Display Saved Nurse Inputs
    st.subheader("Entrées Infirmières Sauvegardées")
    if nurse_inputs:
        st.info(f"**Objectifs :** {nurse_inputs.get('objectives', 'N/A')}")
        st.success(f"**Tâches :** {nurse_inputs.get('tasks', 'N/A')}")
        st.write(f"**Commentaires :** {nurse_inputs.get('comments', 'N/A')}")
    else:
        st.write("Aucune entrée sauvegardée.")
        
    # Guidance for writing good objectives
    with st.expander("Guide pour définir des objectifs SMART"):
        st.markdown("""
        ### Objectifs SMART

        Un objectif SMART est:
        
        - **Spécifique**: Précis, clair et bien défini
        - **Mesurable**: Quantifiable pour suivre les progrès
        - **Atteignable**: Réaliste et réalisable pour le patient
        - **Réaliste**: En lien avec la condition et les capacités du patient
        - **Temporel**: Avec une échéance précise
        
        **Exemple**: "Augmenter progressivement les activités physiques pour atteindre 30 minutes de marche quotidienne d'ici deux semaines"
        
        ### Tâches d'Activation Comportementale
        
        Les tâches devraient:
        - Être simples et bien définies
        - Commencer petit et augmenter progressivement
        - Être alignées avec les intérêts du patient
        - Générer un sentiment d'accomplissement
        
        **Exemple**: "Jour 1-3: Marcher 10 minutes après le petit-déjeuner; Jour 4-7: Augmenter à 15 minutes..."
        """)

def validate_nurse_inputs(objectives, tasks, comments):
    """Validate nurse inputs"""
    errors = []
    
    if not objectives.strip() and not tasks.strip() and not comments.strip():
        errors.append("Au moins un des champs doit être rempli")
        
    if len(objectives) > 1000:
        errors.append("Les objectifs ne peuvent pas dépasser 1000 caractères")
        
    if len(tasks) > 1000:
        errors.append("Les tâches ne peuvent pas dépasser 1000 caractères")
    
    return errors