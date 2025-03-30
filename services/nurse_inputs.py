# components/nurse_inputs.py
import streamlit as st
import pandas as pd
# Import the specific functions needed from nurse_service
from services.nurse_service import get_latest_nurse_inputs, save_nurse_inputs, get_nurse_inputs_history

# Define goal status options
GOAL_STATUS_OPTIONS = ["Not Set", "Not Started", "In Progress", "Achieved", "On Hold", "Revised"]

def nurse_inputs_page():
    """Page for nurse inputs and management, including treatment planning."""
    st.header("📝 Plan de Soins et Entrées Infirmières")

    if not st.session_state.get("selected_patient_id"):
        st.warning("⚠️ Aucun patient sélectionné. Veuillez en choisir un dans la barre latérale.")
        # Optional: Add a placeholder image or instruction
        # st.image("path/to/placeholder.png", width=100)
        return

    patient_id = st.session_state.selected_patient_id
    st.info(f"Patient Actuel: **{patient_id}**")

    # Load latest inputs for the form fields
    latest_inputs = get_latest_nurse_inputs(patient_id)
    if latest_inputs is None:
        st.error("Erreur lors du chargement des dernières entrées infirmières.")
        # Provide default structure if loading failed
        latest_inputs = {
            "objectives": "", "tasks": "", "comments": "",
            "target_symptoms": "", "planned_interventions": "", "goal_status": "Not Set"
        }

    # --- Form for Adding New Entry ---
    st.subheader("➕ Ajouter/Modifier le Plan de Soins Actuel")
    st.caption("Sauvegarder créera une nouvelle entrée historique avec ces informations.")

    with st.form(key='nursing_inputs_form_page'):
        st.markdown("**Objectifs & Tâches**")
        col_obj, col_task = st.columns(2)
        with col_obj:
            objectives_input = st.text_area(
                "🎯 Objectifs SMART", height=150,
                value=latest_inputs.get("objectives", ""),
                placeholder="Objectifs Spécifiques, Mesurables, Atteignables, Réalistes, Temporels..."
            )
        with col_task:
            tasks_input = st.text_area(
                "🏃 Tâches d'Activation Comportementale", height=150,
                value=latest_inputs.get("tasks", ""),
                placeholder="Tâches spécifiques pour le patient..."
            )

        st.markdown("**Planification & Suivi**")
        col_symp, col_int, col_stat = st.columns([2, 2, 1])
        with col_symp:
            target_symptoms_input = st.text_input(
                "📉 Symptômes Cibles",
                value=latest_inputs.get("target_symptoms", ""),
                placeholder="Ex: Insomnie, Anhédonie, MADRS-9"
            )
        with col_int:
            planned_interventions_input = st.text_input(
                "🛠️ Interventions Planifiées",
                value=latest_inputs.get("planned_interventions", ""),
                placeholder="Ex: Ajustement protocole, Thérapie comportementale"
            )
        with col_stat:
            # Find index of current status for default selection
            current_status = latest_inputs.get("goal_status", "Not Set")
            # Handle case where status might not be in options (e.g., data corruption)
            try:
                status_index = GOAL_STATUS_OPTIONS.index(current_status)
            except ValueError:
                status_index = 0 # Default to "Not Set" if current status is invalid

            goal_status_input = st.selectbox(
                "📊 Statut Objectif",
                options=GOAL_STATUS_OPTIONS,
                index=status_index, # Set default based on latest entry
                help="Statut actuel des objectifs définis ci-dessus."
            )

        st.markdown("**Commentaires Généraux**")
        comments_input = st.text_area(
            "💬 Commentaires Cliniques", height=100,
            value=latest_inputs.get("comments", ""),
            placeholder="Observations générales, contexte, etc."
        )

        submit_button = st.form_submit_button(label='💾 Sauvegarder la Nouvelle Entrée')

        if submit_button:
            # Basic validation: check if at least one planning field or comment is filled
            if not objectives_input.strip() and not tasks_input.strip() and \
               not target_symptoms_input.strip() and not planned_interventions_input.strip() and \
               not comments_input.strip() and goal_status_input == "Not Set":
                st.error("❌ Veuillez remplir au moins un champ ou définir un statut pour sauvegarder.")
            else:
                # Save the new entry with all fields
                # Ensure all arguments expected by the function are passed
                success = save_nurse_inputs(
                    patient_id=patient_id,
                    objectives=objectives_input,
                    tasks=tasks_input,
                    comments=comments_input,
                    target_symptoms=target_symptoms_input,
                    planned_interventions=planned_interventions_input,
                    goal_status=goal_status_input
                    # created_by could be added here, e.g., created_by=st.session_state.get('username', 'Clinician')
                )
                if success:
                    st.success("✅ Nouvelle entrée de plan de soins sauvegardée avec succès!")
                    st.rerun() # Rerun to update history display and clear form implicitly
                else:
                    st.error("❌ Erreur lors de la sauvegarde.")

    st.markdown("---")

    # --- Display Historical Entries ---
    st.subheader("🗓️ Historique des Plans de Soins")
    history_df = get_nurse_inputs_history(patient_id)

    if history_df.empty:
        st.info("ℹ️ Aucun historique trouvé pour ce patient.")
    else:
        st.info(f"Affichage des {len(history_df)} entrées précédentes (les plus récentes en premier).")

        # Define columns to display
        display_columns = [
            'timestamp', 'goal_status', 'objectives', 'tasks',
            'target_symptoms', 'planned_interventions', 'comments', 'created_by' # Add new columns + optional created_by
        ]
        # Filter dataframe to only include columns that actually exist in the history
        display_columns = [col for col in display_columns if col in history_df.columns]
        display_df = history_df[display_columns].copy()

        # Rename columns for better readability
        rename_map = {
            'timestamp': 'Date/Heure', 'goal_status': 'Statut', 'objectives': 'Objectifs',
            'tasks': 'Tâches', 'target_symptoms': 'Symptômes Cibles',
            'planned_interventions': 'Interventions', 'comments': 'Commentaires',
            'created_by': 'Auteur'
        }
        display_df.rename(columns=rename_map, inplace=True)


        # Format date/time
        if 'Date/Heure' in display_df.columns:
             # Ensure it's datetime before formatting
             display_df['Date/Heure'] = pd.to_datetime(display_df['Date/Heure'])
             display_df['Date/Heure'] = display_df['Date/Heure'].dt.strftime('%Y-%m-%d %H:%M')

        # Display using expanders for detail
        for index, row in display_df.iterrows():
            expander_title = f"Plan du {row.get('Date/Heure', 'N/A')} (Statut: {row.get('Statut', 'N/A')})"
            # Add author if available
            if 'Auteur' in row:
                 expander_title += f" - {row['Auteur']}"

            with st.expander(expander_title):
                col1_hist, col2_hist = st.columns(2)
                with col1_hist:
                     st.markdown(f"**Statut Objectif:** {row.get('Statut', 'N/A')}")
                     st.markdown(f"**Symptômes Cibles:** {row.get('Symptômes Cibles', 'N/A')}")
                     st.markdown(f"**Interventions:** {row.get('Interventions', 'N/A')}")
                with col2_hist:
                     st.markdown(f"**Objectifs SMART:**\n{row.get('Objectifs', 'N/A')}")
                     st.markdown(f"**Tâches d'Activation:**\n{row.get('Tâches', 'N/A')}")

                st.markdown("---")
                st.markdown(f"**Commentaires Généraux:**\n{row.get('Commentaires', 'N/A')}")


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
