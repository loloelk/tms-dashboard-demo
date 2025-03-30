# components/nurse_inputs.py
import streamlit as st
import pandas as pd
# CORRECTED LINE: Import the renamed function get_latest_nurse_inputs
from services.nurse_service import get_latest_nurse_inputs, save_nurse_inputs, get_nurse_inputs_history

def nurse_inputs_page():
    """Page for nurse inputs and management, using database."""
    st.header("📝 Entrées Infirmières")

    if not st.session_state.get("selected_patient_id"):
        st.warning("⚠️ Aucun patient sélectionné. Veuillez en choisir un dans la barre latérale.")
        st.image("https://cdn-icons-png.flaticon.com/512/190/190684.png", width=100) # Example placeholder image
        return

    patient_id = st.session_state.selected_patient_id
    st.info(f"Patient Actuel: **{patient_id}**")

    # Load latest inputs for the form fields using the corrected function name
    latest_inputs = get_latest_nurse_inputs(patient_id) # Uses the correct function
    if latest_inputs is None:
        st.error("Erreur lors du chargement des dernières entrées infirmières.")
        latest_inputs = {"objectives": "", "tasks": "", "comments": ""} # Default empty if error


    st.subheader("➕ Ajouter une Nouvelle Entrée")
    with st.form(key='nursing_inputs_form_page'):
        col1, col2 = st.columns(2)
        with col1:
            objectives_input = st.text_area(
                "🎯 Objectifs SMART",
                height=150,
                value=latest_inputs.get("objectives", ""), # Use latest as default
                placeholder="Entrez des objectifs Spécifiques, Mesurables, Atteignables, Réalistes et Temporels"
            )
        with col2:
            tasks_input = st.text_area(
                "🏃 Tâches d'Activation Comportementale",
                height=150,
                value=latest_inputs.get("tasks", ""), # Use latest as default
                placeholder="Entrez les tâches recommandées au patient"
            )

        comments_input = st.text_area(
            "💬 Commentaires Cliniques",
            height=100,
            value=latest_inputs.get("comments", ""), # Use latest as default
            placeholder="Observations cliniques, changements notables, etc."
        )

        submit_button = st.form_submit_button(label='💾 Sauvegarder la Nouvelle Entrée')

        if submit_button:
            # Basic validation
            if not objectives_input.strip() and not tasks_input.strip() and not comments_input.strip():
                st.error("❌ Au moins un champ (Objectifs, Tâches, Commentaires) doit être rempli.")
            else:
                # Save the new entry (this adds a new row to the database)
                success = save_nurse_inputs(
                    patient_id,
                    objectives_input,
                    tasks_input,
                    comments_input
                )
                if success:
                    st.success("✅ Nouvelle entrée infirmière sauvegardée avec succès!")
                    # Clear the form fields? Optional, depends on desired UX
                    # st.experimental_rerun() # Could use rerun, or just update display below
                    st.rerun() # Rerun to update history display
                else:
                    st.error("❌ Erreur lors de la sauvegarde de la nouvelle entrée.")

    st.markdown("---")

    # Display Historical Nurse Inputs
    st.subheader("🗓️ Historique des Entrées Infirmières")
    history_df = get_nurse_inputs_history(patient_id)

    if history_df.empty:
        st.info("ℹ️ Aucune entrée infirmière trouvée pour ce patient.")
    else:
        st.info(f"Affichage des {len(history_df)} entrées précédentes (les plus récentes en premier).")
        # Format for display
        display_df = history_df[['timestamp', 'objectives', 'tasks', 'comments']].copy()
        display_df.rename(columns={
            'timestamp': 'Date/Heure',
            'objectives': 'Objectifs',
            'tasks': 'Tâches',
            'comments': 'Commentaires'
        }, inplace=True)

        # Format date/time nicely
        if 'Date/Heure' in display_df.columns:
             display_df['Date/Heure'] = display_df['Date/Heure'].dt.strftime('%Y-%m-%d %H:%M')


        # Display as a table or expanders
        # st.dataframe(display_df, use_container_width=True) # Simple table view

        # More detailed view using expanders:
        for index, row in display_df.iterrows():
            with st.expander(f"Entrée du {row['Date/Heure']}"):
                st.markdown(f"**Objectifs:**\n{row.get('Objectifs', 'N/A')}")
                st.markdown(f"**Tâches:**\n{row.get('Tâches', 'N/A')}")
                st.markdown(f"**Commentaires:**\n{row.get('Commentaires', 'N/A')}")


    # Guidance Section (remains the same)
    with st.expander("💡 Guide pour définir des objectifs SMART et Tâches"):
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