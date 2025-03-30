# components/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
from services.network_analysis import generate_person_specific_network
# Use the new database functions from nurse_service
from services.nurse_service import get_latest_nurse_inputs, save_nurse_inputs, get_nurse_inputs_history, get_side_effects_history
import numpy as np # Needed for standard deviation calculation

def get_patient_ema_data(patient_id):
    """Retrieve EMA data for a specific patient"""
    if 'simulated_ema_data' not in st.session_state or st.session_state.simulated_ema_data.empty:
        st.warning("Données EMA simulées non chargées.")
        return pd.DataFrame()

    patient_ema = st.session_state.simulated_ema_data[
        st.session_state.simulated_ema_data['PatientID'] == patient_id
    ].copy() # Create a copy to avoid SettingWithCopyWarning

    # Ensure Timestamp is datetime
    if not patient_ema.empty:
        patient_ema['Timestamp'] = pd.to_datetime(patient_ema['Timestamp'])
        patient_ema.sort_values(by='Timestamp', inplace=True)

    return patient_ema


def treatment_progress(patient_ema):
    """Display treatment progress tracking"""
    st.subheader("Suivi de Progression du Traitement")

    # Define treatment milestones (example)
    milestones = ['Éval Initiale', 'Semaine 1', 'Semaine 2', 'Semaine 3', 'Semaine 4', 'Fin Traitement']

    if not patient_ema.empty:
        # Get first and last entry dates
        first_entry = patient_ema['Timestamp'].min()
        last_entry = patient_ema['Timestamp'].max()

        # Calculate days elapsed since first entry
        # Assuming treatment starts around the first EMA entry date
        days_elapsed = (last_entry - first_entry).days

        # Determine treatment duration assumption (e.g., 4 weeks / 28 days standard?)
        # This might need to come from patient_data if treatment length varies
        assumed_duration_days = 28 # Example: 4 weeks

        # Calculate progress percentage based on assumed duration
        progress_percentage = min((days_elapsed / assumed_duration_days) * 100, 100)

         # Figure out which milestone they're likely at based on elapsed days
        # Map days to milestones (adjust thresholds as needed)
        if days_elapsed <= 1:
             current_milestone_index = 0 # Éval Initiale
        elif days_elapsed <= 7:
             current_milestone_index = 1 # Semaine 1
        elif days_elapsed <= 14:
             current_milestone_index = 2 # Semaine 2
        elif days_elapsed <= 21:
            current_milestone_index = 3 # Semaine 3
        elif days_elapsed <= assumed_duration_days:
             current_milestone_index = 4 # Semaine 4
        else:
             current_milestone_index = 5 # Fin Traitement

        # Show progress bar
        st.progress(progress_percentage / 100)
        st.write(f"Progression estimée: {progress_percentage:.0f}% ({days_elapsed} jours depuis la première donnée EMA)")


        # Show milestone indicators visually
        cols = st.columns(len(milestones))
        for i, (col, milestone) in enumerate(zip(cols, milestones)):
            with col:
                if i < current_milestone_index:
                    # Past milestones marked as complete
                    st.success(f"✅ {milestone}")
                elif i == current_milestone_index:
                    # Current milestone highlighted
                    st.info(f"➡️ {milestone}")
                else:
                    # Future milestones subdued
                    st.markdown(f"<span style='opacity: 0.5;'>⬜ {milestone}</span>", unsafe_allow_html=True)

    else:
        st.warning("ℹ️ Aucune donnée EMA disponible pour suivre la progression.")


def patient_dashboard():
    """Main dashboard for individual patient view, using database for notes/effects"""
    st.header("📊 Tableau de Bord du Patient")

    if not st.session_state.get("selected_patient_id"):
        st.warning("⚠️ Aucun patient sélectionné. Veuillez en choisir un dans la barre latérale.")
        return

    patient_id = st.session_state.selected_patient_id
    st.success(f"Patient Actuel: **{patient_id}**")

    # Retrieve main patient static data (assuming it's still loaded in session state)
    if 'final_data' not in st.session_state or st.session_state.final_data.empty:
         st.error("❌ Données principales du patient non chargées.")
         return

    patient_row = st.session_state.final_data[st.session_state.final_data["ID"] == patient_id]

    if patient_row.empty:
        st.error(f"❌ Données non trouvées pour le patient {patient_id}.")
        return

    patient_data = patient_row.iloc[0]

    # Retrieve EMA data
    patient_ema = get_patient_ema_data(patient_id)


    # Create tabs for better organization
    # --- Define Tabs ---
    # ********** START OF CHANGES: Added Plan de Soins tab **********
    tab_overview, tab_assessments, tab_network, tab_progress, tab_plan, tab_side_effects, tab_notes_history = st.tabs([
        "👤 Aperçu",
        "📈 Évaluations",
        "🕸️ Réseau Sx",
        "⏳ Progrès EMA",
        "🎯 Plan de Soins", # New Tab for latest plan
        "🩺 Effets 2nd", # Shortened Name
        "📝 Historique Notes" # New Tab for history
    ])
    # ********** END OF CHANGES: Added Plan de Soins tab **********


    # --- Tab 1: Patient Overview ---
    with tab_overview:
        st.header("👤 Aperçu du Patient")

        # Patient overview in metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            sex_numeric = patient_data.get('sexe', 'N/A')
            sex = "Homme" if sex_numeric == '1' else "Femme" if sex_numeric == '2' else "Autre" if sex_numeric else "N/A"
            st.metric(label="Sexe", value=sex)
        with col2:
            st.metric(label="Âge", value=patient_data.get('age', 'N/A'))
        with col3:
            st.metric(label="Protocole TMS", value=patient_data.get('protocol', 'N/A'))

        # Clinical data in expandable sections
        with st.expander("🩺 Données Cliniques Détaillées", expanded=False):
            col1_details, col2_details = st.columns(2)
            with col1_details:
                st.subheader("Comorbidités")
                st.write(patient_data.get('comorbidities', 'Aucune comorbidité documentée'))
            with col2_details:
                st.subheader("Historique de Traitement")
                psychotherapie = "Oui" if patient_data.get('psychotherapie_bl') == '1' else "Non"
                ect = "Oui" if patient_data.get('ect_bl') == '1' else "Non"
                rtms = "Oui" if patient_data.get('rtms_bl') == '1' else "Non"
                tdcs = "Oui" if patient_data.get('tdcs_bl') == '1' else "Non"
                st.write(f"**Psychothérapie antérieure:** {psychotherapie}")
                st.write(f"**ECT antérieure:** {ect}")
                st.write(f"**rTMS antérieure:** {rtms}")
                st.write(f"**tDCS antérieure:** {tdcs}")

        st.markdown("---")
        # Display latest SMART objectives and Tasks from DB - Moved to Plan de Soins tab

        # Add data export option (for the main patient data CSV)
        st.markdown("---")
        if st.button("Exporter les Données Principales du Patient (CSV)"):
            patient_main_df = patient_row.to_frame().T # Export only the selected patient's row
            csv = patient_main_df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="patient_{patient_id}_main_data.csv">Télécharger les données principales (CSV)</a>'
            st.markdown(href, unsafe_allow_html=True)


    # --- Tab 2: Clinical Assessments ---
    with tab_assessments:
        st.header("📈 Évaluations Cliniques")

        # Create sub-tabs for different assessments
        subtab_madrs, subtab_phq9, subtab_pid5 = st.tabs(["MADRS", "PHQ-9", "PID-5"])

        with subtab_madrs:
            st.subheader("Scores MADRS")
             # Check if MADRS columns exist
            if 'madrs_score_bl' not in patient_data or 'madrs_score_fu' not in patient_data:
                 st.warning("Données MADRS (baseline ou suivi) manquantes pour ce patient.")
            else:
                madrs_bl = patient_data["madrs_score_bl"]
                madrs_fu = patient_data["madrs_score_fu"]

                col1_madrs, col2_madrs = st.columns(2)

                with col1_madrs:
                    st.metric(label="MADRS Baseline", value=f"{madrs_bl}")
                    # Determine severity level based on baseline
                    severity = "N/A"
                    if not pd.isna(madrs_bl):
                        score = madrs_bl
                        if score <= 6: severity = "Normal"
                        elif score <= 19: severity = "Légère"
                        elif score <= 34: severity = "Modérée"
                        else: severity = "Sévère"
                    st.write(f"**Sévérité Initiale:** {severity}")

                    if not pd.isna(madrs_fu):
                        delta_score = madrs_fu - madrs_bl
                        st.metric(label="MADRS Jour 30", value=f"{madrs_fu}", delta=f"{delta_score} points")

                        # Calculate improvement percentage
                        if madrs_bl > 0:
                             improvement_pct = ((madrs_bl - madrs_fu) / madrs_bl) * 100
                             improvement_label = f"{improvement_pct:.1f}%"
                             st.metric(label="Amélioration", value=improvement_label)
                             # Classify response/remission
                             is_responder = improvement_pct >= 50
                             is_remitter = madrs_fu < 10
                             st.write(f"**Réponse (>50%):** {'Oui' if is_responder else 'Non'}")
                             st.write(f"**Rémission (<10):** {'Oui' if is_remitter else 'Non'}")
                        else:
                             st.write("Amélioration non calculable (baseline = 0)")
                    else:
                         st.metric(label="MADRS Jour 30", value="N/A")


                    # Bar chart for total scores
                    madrs_total_df = pd.DataFrame({
                         'Temps': ['Baseline', 'Jour 30'],
                         'Score': [madrs_bl, madrs_fu if not pd.isna(madrs_fu) else 0] # Use 0 for plotting if NaN
                     })
                    fig_madrs_total = px.bar(
                         madrs_total_df, x='Temps', y='Score',
                         title="Score Total MADRS",
                         color='Temps',
                         color_discrete_sequence=st.session_state.PASTEL_COLORS[:2],
                         labels={"Score": "Score MADRS Total"}
                    )
                    st.plotly_chart(fig_madrs_total, use_container_width=True)


                with col2_madrs:
                    st.subheader("Scores par Item MADRS")
                    # Filter for MADRS item columns (assuming format madrs_1_bl, madrs_1_fu etc.)
                    madrs_item_cols_bl = [f'madrs_{i}_bl' for i in range(1, 11)]
                    madrs_item_cols_fu = [f'madrs_{i}_fu' for i in range(1, 11)]

                    # Check if all needed columns exist
                    if all(col in patient_data for col in madrs_item_cols_bl) and \
                       all(col in patient_data for col in madrs_item_cols_fu):

                        items_data = []
                        for i in range(1, 11):
                            item_label = st.session_state.MADRS_ITEMS_MAPPING.get(i, f"Item {i}")
                            items_data.append({
                                'Item': item_label,
                                'Baseline': patient_data[f'madrs_{i}_bl'],
                                'Jour 30': patient_data[f'madrs_{i}_fu']
                            })

                        madrs_items_df = pd.DataFrame(items_data)
                        madrs_items_long = madrs_items_df.melt(id_vars='Item', var_name='Temps', value_name='Score')

                        if madrs_items_long['Score'].isna().all():
                             st.warning("Scores par item MADRS non disponibles.")
                        else:
                             fig_items = px.bar(
                                 madrs_items_long, x='Item', y='Score', color='Temps',
                                 barmode='group', title="Scores par Item MADRS (Baseline vs Jour 30)",
                                 template="plotly_white",
                                 color_discrete_sequence=st.session_state.PASTEL_COLORS[:2],
                                 labels={"Score": "Score (0-6)"}
                             )
                             fig_items.update_xaxes(tickangle=-45)
                             st.plotly_chart(fig_items, use_container_width=True)
                    else:
                         st.warning("Colonnes d'items MADRS manquantes ou incomplètes.")


                # --- Patient Comparison Section ---
                st.markdown("---")
                st.subheader("Comparaison avec d'autres patients")
                # Use cohort data loaded in session state
                all_data = st.session_state.final_data

                # Select comparison type
                comparison_type = st.radio(
                    "Comparer avec:",
                    ["Cohorte entière", "Patients sous même protocole"],
                    key="madrs_comparison_radio"
                )

                current_protocol = patient_data.get('protocol', 'N/A')
                comparison_group_df = pd.DataFrame() # Initialize empty

                if comparison_type == "Cohorte entière":
                    # Compare with all OTHER patients
                    comparison_group_df = all_data[all_data['ID'] != patient_id].copy()
                    comparison_title = "toute la cohorte (autres patients)"
                else: # "Patients sous même protocole"
                    if current_protocol != 'N/A':
                        # Compare with OTHER patients on same protocol
                        comparison_group_df = all_data[
                            (all_data['protocol'] == current_protocol) &
                            (all_data['ID'] != patient_id)
                        ].copy()
                        comparison_title = f"autres patients sous protocole {current_protocol}"
                    else:
                        comparison_title = "N/A (protocole inconnu)"


                if comparison_group_df.empty or 'madrs_score_bl' not in comparison_group_df.columns or 'madrs_score_fu' not in comparison_group_df.columns:
                    st.warning(f"Aucun patient ou données MADRS suffisantes pour comparaison avec {comparison_title}.")
                else:
                    # Filter comparison group for valid MADRS scores
                    comparison_group_df = comparison_group_df.dropna(subset=['madrs_score_bl', 'madrs_score_fu'])

                    if comparison_group_df.empty:
                         st.warning(f"Aucun patient avec données MADRS complètes dans le groupe : {comparison_title}.")
                    else:
                        # Calculate comparison stats
                        comp_initial = comparison_group_df['madrs_score_bl'].mean()
                        comp_followup = comparison_group_df['madrs_score_fu'].mean()
                        comp_improvement = comp_initial - comp_followup
                        comp_improvement_pct = (comp_improvement / comp_initial * 100) if comp_initial > 0 else 0

                        # Current patient values (ensure they exist)
                        current_initial = madrs_bl if not pd.isna(madrs_bl) else None
                        current_followup = madrs_fu if not pd.isna(madrs_fu) else None
                        current_improvement = (current_initial - current_followup) if current_initial is not None and current_followup is not None else None
                        current_improvement_pct = (current_improvement / current_initial * 100) if current_improvement is not None and current_initial is not None and current_initial > 0 else None

                        # Create comparison dataframe
                        comp_table_data = [
                             {
                                 'Patient': f"Patient {patient_id}",
                                 'MADRS Initial': f"{current_initial:.1f}" if current_initial is not None else "N/A",
                                 'MADRS Jour 30': f"{current_followup:.1f}" if current_followup is not None else "N/A",
                                 'Amélioration (%)': f"{current_improvement_pct:.1f}%" if current_improvement_pct is not None else "N/A"
                             },
                             {
                                 'Patient': f"Moyenne {comparison_title} (n={len(comparison_group_df)})",
                                 'MADRS Initial': f"{comp_initial:.1f}",
                                 'MADRS Jour 30': f"{comp_followup:.1f}",
                                 'Amélioration (%)': f"{comp_improvement_pct:.1f}%"
                             }
                         ]
                        comparison_table_display = pd.DataFrame(comp_table_data)
                        st.dataframe(comparison_table_display, hide_index=True)

                        # Create comparison bar chart data
                        chart_data = {
                             'Patient': [f"Patient {patient_id}", f"Moyenne {comparison_title}"],
                             'MADRS Initial': [current_initial if current_initial is not None else 0, comp_initial],
                             'MADRS Jour 30': [current_followup if current_followup is not None else 0, comp_followup]
                        }
                        comp_chart_df = pd.DataFrame(chart_data)
                        comp_chart_long = comp_chart_df.melt(id_vars='Patient', var_name='Temps', value_name='Score')

                        fig_comp_bar = px.bar(
                             comp_chart_long, x='Patient', y='Score', color='Temps',
                             barmode='group', title=f"Comparaison des Scores MADRS avec {comparison_title}",
                             color_discrete_sequence=st.session_state.PASTEL_COLORS[2:4]
                        )
                        st.plotly_chart(fig_comp_bar, use_container_width=True)


                        # Optional: Show distribution
                        if st.checkbox("Voir la distribution des améliorations dans le groupe de comparaison", key="show_dist_cb"):
                             comparison_group_df['improvement_pct'] = (comparison_group_df['madrs_score_bl'] - comparison_group_df['madrs_score_fu']) / comparison_group_df['madrs_score_bl'] * 100
                             comparison_group_df.dropna(subset=['improvement_pct'], inplace=True)

                             if not comparison_group_df.empty:
                                 fig_hist = px.histogram(
                                     comparison_group_df, x='improvement_pct', nbins=10,
                                     title=f"Distribution de l'amélioration (%) dans {comparison_title}",
                                     labels={'improvement_pct': 'Amélioration MADRS (%)'},
                                     color_discrete_sequence=[st.session_state.PASTEL_COLORS[4]]
                                 )
                                 # Add line for current patient if improvement exists
                                 if current_improvement_pct is not None:
                                     fig_hist.add_vline(
                                         x=current_improvement_pct, line_dash="dash", line_color="red",
                                         annotation_text=f"Patient {patient_id}", annotation_position="top right"
                                     )
                                 st.plotly_chart(fig_hist, use_container_width=True)
                             else:
                                  st.info("Pas assez de données pour afficher la distribution.")


        with subtab_phq9:
            # PHQ-9 visualization (if data exists)
             # Check if necessary columns exist in patient_data
            phq9_days = [5, 10, 15, 20, 25, 30]
            phq9_cols_exist = all(f'phq9_day{day}_item{item}' in patient_data for day in phq9_days for item in range(1, 10))

            if phq9_cols_exist:
                st.subheader("Progression PHQ-9")
                phq9_scores_over_time = {}
                for day in phq9_days:
                    item_columns = [f'phq9_day{day}_item{item}' for item in range(1, 10)]
                    # Sum scores for the day, handling potential NaNs by treating them as 0 for sum
                    daily_score = patient_data[item_columns].sum(skipna=True)
                    phq9_scores_over_time[f'Jour {day}'] = daily_score

                phq9_df = pd.DataFrame(list(phq9_scores_over_time.items()), columns=["Jour", "Score"])

                fig_phq9 = px.line(
                    phq9_df, x="Jour", y="Score", markers=True,
                    title="Progression PHQ-9 au Fil du Temps",
                    template="plotly_white",
                    labels={'Score': 'Score PHQ-9 Total'},
                    color_discrete_sequence=[st.session_state.PASTEL_COLORS[0]]
                )
                fig_phq9.update_layout(yaxis_range=[0, 27]) # PHQ-9 max score is 27
                st.plotly_chart(fig_phq9, use_container_width=True)
            else:
                st.info("ℹ️ Les données PHQ-9 journalières ne sont pas disponibles pour ce patient.")


        with subtab_pid5:
            # PID-5 visualization (link to dedicated page)
            has_pid5 = any(col.startswith('pid5_') and '_bl' in col for col in patient_data.index) and \
                       any(col.startswith('pid5_') and '_fu' in col for col in patient_data.index)

            if has_pid5:
                st.subheader("Scores PID-5")
                st.info("💡 Voir l'onglet 'Détails PID-5' dans la barre latérale pour une analyse complète.")

                # Quick summary radar chart
                try:
                    dimension_scores_bl = {}
                    dimension_scores_fu = {}
                    categories = list(st.session_state.PID5_DIMENSIONS_MAPPING.keys())

                    for dimension, items in st.session_state.PID5_DIMENSIONS_MAPPING.items():
                         # Safely get items, treating missing ones as 0
                         baseline_cols = [f'pid5_{item}_bl' for item in items]
                         followup_cols = [f'pid5_{item}_fu' for item in items]

                         # Sum only existing columns
                         baseline_score = patient_data.get(baseline_cols, pd.Series(0)).sum()
                         followup_score = patient_data.get(followup_cols, pd.Series(0)).sum()

                         dimension_scores_bl[dimension] = baseline_score
                         dimension_scores_fu[dimension] = followup_score

                    values_bl = [dimension_scores_bl.get(cat, 0) for cat in categories]
                    values_fu = [dimension_scores_fu.get(cat, 0) for cat in categories]

                    # Determine max value for radar range dynamically but add buffer
                    max_val = max(max(values_bl, default=0), max(values_fu, default=0))
                    radar_range = [0, max(10, max_val * 1.1)] # Ensure minimum range, add buffer

                    fig_spider = go.Figure()
                    # Baseline trace
                    fig_spider.add_trace(go.Scatterpolar(
                        r=values_bl + [values_bl[0]], # Close the loop
                        theta=categories + [categories[0]], # Close the loop
                        fill='toself', name='Baseline',
                        line_color=st.session_state.PASTEL_COLORS[0]
                    ))
                    # Follow-up trace
                    fig_spider.add_trace(go.Scatterpolar(
                        r=values_fu + [values_fu[0]], # Close the loop
                        theta=categories + [categories[0]], # Close the loop
                        fill='toself', name='Jour 30',
                        line_color=st.session_state.PASTEL_COLORS[1]
                    ))

                    fig_spider.update_layout(
                         title="Scores PID-5 par Dimension (Aperçu Rapide)",
                         polar=dict(radialaxis=dict(visible=True, range=radar_range)),
                         showlegend=True, height=400, template="plotly_white"
                    )
                    st.plotly_chart(fig_spider, use_container_width=True)

                except Exception as e:
                     st.warning(f"Impossible de générer le graphique radar PID-5 : {e}")

            else:
                st.info("ℹ️ Les données PID-5 ne sont pas disponibles pour ce patient.")


    # --- Tab 3: Symptom Network ---
    with tab_network:
        st.header("🕸️ Réseau de Symptômes (Basé sur EMA)")
        if patient_ema.empty:
            st.warning("⚠️ Aucune donnée EMA disponible pour ce patient. Le réseau ne peut pas être généré.")
        else:
            # Check if enough data points exist
             if len(patient_ema) < 10: # Arbitrary threshold - needs tuning
                  st.warning(f"⚠️ Pas assez de données EMA ({len(patient_ema)} entrées) pour une analyse fiable du réseau.")
             else:
                st.info("Ce réseau montre comment les symptômes (rapportés via EMA) s'influencent mutuellement au fil du temps.")
                # Add threshold slider for interactive network adjustment
                threshold = st.slider(
                    "Seuil de force des connexions",
                    min_value=0.1, max_value=0.7, value=0.3, step=0.05,
                    help="Ajustez ce seuil pour afficher des connexions plus (valeur basse) ou moins (valeur haute) fortes entre les symptômes.",
                    key="network_threshold_slider"
                )

                # Option to generate the network
                if st.button("🔄 Générer/Actualiser le Réseau de Symptômes"):
                    with st.spinner('⏳ Génération du réseau en cours... Cela peut prendre un moment.'):
                        try:
                            # Ensure symptom columns exist
                            symptoms_to_use = [s for s in st.session_state.SYMPTOMS if s in patient_ema.columns]
                            if not symptoms_to_use:
                                 st.error("❌ Aucune colonne de symptôme trouvée dans les données EMA.")
                            else:
                                 # Add 'PatientID' if it's missing for the model function (it expects it)
                                 if 'PatientID' not in patient_ema.columns:
                                      patient_ema['PatientID'] = patient_id # Add it back if missing

                                 fig_network = generate_person_specific_network(
                                     patient_ema,
                                     patient_id,
                                     symptoms_to_use, # Use only available symptoms
                                     threshold=threshold
                                 )
                                 st.plotly_chart(fig_network, use_container_width=True)

                                 # Add network interpretation guide
                                 with st.expander("💡 Interprétation du Réseau"):
                                      st.markdown("""
                                      - **Nœuds (Cercles):** Représentent les symptômes individuels (M=MADRS, A=Anxiété).
                                      - **Flèches (Lignes):** Indiquent une influence temporelle probable (Symptôme A au temps t-1 prédit Symptôme B au temps t).
                                      - **Couleur/Taille Nœud:** Indique souvent la 'centralité' (nombre de connexions). Les nœuds plus centraux peuvent être des cibles thérapeutiques importantes.
                                      - **Force (Seuil):** Seules les connexions dépassant le seuil choisi sont affichées.
                                      *Ce réseau est basé sur des modèles statistiques et suggère des relations potentielles.*
                                      """)
                        except Exception as e:
                            st.error(f"❌ Erreur lors de la génération du réseau: {e}")
                            st.exception(e) # Show full traceback for debugging if needed
                else:
                    st.info("Cliquez sur le bouton ci-dessus pour générer le réseau.")


    # --- Tab 4: EMA Progression ---
    with tab_progress:
        st.header("⏳ Progression (Basé sur EMA)")

        # Treatment progress timeline
        treatment_progress(patient_ema)
        st.markdown("---")

        if not patient_ema.empty:
             # Ensure 'Day' column exists
            if 'Day' not in patient_ema.columns:
                 st.warning("La colonne 'Day' est manquante dans les données EMA.")
            else:
                # --- Part 1: Daily Average Trend (Existing) ---
                st.subheader("📉 Évolution des Scores EMA Quotidiens Moyens")
                symptoms_present = [s for s in st.session_state.SYMPTOMS if s in patient_ema.columns]
                daily_symptoms = pd.DataFrame() # Initialize
                if not symptoms_present:
                     st.warning("Aucune colonne de symptôme connue trouvée dans les données EMA.")
                else:
                     daily_symptoms = patient_ema.groupby('Day')[symptoms_present].mean().reset_index()

                     # Select which symptoms to display (remains same)
                     symptom_categories = {
                         "MADRS Items": [s for s in st.session_state.MADRS_ITEMS if s in symptoms_present],
                         "Anxiety Items": [s for s in st.session_state.ANXIETY_ITEMS if s in symptoms_present],
                         "Autres (Sommeil, Énergie, Stress)": [s for s in [st.session_state.SLEEP, st.session_state.ENERGY, st.session_state.STRESS] if s in symptoms_present]
                     }
                     available_categories = {k: v for k, v in symptom_categories.items() if v}

                     if not available_categories:
                          st.warning("Aucune catégorie de symptômes EMA disponible pour l'affichage.")
                     else:
                          selected_category = st.selectbox(
                              "Afficher la tendance moyenne pour:",
                              options=list(available_categories.keys()),
                              key="ema_category_selector_avg" # Use unique key
                          )
                          selected_symptoms_avg = available_categories[selected_category]
                          fig_ema_trends = px.line(
                              daily_symptoms, x="Day", y=selected_symptoms_avg, markers=True,
                              title=f"Tendance Moyenne: {selected_category}",
                              template="plotly_white", labels={"value": "Score Moyen", "variable": "Symptôme"}
                          )
                          st.plotly_chart(fig_ema_trends, use_container_width=True)

                st.markdown("---")

                # --- Part 2: Symptom Variability (New) ---
                st.subheader("📈 Variabilité des Symptômes EMA au Fil du Temps")
                st.info("Visualise la fluctuation (écart-type) des scores EMA sur des périodes glissantes. Une diminution peut indiquer une stabilisation.")

                # Calculate rolling standard deviation (variability)
                # Need enough data points for rolling calculation
                rolling_window = st.slider("Fenêtre de calcul pour la variabilité (jours)", min_value=3, max_value=14, value=7, key="ema_variability_window")

                if daily_symptoms.empty or len(daily_symptoms) < rolling_window:
                     st.warning(f"Pas assez de jours de données ({len(daily_symptoms)}) pour calculer la variabilité sur une fenêtre de {rolling_window} jours.")
                elif not available_categories:
                     st.warning("Aucune catégorie de symptôme disponible pour l'analyse de variabilité.")
                else:
                     # Select symptoms for variability plot
                     selected_category_var = st.selectbox(
                         "Afficher la variabilité pour:",
                         options=list(available_categories.keys()),
                          key="ema_category_selector_var" # Use unique key
                     )
                     selected_symptoms_var = available_categories[selected_category_var]

                     # Calculate rolling standard deviation for selected symptoms
                     variability_df = daily_symptoms[['Day'] + selected_symptoms_var].copy()
                     for symptom in selected_symptoms_var:
                         # Calculate rolling std dev, minimum periods = 1 to get value even at start
                         variability_df[symptom] = variability_df[symptom].rolling(window=rolling_window, min_periods=1).std()

                     # Plot variability
                     fig_ema_variability = px.line(
                         variability_df, x='Day', y=selected_symptoms_var, markers=False, # Usually better without markers for std dev
                         title=f"Variabilité (Écart-Type Glissant sur {rolling_window} jours): {selected_category_var}",
                         template="plotly_white",
                         labels={"value": f"Écart-Type (Fenêtre={rolling_window}j)", "variable": "Symptôme"}
                     )
                     # Set Y axis to start from 0
                     # Handle potential NaNs or empty results from rolling calculation before finding max
                     max_y_val = variability_df[selected_symptoms_var].max(skipna=True).max(skipna=True)
                     fig_ema_variability.update_layout(yaxis_range=[0, max_y_val * 1.1 if not pd.isna(max_y_val) else 1]) # Adjust range slightly above max variability
                     st.plotly_chart(fig_ema_variability, use_container_width=True)


                st.markdown("---")

                # --- Part 3: Correlation Heatmap (Existing - keep optional) ---
                if st.checkbox("Afficher la heatmap des corrélations EMA", key="show_ema_corr_cb"):
                    st.subheader("↔️ Corrélations entre Symptômes EMA")
                    # Use the category selected for average trends for consistency
                    if available_categories:
                         selected_category_corr = st.selectbox(
                             "Calculer corrélations pour:",
                             options=list(available_categories.keys()),
                             key="ema_category_selector_corr" # Use unique key
                         )
                         selected_symptoms_corr = available_categories.get(selected_category_corr, []) # Use selection
                         if selected_symptoms_corr:
                              # Use the original patient_ema which has all entries, not daily averages
                              corr_matrix = patient_ema[selected_symptoms_corr].corr()
                              if corr_matrix.empty or corr_matrix.isna().all().all():
                                   st.warning("Impossible de calculer la matrice de corrélation pour les symptômes sélectionnés.")
                              else:
                                   fig_heatmap = px.imshow(
                                        corr_matrix, text_auto=".2f", aspect="auto",
                                        color_continuous_scale="Blues",
                                        title=f"Corrélations entre les {selected_category_corr.lower()} (EMA)"
                                   )
                                   st.plotly_chart(fig_heatmap, use_container_width=True)
                         else:
                              st.warning("Aucun symptôme sélectionné pour le calcul de corrélation.")
                    else:
                         st.warning("Aucune catégorie de symptômes disponible pour le calcul de corrélation.")

        else:
            st.info("ℹ️ Aucune donnée EMA disponible pour visualiser la progression.")


    # --- Tab 5: Treatment Plan ---
    with tab_plan:
        st.header("🎯 Plan de Soins Actuel")
        st.info("Ceci affiche la **dernière** entrée de plan de soins enregistrée. Pour ajouter ou modifier, allez à la page 'Plan de Soins et Entrées Infirmières'.")

        latest_plan = get_latest_nurse_inputs(patient_id)

        if latest_plan and latest_plan.get('timestamp'): # Check if plan exists and has timestamp
            plan_date = pd.to_datetime(latest_plan.get('timestamp')).strftime('%Y-%m-%d %H:%M')
            st.subheader(f"Dernière Mise à Jour: {plan_date}")

            col_stat, col_symp, col_int = st.columns([1,2,2])
            with col_stat:
                st.metric("Statut Objectif", latest_plan.get('goal_status', 'N/A'))
            with col_symp:
                st.markdown("**Symptômes Cibles:**")
                st.markdown(f"> {latest_plan.get('target_symptoms', 'Non spécifié')}")
            with col_int:
                st.markdown("**Interventions Planifiées:**")
                st.markdown(f"> {latest_plan.get('planned_interventions', 'Non spécifié')}")

            st.markdown("---")
            st.markdown("**Objectifs SMART Actuels:**")
            st.markdown(f"_{latest_plan.get('objectives', 'Non défini')}_")

            st.markdown("**Tâches d'Activation Actuelles:**")
            st.markdown(f"_{latest_plan.get('tasks', 'Non défini')}_")

            st.markdown("**Derniers Commentaires Cliniques:**")
            st.markdown(f"_{latest_plan.get('comments', 'Aucun commentaire récent.')}_")

        elif latest_plan: # Plan exists but maybe no timestamp (older entry?)
             st.warning("Dernier plan trouvé mais date inconnue.")
             # Display other fields anyway
             st.metric("Statut Objectif", latest_plan.get('goal_status', 'N/A'))
             st.markdown("**Symptômes Cibles:**")
             st.markdown(f"> {latest_plan.get('target_symptoms', 'Non spécifié')}")
             # ... display other fields ...
        else:
            st.warning("ℹ️ Aucun plan de soins trouvé pour ce patient.")
            if st.button("➕ Ajouter un premier plan de soins"):
                 st.info("Veuillez naviguer vers 'Plan de Soins et Entrées Infirmières' dans la barre latérale pour ajouter une entrée.")


    # --- Tab 6: Side Effects (Summary View) ---
    with tab_side_effects:
         st.header("🩺 Suivi des Effets Secondaires (Résumé)") # Renamed tab slightly
         st.info("💡 Ceci est un résumé. Pour ajouter ou voir l'historique détaillé, utilisez la page 'Suivi des Effets Secondaires' dans la barre latérale.")

         side_effects_history = get_side_effects_history(patient_id)
         if not side_effects_history.empty:
             st.subheader("Effets Signalés (Fréquence et Max Sévérité)")
             severity_cols = ['headache', 'nausea', 'scalp_discomfort', 'dizziness']
             summary_list = []
             for col in severity_cols:
                  # Ensure column exists before processing
                  if col in side_effects_history.columns:
                       # Ensure the column is numeric before comparison and aggregation
                       numeric_col = pd.to_numeric(side_effects_history[col], errors='coerce').fillna(0)
                       count = (numeric_col > 0).sum()
                       if count > 0:
                           max_sev = numeric_col.max()
                           summary_list.append(f"{col.replace('_', ' ').capitalize()}: {count} fois (max {max_sev}/10)")

             if summary_list: st.markdown("- " + "\n- ".join(summary_list))
             else: st.info("Aucun effet secondaire (sévérité > 0) signalé.")

             latest_report = side_effects_history.iloc[0] # Already sorted by date desc
             latest_note = latest_report.get('notes', '')
             latest_other = latest_report.get('other_effects', '')
             report_date = pd.to_datetime(latest_report['report_date']).strftime('%Y-%m-%d') if 'report_date' in latest_report else "Date inconnue"

             if latest_note or latest_other:
                  with st.expander(f"Détails du Dernier Rapport ({report_date})"):
                       if latest_other: st.write(f"**Autres effets:** {latest_other}")
                       if latest_note: st.write(f"**Notes:** {latest_note}")
         else:
             st.info("ℹ️ Aucun rapport d'effet secondaire trouvé.")


    # --- Tab 7: Nurse Notes History ---
    with tab_notes_history:
        st.header("📝 Historique des Notes Infirmières")
        st.info("Ceci affiche toutes les notes précédentes. Pour ajouter une nouvelle note ou voir le plan actuel, utilisez les autres onglets ou la page dédiée.")

        notes_history_df = get_nurse_inputs_history(patient_id)

        if notes_history_df.empty:
            st.info("ℹ️ Aucune note historique trouvée pour ce patient.")
        else:
            st.info(f"Affichage des {len(notes_history_df)} notes/plans précédents (les plus récents en premier).")
            # Define columns to display (same as in nurse_inputs_page)
            display_columns = [
                'timestamp', 'goal_status', 'objectives', 'tasks',
                'target_symptoms', 'planned_interventions', 'comments'
            ]
            display_columns = [col for col in display_columns if col in notes_history_df.columns]
            display_df_hist = notes_history_df[display_columns].copy()
            display_df_hist.rename(columns={
                'timestamp': 'Date/Heure', 'goal_status': 'Statut', 'objectives': 'Objectifs',
                'tasks': 'Tâches', 'target_symptoms': 'Symptômes Cibles',
                'planned_interventions': 'Interventions', 'comments': 'Commentaires'
            }, inplace=True)
            if 'Date/Heure' in display_df_hist.columns:
                 display_df_hist['Date/Heure'] = display_df_hist['Date/Heure'].dt.strftime('%Y-%m-%d %H:%M')

            # Display using expanders
            for index, row in display_df_hist.iterrows():
                expander_title = f"Entrée du {row.get('Date/Heure', 'N/A')} (Statut: {row.get('Statut', 'N/A')})"
                with st.expander(expander_title):
                    st.markdown(f"**Statut Objectif:** {row.get('Statut', 'N/A')}")
                    st.markdown(f"**Symptômes Cibles:** {row.get('Symptômes Cibles', 'N/A')}")
                    st.markdown(f"**Interventions Planifiées:** {row.get('Interventions', 'N/A')}")
                    st.markdown("---")
                    st.markdown(f"**Objectifs SMART:**\n{row.get('Objectifs', 'N/A')}")
                    st.markdown(f"**Tâches d'Activation:**\n{row.get('Tâches', 'N/A')}")
                    st.markdown("---")
                    st.markdown(f"**Commentaires Généraux:**\n{row.get('Commentaires', 'N/A')}")