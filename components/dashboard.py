# components/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
from services.network_analysis import generate_person_specific_network
from services.nurse_service import get_nurse_inputs

def get_patient_ema_data(patient_id):
    """Retrieve EMA data for a specific patient"""
    if 'simulated_ema_data' not in st.session_state or st.session_state.simulated_ema_data.empty:
        return pd.DataFrame()
        
    patient_ema = st.session_state.simulated_ema_data[
        st.session_state.simulated_ema_data['PatientID'] == patient_id
    ].sort_values(by='Timestamp')
    
    return patient_ema

def treatment_progress(patient_ema):
    """Display treatment progress tracking"""
    st.subheader("Suivi de Progression du Traitement")
    
    # Define treatment milestones
    milestones = ['Évaluation Initiale', 'Semaine 1', 'Semaine 2', 'Semaine 3', 'Semaine 4']
    
    # Calculate progress
    if not patient_ema.empty:
        # Get first and last entry dates
        first_entry = pd.to_datetime(patient_ema['Timestamp'].min())
        last_entry = pd.to_datetime(patient_ema['Timestamp'].max())
        
        # Calculate days elapsed
        days_elapsed = (last_entry - first_entry).days
        
        # Figure out which milestone they're at
        current_milestone = min(int(days_elapsed / 7) + 1, len(milestones))
        
        # Calculate progress percentage (4 weeks = 100%)
        progress_percentage = min(days_elapsed / 28 * 100, 100)
        
        # Show progress bar
        st.progress(progress_percentage / 100)
        
        # Show milestone indicators
        cols = st.columns(len(milestones))
        for i, (col, milestone) in enumerate(zip(cols, milestones)):
            with col:
                if i < current_milestone - 1:
                    # Past milestones in green
                    st.success(milestone)
                elif i == current_milestone - 1:
                    # Current milestone in blue
                    st.info(milestone)
                else:
                    # Future milestones in gray
                    st.write(milestone)
    else:
        st.warning("Aucune donnée EMA disponible pour suivre la progression.")

# Modified start of the dashboard.py file
def patient_dashboard():
    """Main dashboard for individual patient view"""
    st.header("Tableau de Bord du Patient")
    
    # Simple patient indicator instead of navigation controls
    if st.session_state.selected_patient_id:
        st.success(f"Patient actuel: {st.session_state.selected_patient_id}")
    else:
        st.warning("Aucun patient sélectionné. Veuillez choisir un patient dans la barre latérale.")
        return
    
    # Retrieve patient data
    patient_row = st.session_state.final_data[
        st.session_state.final_data["ID"] == st.session_state.selected_patient_id
    ]
    
    if patient_row.empty:
        st.error("Données du patient non trouvées.")
        return
        
    patient_data = patient_row.iloc[0]

    # Retrieve EMA data
    patient_ema = get_patient_ema_data(st.session_state.selected_patient_id)

    # Create tabs for better organization
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Aperçu du Patient", 
        "📊 Évaluations Cliniques", 
        "🔄 Réseau de Symptômes",
        "📈 Progression",
        "📝 Notes Infirmières"
    ])
    
    # Retrieve patient data
    patient_row = st.session_state.final_data[
        st.session_state.final_data["ID"] == st.session_state.selected_patient_id
    ]
    
    if patient_row.empty:
        st.error("Données du patient non trouvées.")
        return

    # Retrieve patient data
    patient_row = st.session_state.final_data[
        st.session_state.final_data["ID"] == st.session_state.selected_patient_id
    ]
    
    if patient_row.empty:
        st.error("Données du patient non trouvées.")
        return
        
    patient_data = patient_row.iloc[0]

    # Retrieve EMA data
    patient_ema = get_patient_ema_data(st.session_state.selected_patient_id)

    with tab1:
        st.header("Aperçu du Patient")
        
        # Patient overview in metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            sex_numeric = patient_data.get('sexe', 'N/A')
            sex = "Homme" if sex_numeric == '1' else "Femme" if sex_numeric == '2' else "Autre" if sex_numeric else "N/A"
            st.metric(label="Sexe", value=sex)
        
        with col2:
            st.metric(label="Âge", value=patient_data.get('age', 'N/A'))
            
        with col3:
            st.metric(label="Protocole", value=patient_data.get('protocol', 'N/A'))
        
        # Clinical data in expandable sections
        with st.expander("Données Cliniques Détaillées", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Comorbidités")
                st.write(patient_data.get('comorbidities', 'Aucune comorbidité documentée'))
            with col2:
                st.subheader("Historique de Traitement")
                psychotherapie = "Oui" if patient_data.get('psychotherapie_bl') == '1' else "Non"
                ect = "Oui" if patient_data.get('ect_bl') == '1' else "Non"
                rtms = "Oui" if patient_data.get('rtms_bl') == '1' else "Non"
                tdcs = "Oui" if patient_data.get('tdcs_bl') == '1' else "Non"
                
                st.write(f"**Psychothérapie antérieure:** {psychotherapie}")
                st.write(f"**ECT antérieure:** {ect}")
                st.write(f"**rTMS antérieure:** {rtms}")
                st.write(f"**tDCS antérieure:** {tdcs}")
        
        # SMART objectives
        st.subheader("Objectifs SMART")
        nurse_inputs = get_nurse_inputs(st.session_state.selected_patient_id, st.session_state.nurse_data)
        
        # Use colored boxes for objectives and tasks
        if nurse_inputs.get("objectives"):
            st.info(nurse_inputs.get("objectives"))
        else:
            st.warning("Aucun objectif défini pour ce patient.")
            
        if nurse_inputs.get("tasks"):
            st.success(f"**Tâches d'activation comportementale:**\n\n{nurse_inputs.get('tasks')}")
            
        # Add data export option
        if st.button("Exporter les données du patient"):
            # Get patient data
            patient_df = st.session_state.final_data[
                st.session_state.final_data["ID"] == st.session_state.selected_patient_id
            ]
            
            # Convert to CSV
            csv = patient_df.to_csv(index=False)
            
            # Encode for download
            b64 = base64.b64encode(csv.encode()).decode()
            
            # Create download link
            href = f'<a href="data:file/csv;base64,{b64}" download="patient_{st.session_state.selected_patient_id}_data.csv">Télécharger les données (CSV)</a>'
            
            # Display link
            st.markdown(href, unsafe_allow_html=True)

    with tab2:
        st.header("Évaluations Cliniques")
        
        # Create sub-tabs for different assessments
        subtab1, subtab2, subtab3 = st.tabs(["MADRS", "PHQ-9", "PID-5"])
        
        with subtab1:
            # MADRS visualization
            st.subheader("Scores MADRS")
            col1, col2 = st.columns(2)
            with col1:
                madrs_total = {
                    "Baseline": patient_data.get("madrs_score_bl", 0),
                    "Jour 30": patient_data.get("madrs_score_fu", 0)
                }
                
                # Add severity level
                severity = "N/A"
                if "madrs_score_bl" in patient_data and not pd.isna(patient_data["madrs_score_bl"]):
                    score = patient_data["madrs_score_bl"]
                    if score < 7:
                        severity = "Normal"
                    elif score < 20:
                        severity = "Légère"
                    elif score < 35:
                        severity = "Modérée"
                    else:
                        severity = "Sévère"
                
                st.metric(
                    label="Sévérité Initiale", 
                    value=severity,
                    delta=f"Score: {madrs_total['Baseline']}"
                )
                
                # Calculate improvement percentage
                if madrs_total["Baseline"] > 0 and madrs_total["Jour 30"] > 0:
                    improvement = ((madrs_total["Baseline"] - madrs_total["Jour 30"]) / madrs_total["Baseline"]) * 100
                    st.metric(
                        label="Amélioration", 
                        value=f"{improvement:.1f}%",
                        delta=f"{madrs_total['Baseline'] - madrs_total['Jour 30']} points"
                    )
                
                # Bar chart
                fig_madrs = px.bar(
                    x=list(madrs_total.keys()),
                    y=list(madrs_total.values()),
                    labels={"x": "Temps", "y": "Score MADRS"},
                    color=list(madrs_total.keys()),
                    color_discrete_sequence=st.session_state.PASTEL_COLORS,
                    title="Score Total MADRS"
                )
                st.plotly_chart(fig_madrs, use_container_width=True)
                
            with col2:
                st.subheader("Scores par Item MADRS")
                # Assuming MADRS item columns are named like 'madrs_1_bl', 'madrs_1_fu', etc.
                madrs_items = patient_data.filter(regex=r"^madrs[_.]\d+[_.](bl|fu)$")
                if madrs_items.empty:
                    st.warning("Aucun score par item MADRS trouvé pour ce patient.")
                else:
                    madrs_items_df = madrs_items.to_frame().T
                    madrs_long = madrs_items_df.melt(var_name="Item", value_name="Score").dropna()
                    madrs_long["Temps"] = madrs_long["Item"].str.extract("_(bl|fu)$")[0]
                    madrs_long["Temps"] = madrs_long["Temps"].map({"bl": "Baseline", "fu": "Jour 30"})
                    madrs_long["Item_Number"] = madrs_long["Item"].str.extract(r"madrs[_.](\d+)_")[0].astype(int)
                    madrs_long["Item"] = madrs_long["Item_Number"].map(st.session_state.MADRS_ITEMS_MAPPING)
                    madrs_long.dropna(subset=["Item"], inplace=True)

                    if madrs_long.empty:
                        st.warning("Tous les scores par item MADRS sont NaN.")
                    else:
                        fig = px.bar(
                            madrs_long,
                            x="Item",
                            y="Score",
                            color="Temps",
                            barmode="group",
                            title="Scores par Item MADRS",
                            template="plotly_white",
                            color_discrete_sequence=st.session_state.PASTEL_COLORS
                        )
                        fig.update_xaxes(tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
            
            # Patient comparison section
            with st.expander("Comparer avec d'autres patients"):
                # Let user select other patients to compare
                other_patients = st.multiselect(
                    "Sélectionner des patients à comparer", 
                    options=[id for id in st.session_state.final_data['ID'].unique() 
                             if id != st.session_state.selected_patient_id]
                )
                
                # If they selected some patients, show the comparison
                if other_patients:
                    # Get data for all selected patients
                    patients_to_compare = [st.session_state.selected_patient_id] + other_patients
                    comparison_data = st.session_state.final_data[
                        st.session_state.final_data['ID'].isin(patients_to_compare)
                    ]
                    
                    # Show a table with MADRS scores
                    st.subheader("Comparaison des scores MADRS")
                    comparison_table = comparison_data[['ID', 'madrs_score_bl', 'madrs_score_fu']]
                    comparison_table.columns = ['Patient ID', 'MADRS Initial', 'MADRS Jour 30']
                    st.dataframe(comparison_table)
                    
                    # Calculate improvement
                    comparison_table['Amélioration'] = comparison_table['MADRS Initial'] - comparison_table['MADRS Jour 30']
                    comparison_table['Amélioration (%)'] = (comparison_table['Amélioration'] / 
                                                          comparison_table['MADRS Initial'] * 100).round(1)
                    
                    # Create a grouped bar chart for initial vs follow-up
                    fig = px.bar(
                        comparison_table, 
                        x='Patient ID', 
                        y=['MADRS Initial', 'MADRS Jour 30'],
                        barmode='group',
                        title="Comparaison des Scores MADRS"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Create a bar chart for improvement percentage
                    fig_improvement = px.bar(
                        comparison_table,
                        x='Patient ID',
                        y='Amélioration (%)',
                        title="Pourcentage d'Amélioration MADRS",
                        color='Amélioration (%)',
                        color_continuous_scale='Blues'
                    )
                    st.plotly_chart(fig_improvement, use_container_width=True)
        
        with subtab2:
            # PHQ-9 visualization
            has_phq9 = any(col.startswith('phq9_') for col in st.session_state.final_data.columns)
            if has_phq9:
                st.subheader("Progression PHQ-9")
                phq9_days = [5, 10, 15, 20, 25, 30]
                phq9_scores = {}
                missing_phq9 = False
                for day in phq9_days:
                    item_columns = [f'phq9_day{day}_item{item}' for item in range(1, 10)]
                    if not set(item_columns).issubset(st.session_state.final_data.columns):
                        missing_phq9 = True
                        break
                    phq9_score = patient_data[item_columns].sum()
                    phq9_scores[f'Jour {day}'] = phq9_score

                if missing_phq9:
                    st.warning("Données PHQ-9 incomplètes pour ce patient.")
                else:
                    phq9_df = pd.DataFrame(list(phq9_scores.items()), columns=["Jour", "Score"])
                    fig_phq9 = px.line(
                        phq9_df,
                        x="Jour",
                        y="Score",
                        markers=True,
                        title="Progression PHQ-9",
                        template="plotly_white",
                        color_discrete_sequence=[st.session_state.PASTEL_COLORS[0]]
                    )
                    fig_phq9.update_layout(xaxis_title="Jour", yaxis_title="Score PHQ-9")
                    st.plotly_chart(fig_phq9, use_container_width=True)
            else:
                st.info("Les données PHQ-9 ne sont pas disponibles.")
        
        with subtab3:
            # PID-5 visualization - simplified version here, detailed in pid5_details.py
            has_pid5 = any(col.startswith('pid5_') for col in st.session_state.final_data.columns)
            if has_pid5:
                st.subheader("Scores PID-5")
                st.info("Voir l'onglet 'Détails PID-5' pour une analyse complète des scores PID-5.")
                
                # Create quick summary
                dimension_scores_bl = {}
                dimension_scores_fu = {}
                for dimension, items in st.session_state.PID5_DIMENSIONS_MAPPING.items():
                    try:
                        baseline_score = patient_data[[f'pid5_{item}_bl' for item in items]].sum()
                        followup_score = patient_data[[f'pid5_{item}_fu' for item in items]].sum()
                        dimension_scores_bl[dimension] = baseline_score
                        dimension_scores_fu[dimension] = followup_score
                    except:
                        st.warning(f"Données manquantes pour dimension {dimension}")
                
                if dimension_scores_bl and dimension_scores_fu:
                    # Create a simplified radar chart
                    categories = list(st.session_state.PID5_DIMENSIONS_MAPPING.keys())
                    values_bl = [dimension_scores_bl.get(cat, 0) for cat in categories]
                    values_fu = [dimension_scores_fu.get(cat, 0) for cat in categories]
                    
                    # Close the radar chart
                    categories += [categories[0]]
                    values_bl += [values_bl[0]]
                    values_fu += [values_fu[0]]
                    
                    fig_spider = go.Figure()
                    fig_spider.add_trace(go.Scatterpolar(
                        r=values_bl,
                        theta=categories,
                        fill='toself',
                        name='Baseline',
                        line_color=st.session_state.PASTEL_COLORS[0]
                    ))
                    fig_spider.add_trace(go.Scatterpolar(
                        r=values_fu,
                        theta=categories,
                        fill='toself',
                        name='Jour 30',
                        line_color=st.session_state.PASTEL_COLORS[1]
                    ))
                    fig_spider.update_layout(
                        polar=dict(radialaxis=dict(visible=False, range=[0, 15])),
                        showlegend=True,
                        height=400
                    )
                    st.plotly_chart(fig_spider, use_container_width=True)
            else:
                st.info("Les données PID-5 ne sont pas disponibles.")

    with tab3:
        st.header("Réseau de Symptômes")
        if patient_ema.empty:
            st.warning("Aucune donnée EMA disponible pour ce patient. Le réseau ne peut pas être généré.")
        else:
            # Add threshold slider for interactive network adjustment
            threshold = st.slider(
                "Seuil de force des connexions", 
                min_value=0.1, 
                max_value=0.7, 
                value=0.3, 
                step=0.05,
                help="Ajustez ce seuil pour afficher des connexions plus ou moins fortes entre les symptômes."
            )
            
            # Option to load the network (which might be computationally intensive)
            if st.checkbox("Générer le réseau de symptômes", value=False):
                with st.spinner('Génération du réseau en cours...'):
                    try:
                        fig_network = generate_person_specific_network(
                            patient_ema, 
                            st.session_state.selected_patient_id, 
                            st.session_state.SYMPTOMS, 
                            threshold=threshold
                        )
                        st.plotly_chart(fig_network, use_container_width=True)
                        
                        # Add network interpretation
                        with st.expander("Interprétation du Réseau de Symptômes"):
                            st.markdown("""
                            **Comment interpréter ce réseau:**
                            
                            - Chaque nœud représente un symptôme
                            - Les connexions indiquent des relations temporelles entre les symptômes
                            - La couleur des nœuds indique le nombre de connexions
                            - Plus un nœud a de connexions, plus il peut être central dans la psychopathologie
                            
                            Les symptômes fortement connectés peuvent être des cibles prioritaires pour l'intervention.
                            """)
                    except Exception as e:
                        st.error(f"Erreur lors de la génération du réseau de symptômes: {e}")
                        st.write("Détails techniques pour le support:", str(e))
            else:
                st.info("Cochez la case ci-dessus pour générer le réseau de symptômes.")

    with tab4:
        st.header("Progression du Traitement")
        
        # Treatment progress tracking
        treatment_progress(patient_ema)
        
        # Display EMA data trends if available
        if not patient_ema.empty:
            st.subheader("Évolution des Symptômes")
            
            # Group by day for cleaner visualization
            daily_symptoms = patient_ema.groupby('Day')[st.session_state.SYMPTOMS].mean().reset_index()
            
            # Select which symptoms to display
            symptom_categories = {
                "MADRS Items": st.session_state.MADRS_ITEMS,
                "Anxiety Items": st.session_state.ANXIETY_ITEMS,
                "Other Symptoms": [st.session_state.SLEEP, st.session_state.ENERGY, st.session_state.STRESS]
            }
            
            selected_category = st.selectbox(
                "Catégorie de symptômes à afficher", 
                options=list(symptom_categories.keys())
            )
            
            selected_symptoms = symptom_categories[selected_category]
            
            # Create line chart for selected symptoms
            fig = px.line(
                daily_symptoms,
                x="Day",
                y=selected_symptoms,
                markers=True,
                title=f"Évolution des {selected_category}",
                template="plotly_white"
            )
            
            # Update layout for better readability
            fig.update_layout(
                xaxis_title="Jour",
                yaxis_title="Score",
                legend_title="Symptôme"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Correlation heatmap between symptoms
            st.subheader("Corrélations entre Symptômes")
            
            # Calculate correlation matrix
            corr_matrix = patient_ema[selected_symptoms].corr()
            
            # Create heatmap
            fig_heatmap = px.imshow(
                corr_matrix,
                text_auto=".2f",
                color_continuous_scale="Blues",
                title=f"Corrélations des {selected_category}"
            )
            
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("Aucune donnée EMA disponible pour visualiser l'évolution des symptômes.")

    with tab5:
        st.header("Notes Infirmières")
        
        # Use columns for a cleaner form layout
        with st.form(key='nursing_inputs_dashboard_form'):
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
                try:
                    from services.nurse_service import save_nurse_inputs
                    save_nurse_inputs(
                        st.session_state.selected_patient_id, 
                        objectives_input, 
                        tasks_input, 
                        comments_input, 
                        st.session_state.nurse_data, 
                        st.session_state.NURSE_INPUTS_CSV
                    )
                    # Reload nurse data
                    st.session_state.nurse_data = load_nurse_data(st.session_state.NURSE_INPUTS_CSV)
                    st.success("Entrées infirmières sauvegardées avec succès.")
                except Exception as e:
                    st.error(f"Erreur lors de la sauvegarde des entrées infirmières: {e}")
                    
        # History of notes (simulated - would be replaced with actual database in production)
        st.subheader("Historique des Notes")
        
        if 'history' not in st.session_state:
            st.session_state.history = {}
            
        if st.session_state.selected_patient_id not in st.session_state.history:
            # This would be replaced with actual database queries
            st.session_state.history[st.session_state.selected_patient_id] = [
                {"date": "2024-01-15", "author": "Dr. Martin", "note": "Patient showing initial response to treatment"},
                {"date": "2024-01-22", "author": "Infirmière Dubois", "note": "Patient reports improved sleep quality"}
            ]
            
        for note in st.session_state.history[st.session_state.selected_patient_id]:
            with st.expander(f"{note['date']} - {note['author']}"):
                st.write(note['note'])