# components/patient_journey.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import logging
from services.nurse_service import get_nurse_inputs_history, get_side_effects_history
from datetime import datetime, timedelta # Ensure datetime is imported here too

def patient_journey_page():
    """Displays a chronological timeline of key patient events."""
    st.header("🗓️ Parcours du Patient")

    # Check patient selection
    if not st.session_state.get("selected_patient_id"):
        st.warning("⚠️ Aucun patient sélectionné. Veuillez en choisir un dans la barre latérale.")
        return

    patient_id = st.session_state.selected_patient_id
    st.info(f"Patient Actuel: **{patient_id}**")

    # Initialize list to hold valid event DataFrames
    all_event_dfs = [] # Use a different name to avoid confusion

    # --- Data Fetching & Processing ---
    try:
        # 1. Get Nurse Inputs History
        try:
            nurse_history = get_nurse_inputs_history(patient_id)
            if nurse_history is not None and not nurse_history.empty and 'timestamp' in nurse_history.columns:
                df_nurse = pd.DataFrame() # Create new df
                df_nurse['date'] = pd.to_datetime(nurse_history['timestamp'])
                df_nurse['event_type'] = 'Plan de Soins / Note'
                # Ensure details column is created correctly as strings
                df_nurse['details'] = nurse_history.apply(
                    lambda row: f"Statut: {row.get('goal_status', 'N/A')}. Obj: {str(row.get('objectives', ''))[:40]}...", axis=1
                ).astype(str) # Force to string type
                all_event_dfs.append(df_nurse[['date', 'event_type', 'details']]) # Only keep needed columns
            else:
                logging.info(f"No nurse history found or timestamp missing for {patient_id}")
        except Exception as e:
            logging.error(f"Error processing nurse history for journey: {e}")
            st.warning("Erreur lors du traitement de l'historique des notes infirmières.")

        # 2. Get Side Effects History
        try:
            side_effect_history = get_side_effects_history(patient_id)
            if side_effect_history is not None and not side_effect_history.empty and 'report_date' in side_effect_history.columns:
                df_side_effects = pd.DataFrame() # Create new df
                df_side_effects['date'] = pd.to_datetime(side_effect_history['report_date'])
                df_side_effects['event_type'] = 'Effet Secondaire Signalé'

                def summarize_effects(row):
                    s = []
                    # Use .get() for safety in case columns are missing
                    if row.get('headache', 0) > 0: s.append(f"Tête:{int(row.get('headache',0))}")
                    if row.get('nausea', 0) > 0: s.append(f"Nausée:{int(row.get('nausea',0))}")
                    if row.get('scalp_discomfort', 0) > 0: s.append(f"Scalp:{int(row.get('scalp_discomfort',0))}")
                    if row.get('dizziness', 0) > 0: s.append(f"Étourdi:{int(row.get('dizziness',0))}")
                    other = str(row.get('other_effects', ''))
                    if other: s.append(f"Autre: {other[:20]}...") # Truncate other effects slightly
                    return ", ".join(s) if s else "Aucun effet > 0"

                df_side_effects['details'] = side_effect_history.apply(summarize_effects, axis=1).astype(str) # Force to string
                all_event_dfs.append(df_side_effects[['date', 'event_type', 'details']]) # Only keep needed columns
            else:
                logging.info(f"No side effect history found or report_date missing for {patient_id}")
        except Exception as e:
            logging.error(f"Error processing side effect history for journey: {e}")
            st.warning("Erreur lors du traitement de l'historique des effets secondaires.")

        # 3. Get Key Assessment Dates/Info from main data
        try:
            if 'final_data' in st.session_state and not st.session_state.final_data.empty:
                if patient_id in st.session_state.final_data['ID'].values:
                    patient_main_data = st.session_state.final_data[st.session_state.final_data['ID'] == patient_id].iloc[0]
                    assessment_events_list = []
                    start_date_str = patient_main_data.get('Timestamp')
                    start_date = pd.to_datetime(start_date_str) if pd.notna(start_date_str) else None

                    if start_date:
                         madrs_bl = patient_main_data.get('madrs_score_bl', 'N/A')
                         assessment_events_list.append({'date': start_date, 'event_type': 'Évaluation Initiale', 'details': f"MADRS BL: {madrs_bl}"})
                         madrs_fu = patient_main_data.get('madrs_score_fu', 'N/A')
                         fu_date_approx = start_date + timedelta(days=30) # Still approximate
                         assessment_events_list.append({'date': fu_date_approx, 'event_type': 'Évaluation J30 (Approx)', 'details': f"MADRS FU: {madrs_fu}"})

                         # Ensure this DataFrame also has the correct columns
                         df_assessments = pd.DataFrame(assessment_events_list)
                         if not df_assessments.empty:
                              all_event_dfs.append(df_assessments[['date', 'event_type', 'details']])

                    else:
                         logging.warning(f"Start date ('Timestamp') not found for {patient_id}, assessments not added to timeline.")
                else:
                     logging.error(f"Patient ID {patient_id} not found in main data for journey.")
            else:
                logging.error("Main patient data ('final_data') not loaded.")
        except Exception as e:
            logging.error(f"Error processing assessment events for journey: {e}")
            st.warning("Erreur lors du traitement des dates d'évaluation.")


        # --- Combine and Sort Events ---
        if not all_event_dfs:
             st.info("ℹ️ Aucune donnée d'historique trouvée pour construire le parcours de ce patient.")
             return # Stop if no valid event DataFrames found

        # Filter out empty dataframes before concatenating
        valid_dfs = [df for df in all_event_dfs if not df.empty and list(df.columns) == ['date', 'event_type', 'details']]
        if not valid_dfs:
            st.info("ℹ️ Aucune donnée d'historique valide trouvée après traitement.")
            return

        journey_df = pd.concat(valid_dfs, ignore_index=True)
        journey_df.dropna(subset=['date'], inplace=True) # Remove events without a valid date
        journey_df['date'] = pd.to_datetime(journey_df['date'])
        journey_df.sort_values(by='date', ascending=True, inplace=True)

        # --- Display Timeline ---
        if journey_df.empty:
            st.info("ℹ️ Aucune donnée d'historique avec date valide trouvée.")
        else:
            st.subheader("Chronologie des Événements")
            st.write("Visualisation chronologique (les points représentent des événements) :")

            event_type_map = { 'Évaluation Initiale': 1, 'Évaluation J30 (Approx)': 1.1,
                               'Plan de Soins / Note': 2, 'Effet Secondaire Signalé': 3 }
            journey_df['y_value'] = journey_df['event_type'].map(event_type_map).fillna(0)
            journey_df['y_value'] = pd.to_numeric(journey_df['y_value'], errors='coerce').fillna(0)
            # Add less jitter to potentially reduce overlap issues if library versions differ
            journey_df['y_value'] = journey_df['y_value'] + np.random.uniform(-0.05, 0.05, size=len(journey_df))

            try:
                fig = px.scatter( journey_df, x='date', y='y_value', color='event_type', title="Parcours Patient Chronologique",
                                  hover_data={'date': '|%Y-%m-%d', 'event_type': True, 'details': True, 'y_value': False},
                                  labels={'date': 'Date', 'event_type': 'Type d\'Événement', 'y_value': ''})
                fig.update_layout( yaxis=dict(tickmode='array', tickvals=list(event_type_map.values()), ticktext=list(event_type_map.keys()), showgrid=False),
                                   xaxis_title="Date", legend_title_text='Type d\'Événement')
                fig.update_traces(marker=dict(size=12))
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Voir les détails des événements (triés par date)"):
                     for index, row in journey_df.iterrows():
                         st.markdown(f"**{row['date'].strftime('%Y-%m-%d')}**: {row.get('event_type', 'N/A')}")
                         # Ensure details are displayed as string
                         st.markdown(f"> _{str(row.get('details', 'N/A'))}_")
                         st.markdown("---")
            except Exception as e:
                 st.error(f"Erreur lors de la création du graphique chronologique: {e}")
                 logging.exception(f"Error creating journey plot for {patient_id}")

    except Exception as e:
        st.error(f"❌ Une erreur générale s'est produite lors de la génération du parcours patient: {e}")
        logging.exception(f"Error generating patient journey page for {patient_id}:")