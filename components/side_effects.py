# components/side_effects.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

def side_effect_page():
    """Page for tracking treatment side effects"""
    st.header("Suivi des Effets Secondaires")
    
    if not st.session_state.get("selected_patient_id"):
        st.warning("Aucun patient sélectionné.")
        return
    
    # Load side effect data or initialize
    side_effect_file = 'data/side_effects.csv'
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    if 'side_effect_data' not in st.session_state:
        try:
            side_effect_data = pd.read_csv(side_effect_file)
        except FileNotFoundError:
            side_effect_data = pd.DataFrame(columns=[
                'PatientID', 'Date', 'Headache', 'Nausea', 
                'Scalp_Discomfort', 'Dizziness', 'Other', 'Notes'
            ])
        st.session_state.side_effect_data = side_effect_data
    
    # Filter for current patient
    patient_side_effects = st.session_state.side_effect_data[
        st.session_state.side_effect_data['PatientID'] == st.session_state.selected_patient_id
    ]
    
    # Display existing side effects if any
    if not patient_side_effects.empty:
        st.subheader("Effets secondaires signalés")
        
        # Display as a table with formatted column names
        display_df = patient_side_effects.copy()
        display_df.columns = [
            'ID Patient', 'Date', 'Mal de tête', 'Nausée', 
            'Inconfort du cuir chevelu', 'Étourdissements', 'Autre', 'Notes'
        ]
        st.dataframe(display_df)
        
        # Visualize side effects over time
        if len(patient_side_effects) > 1:
            st.subheader("Évolution des effets secondaires")
            
            # Convert dates for plotting
            patient_side_effects['Date'] = pd.to_datetime(patient_side_effects['Date'])
            
            # Melt the data for plotting
            side_effect_long = patient_side_effects.melt(
                id_vars=['PatientID', 'Date'],
                value_vars=['Headache', 'Nausea', 'Scalp_Discomfort', 'Dizziness'],
                var_name='Side_Effect',
                value_name='Severity'
            )
            
            # Map variable names to French for display
            side_effect_long['Side_Effect'] = side_effect_long['Side_Effect'].map({
                'Headache': 'Mal de tête',
                'Nausea': 'Nausée',
                'Scalp_Discomfort': 'Inconfort du cuir chevelu',
                'Dizziness': 'Étourdissements'
            })
            
            # Create line chart
            fig = px.line(
                side_effect_long, 
                x='Date', 
                y='Severity', 
                color='Side_Effect',
                title='Évolution des effets secondaires',
                labels={'Severity': 'Sévérité (0-10)', 'Side_Effect': 'Effet Secondaire'}
            )
            
            # Add markers to the lines
            fig.update_traces(mode='lines+markers')
            
            # Improve layout
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Sévérité (0-10)",
                yaxis_range=[0, 10]
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add a summary view
            st.subheader("Résumé des effets secondaires")
            
            # Calculate summary statistics
            summary = side_effect_long.groupby('Side_Effect')['Severity'].agg(['mean', 'max']).reset_index()
            summary.columns = ['Effet Secondaire', 'Sévérité Moyenne', 'Sévérité Maximum']
            summary['Sévérité Moyenne'] = summary['Sévérité Moyenne'].round(1)
            
            # Show summary table
            st.dataframe(summary)
            
            # Create a bar chart of max severity
            fig_max = px.bar(
                summary,
                x='Effet Secondaire',
                y='Sévérité Maximum',
                color='Effet Secondaire',
                title="Sévérité Maximum par Effet Secondaire"
            )
            st.plotly_chart(fig_max, use_container_width=True)
    else:
        st.info("Aucun effet secondaire n'a été enregistré pour ce patient.")
    
    # Form to add new side effect report
    st.subheader("Ajouter un rapport d'effets secondaires")
    with st.form("side_effect_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("Date", datetime.now())
            headache = st.slider("Mal de tête", 0, 10, 0, help="0 = Aucun, 10 = Insupportable")
            nausea = st.slider("Nausée", 0, 10, 0, help="0 = Aucune, 10 = Insupportable")
        
        with col2:
            scalp_discomfort = st.slider("Inconfort du cuir chevelu", 0, 10, 0, help="0 = Aucun, 10 = Insupportable")
            dizziness = st.slider("Étourdissements", 0, 10, 0, help="0 = Aucun, 10 = Insupportables")
            
        other = st.text_input("Autres effets secondaires")
        notes = st.text_area("Notes supplémentaires")
        
        submitted = st.form_submit_button("Soumettre")
        
        if submitted:
            # Add new entry
            new_entry = pd.DataFrame([{
                'PatientID': st.session_state.selected_patient_id,
                'Date': date.strftime('%Y-%m-%d'),
                'Headache': headache,
                'Nausea': nausea,
                'Scalp_Discomfort': scalp_discomfort,
                'Dizziness': dizziness,
                'Other': other,
                'Notes': notes
            }])
            
            # Concatenate with existing data
            st.session_state.side_effect_data = pd.concat([st.session_state.side_effect_data, new_entry], ignore_index=True)
            
            # Save to CSV
            st.session_state.side_effect_data.to_csv(side_effect_file, index=False)
            st.success("Rapport d'effets secondaires enregistré avec succès.")
            st.rerun()
    
    # Add guide for recording side effects
    with st.expander("Guide pour l'évaluation des effets secondaires"):
        st.markdown("""
        ### Échelle de Sévérité des Effets Secondaires (0-10)
        
        - **0**: Aucun effet secondaire
        - **1-3**: Effets secondaires légers - N'interfèrent pas avec les activités quotidiennes
        - **4-6**: Effets secondaires modérés - Interfèrent partiellement avec les activités quotidiennes
        - **7-9**: Effets secondaires sévères - Interfèrent significativement avec les activités quotidiennes
        - **10**: Effets secondaires insupportables - Empêchent les activités quotidiennes
        
        ### Effets Secondaires Courants de la rTMS
        
        - **Mal de tête**: Généralement léger à modéré, disparaît habituellement dans les 24 heures
        - **Inconfort du cuir chevelu**: Sensation de picotement ou d'inconfort au site de stimulation
        - **Nausée**: Moins fréquente, généralement légère
        - **Étourdissements**: Temporaires, généralement pendant ou juste après la séance
        
        Si des effets secondaires sévères ou non listés surviennent, veuillez contacter immédiatement l'équipe médicale.
        """)