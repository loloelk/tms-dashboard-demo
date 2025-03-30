# components/patient_journey.py
import streamlit as st
import pandas as pd
import plotly.express as px
# --- Required Imports Added ---
import numpy as np # For numerical operations (like adding jitter)
import logging     # For logging errors
# --- End of Added Imports ---
from services.nurse_service import get_nurse_inputs_history, get_side_effects_history
from datetime import datetime, timedelta

def patient_journey_page():
    """Displays a chronological timeline of key patient events."""
    st.header("🗓️ Parcours du Patient")

    if not st.session_state.get("selected_patient_id"):
        st.warning("⚠️ Aucun patient sélectionné. Veuillez en choisir un dans la barre latérale.")
        return

    patient_id = st.session_state.selected_patient_id
    st.info(f"Patient Actuel: **{patient_id}**")

    # --- Data Fetching ---
    try:
        # 1. Get Nurse Inputs History
        nurse_history = get_nurse_inputs_history(patient_id)
        if 'timestamp' in nurse_history.columns:
            nurse_history['date'] = pd.to_datetime(nurse_history['timestamp'])
            nurse_history['event_type'] = 'Plan de Soins / Note'
            nurse_history['details'] = nurse_history.apply(lambda row: f"Statut: {row.get('goal_status', 'N/A')}. Objectifs: {row.get('objectives', '')[:50]}...", axis=1)
        else:
            nurse_history = pd.DataFrame(columns=['date', 'event_type', 'details'])


        # 2. Get Side Effects History
        side_effect_history = get_side_effects_history(patient_id)
        if 'report_date' in side_effect_history.columns:
             side_effect_history['date'] = pd.to_datetime(side_effect_history['report_date'])
             side_effect_history['event_type'] = 'Effet Secondaire Signalé'
             # Create details string summarizing severity > 0
             def summarize_effects(row):
                 summary = []
                 if row.get('headache', 0) > 0: summary.append(f"Tête:{row['headache']}")
                 if row.get('nausea', 0) > 0: summary.append(f"Nausée:{row['nausea']}")
                 if row.get('scalp_discomfort', 0) > 0: summary.append(f"Scalp:{row['scalp_discomfort']}")
                 if row.get('dizziness', 0) > 0: summary.append(f"Étourdi:{row['dizziness']}")
                 if row.get('other_effects', ''): summary.append("Autre")
                 return ", ".join(summary) if summary else "Aucun effet > 0"
             side_effect_history['details'] = side_effect_history.apply(summarize_effects, axis=1)
        else:
             side_effect_history = pd.DataFrame(columns=['date', 'event_type', 'details'])


        # 3. Get Key Assessment Dates/Info from main data
        if 'final_data' in st.session_state:
            # Ensure the selected patient ID exists in the dataframe index or ID column
            if patient_id in st.session_state.final_data['ID'].values:
                patient_main_data = st.session_state.final_data[st.session_state.final_data['ID'] == patient_id].iloc[0]
                assessment_events = []

                # Use Timestamp as approximate start date if available
                start_date_str = patient_main_data.get('Timestamp')
                start_date = pd.to_datetime(start_date_str) if start_date_str else None

                if start_date:
                    # Baseline Assessment (approximate start)
                    madrs_bl = patient_main_data.get('madrs_score_bl', 'N/A')
                    assessment_events.append({
                        'date': start_date,
                        'event_type': 'Évaluation Initiale',
                        'details': f"MADRS Baseline: {madrs_bl}"
                    })

                    # Follow-up Assessment (approximate 30 days later)
                    madrs_fu = patient_main_data.get('madrs_score_fu', 'N/A')
                    # Assume FU is roughly 30 days after baseline date for timeline placement
                    # In reality, you'd need specific assessment date columns
                    fu_date_approx = start_date + timedelta(days=30)
                    assessment_events.append({
                        'date': fu_date_approx,
                        'event_type': 'Évaluation Jour 30 (Approx)',
                        'details': f"MADRS Suivi: {madrs_fu}"
                    })
                else:
                    st.warning("Date de début ('Timestamp') non trouvée pour ce patient, les dates d'évaluation ne peuvent pas être affichées sur la timeline.")

                assessments_df = pd.DataFrame(assessment_events)
            else:
                st.error(f"Patient ID {patient_id} non trouvé dans les données principales.")
                assessments_df = pd.DataFrame(columns=['date', 'event_type', 'details'])
        else:
            st.error("Données patient principales non chargées ('final_data' manquant).")
            assessments_df = pd.DataFrame(columns=['date', 'event_type', 'details'])


        # --- Combine and Sort Events ---
        journey_df = pd.concat([
            nurse_history[['date', 'event_type', 'details']],
            side_effect_history[['date', 'event_type', 'details']],
            assessments_df[['date', 'event_type', 'details']]
        ], ignore_index=True)

        # Drop rows where date could not be parsed or is missing
        journey_df.dropna(subset=['date'], inplace=True)
        # Ensure date column is datetime before sorting
        journey_df['date'] = pd.to_datetime(journey_df['date'])


        # Sort by date
        journey_df.sort_values(by='date', ascending=True, inplace=True)


        # --- Display Timeline ---
        if journey_df.empty:
            st.info("ℹ️ Aucune donnée d'historique trouvée pour construire le parcours de ce patient.")
        else:
            st.subheader("Chronologie des Événements")

            # Option 1: Simple List Display (Commented out, use Plotly)
            # st.write("Affichage simple de la liste des événements:")
            # for index, row in journey_df.iterrows():
            #    st.markdown(f"**{row['date'].strftime('%Y-%m-%d')}**: {row['event_type']} - _{row['details']}_")

            # Option 2: Plotly Timeline (more visual)
            st.write("Visualisation de la chronologie (les points représentent des événements) :")

             # Add a small numeric offset for visualization if needed, map event types to y-axis categories
            event_type_map = {
                 'Évaluation Initiale': 1,
                 'Évaluation Jour 30 (Approx)': 1.1, # Slightly offset assessments
                 'Plan de Soins / Note': 2,
                 'Effet Secondaire Signalé': 3
            }
            journey_df['y_value'] = journey_df['event_type'].map(event_type_map).fillna(0) # Map and fill NaNs if any type missing

             # Add some jitter to y_value to prevent complete overlap for same-day events of same type
            # Make sure y_value is numeric before adding jitter
            journey_df['y_value'] = pd.to_numeric(journey_df['y_value'], errors='coerce')
            journey_df.dropna(subset=['y_value'], inplace=True) # Drop rows where y_value couldn't be numeric
            journey_df['y_value'] = journey_df['y_value'] + np.random.uniform(-0.1, 0.1, size=len(journey_df))


            fig = px.scatter(
                 journey_df,
                 x='date',
                 y='y_value', # Use numeric mapping for y-axis placement
                 color='event_type',
                 title="Parcours Patient Chronologique",
                 hover_data={'date': '|%Y-%m-%d', 'event_type': True, 'details': True, 'y_value': False}, # Format hover date, hide y_value
                 labels={'date': 'Date', 'event_type': 'Type d\'Événement', 'y_value': ''} # Hide y-axis label
            )

            # Customize y-axis ticks to show event types instead of numbers
            fig.update_layout(
                 yaxis=dict(
                     tickmode='array',
                     tickvals=list(event_type_map.values()),
                     ticktext=list(event_type_map.keys()),
                     showgrid=False, # Optionally hide grid lines
                     range=[0.5, 3.5] # Adjust range to fit categories
                 ),
                 xaxis_title="Date",
                 legend_title_text='Type d\'Événement'
            )
            # Make markers larger
            fig.update_traces(marker=dict(size=12))

            st.plotly_chart(fig, use_container_width=True)

            # Display details in an expander below the chart
            with st.expander("Voir les détails des événements (triés par date)"):
                 # Ensure date column is datetime before formatting
                 journey_df['date'] = pd.to_datetime(journey_df['date'])
                 for index, row in journey_df.iterrows():
                     st.markdown(f"**{row['date'].strftime('%Y-%m-%d')}**: {row.get('event_type', 'N/A')}")
                     st.markdown(f"> _{row.get('details', 'N/A')}_")
                     st.markdown("---")


    except Exception as e:
        st.error(f"❌ Une erreur s'est produite lors de la génération du parcours patient: {e}")
        # Use logging here (now that it's imported)
        logging.exception(f"Error generating patient journey for {patient_id}:")