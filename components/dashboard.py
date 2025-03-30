# components/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # Need graph_objects for radar chart
import base64
import logging
import numpy as np
from services.network_analysis import generate_person_specific_network
from services.nurse_service import get_latest_nurse_inputs, get_nurse_inputs_history, get_side_effects_history

# Helper function to get EMA data (ensure robustness)
def get_patient_ema_data(patient_id):
    """Retrieve and prepare EMA data for a specific patient"""
    if 'simulated_ema_data' not in st.session_state or st.session_state.simulated_ema_data.empty:
        logging.warning("Simulated EMA data not found in session state.")
        return pd.DataFrame()
    if 'PatientID' not in st.session_state.simulated_ema_data.columns:
         logging.error("Column 'PatientID' missing in simulated EMA data.")
         return pd.DataFrame()
    try:
        patient_ema = st.session_state.simulated_ema_data[
            st.session_state.simulated_ema_data['PatientID'] == patient_id
        ].copy()
        if 'Timestamp' in patient_ema.columns:
            patient_ema['Timestamp'] = pd.to_datetime(patient_ema['Timestamp'], errors='coerce')
            patient_ema.dropna(subset=['Timestamp'], inplace=True)
            patient_ema.sort_values(by='Timestamp', inplace=True)
        else:
            logging.warning("'Timestamp' column missing in patient EMA data.")
    except Exception as e:
         logging.error(f"Error processing EMA data for {patient_id}: {e}")
         return pd.DataFrame()
    return patient_ema

def treatment_progress(patient_ema):
    """Display treatment progress tracking based on EMA dates"""
    st.subheader("Suivi de Progression du Traitement (Basé sur EMA)")
    milestones = ['Éval Initiale', 'Semaine 1', 'Semaine 2', 'Semaine 3', 'Semaine 4', 'Fin Traitement']
    assumed_duration_days = 28
    if patient_ema.empty or 'Timestamp' not in patient_ema.columns:
        st.warning("ℹ️ Données EMA ou Timestamps manquants pour suivre la progression.")
        return
    try:
        first_entry = patient_ema['Timestamp'].min()
        last_entry = patient_ema['Timestamp'].max()
        days_elapsed = (last_entry - first_entry).days if pd.notna(first_entry) and pd.notna(last_entry) else 0
    except Exception as e:
         logging.error(f"Error calculating date range from EMA Timestamps: {e}")
         days_elapsed = 0
    progress_percentage = min((days_elapsed / assumed_duration_days) * 100, 100) if assumed_duration_days > 0 else 0
    if days_elapsed <= 1: current_milestone_index = 0
    elif days_elapsed <= 7: current_milestone_index = 1
    elif days_elapsed <= 14: current_milestone_index = 2
    elif days_elapsed <= 21: current_milestone_index = 3
    elif days_elapsed <= assumed_duration_days: current_milestone_index = 4
    else: current_milestone_index = 5
    st.progress(progress_percentage / 100)
    st.write(f"Progression estimée: {progress_percentage:.0f}% ({days_elapsed} jours depuis la première donnée EMA)")
    cols = st.columns(len(milestones))
    for i, (col, milestone) in enumerate(zip(cols, milestones)):
        with col:
            if i < current_milestone_index: st.success(f"✅ {milestone}")
            elif i == current_milestone_index: st.info(f"➡️ {milestone}")
            else: st.markdown(f"<span style='opacity: 0.5;'>⬜ {milestone}</span>", unsafe_allow_html=True)

def patient_dashboard():
    """Main dashboard for individual patient view, using database for notes/effects"""
    st.header("📊 Tableau de Bord du Patient")
    if not st.session_state.get("selected_patient_id"):
        st.warning("⚠️ Aucun patient sélectionné. Veuillez en choisir un dans la barre latérale.")
        return
    patient_id = st.session_state.selected_patient_id
    if 'final_data' not in st.session_state or st.session_state.final_data.empty:
         st.error("❌ Données principales du patient non chargées.")
         return
    try:
         if 'ID' not in st.session_state.final_data.columns:
              st.error("Colonne 'ID' manquante dans les données patient principales.")
              return
         patient_row = st.session_state.final_data[st.session_state.final_data["ID"] == patient_id]
         if patient_row.empty:
             st.error(f"❌ Données non trouvées pour le patient {patient_id}.")
             return
         patient_data = patient_row.iloc[0]
    except Exception as e:
         st.error(f"Erreur récupération données pour {patient_id}: {e}")
         logging.exception(f"Error fetching data for patient {patient_id}")
         return

    patient_ema = get_patient_ema_data(patient_id)

    # --- Define Tabs ---
    tab_overview, tab_assessments, tab_network, tab_progress, tab_plan, tab_side_effects, tab_notes_history = st.tabs([
        "👤 Aperçu", "📈 Évaluations", "🕸️ Réseau Sx", "⏳ Progrès EMA",
        "🎯 Plan de Soins", "🩺 Effets 2nd", "📝 Historique Notes"
    ])

    # --- Tab 1: Patient Overview ---
    with tab_overview:
        # (Overview logic remains the same as before)
        st.header("👤 Aperçu du Patient")
        col1, col2, col3 = st.columns(3)
        with col1:
            sex_numeric = patient_data.get('sexe', 'N/A')
            if str(sex_numeric) == '1': sex = "Femme"
            elif str(sex_numeric) == '2': sex = "Homme"
            else: sex = "Autre/N/A"
            st.metric(label="Sexe", value=sex)
        with col2: st.metric(label="Âge", value=patient_data.get('age', 'N/A'))
        with col3: st.metric(label="Protocole TMS", value=patient_data.get('protocol', 'N/A'))
        with st.expander("🩺 Données Cliniques Détaillées", expanded=False):
             col1_details, col2_details = st.columns(2)
             with col1_details: st.subheader("Comorbidités"); st.write(patient_data.get('comorbidities', 'N/A'))
             with col2_details:
                st.subheader("Historique de Traitement")
                st.write(f"Psychothérapie: {'Oui' if patient_data.get('psychotherapie_bl') == '1' else 'Non'}")
                st.write(f"ECT: {'Oui' if patient_data.get('ect_bl') == '1' else 'Non'}")
                st.write(f"rTMS: {'Oui' if patient_data.get('rtms_bl') == '1' else 'Non'}")
                st.write(f"tDCS: {'Oui' if patient_data.get('tdcs_bl') == '1' else 'Non'}")
        st.markdown("---")
        if st.button("Exporter Données Principales Patient (CSV)"):
             try:
                 patient_main_df = patient_row.to_frame().T; csv = patient_main_df.to_csv(index=False).encode('utf-8')
                 st.download_button(label="Télécharger (CSV)", data=csv, file_name=f"patient_{patient_id}_main_data.csv", mime='text/csv')
             except Exception as e: st.error(f"Erreur export: {e}")

    # --- Tab 2: Clinical Assessments ---
    with tab_assessments:
        st.header("📈 Évaluations Cliniques")
        # --- BFI MODIFICATION START: Add BFI tab ---
        subtab_madrs, subtab_phq9, subtab_bfi = st.tabs(["MADRS", "PHQ-9", "BFI"])
        # --- BFI MODIFICATION END ---

        with subtab_madrs:
            # (MADRS logic remains the same)
            st.subheader("Scores MADRS")
            madrs_bl = pd.to_numeric(patient_data.get("madrs_score_bl"), errors='coerce')
            madrs_fu = pd.to_numeric(patient_data.get("madrs_score_fu"), errors='coerce')
            if pd.isna(madrs_bl): st.warning("Score MADRS Baseline manquant.")
            else:
                # (Detailed MADRS display logic as before...)
                col1_madrs, col2_madrs = st.columns(2)
                with col1_madrs:
                    st.metric(label="MADRS Baseline", value=f"{madrs_bl:.0f}")
                    score = madrs_bl
                    if score <= 6: severity = "Normal"
                    elif score <= 19: severity = "Légère"
                    elif score <= 34: severity = "Modérée"
                    else: severity = "Sévère"
                    st.write(f"**Sévérité Initiale:** {severity}")
                    if not pd.isna(madrs_fu):
                        delta_score = madrs_fu - madrs_bl; st.metric(label="MADRS Jour 30", value=f"{madrs_fu:.0f}", delta=f"{delta_score:.0f} points")
                        if madrs_bl > 0:
                             improvement_pct = ((madrs_bl - madrs_fu) / madrs_bl) * 100; st.metric(label="Amélioration", value=f"{improvement_pct:.1f}%")
                             is_responder = improvement_pct >= 50; is_remitter = madrs_fu < 10
                             st.write(f"**Réponse (>50%):** {'Oui' if is_responder else 'Non'}"); st.write(f"**Rémission (<10):** {'Oui' if is_remitter else 'Non'}")
                        else: st.write("Amélioration (%) non calculable (baseline=0)")
                    else: st.metric(label="MADRS Jour 30", value="N/A")
                    madrs_total_df = pd.DataFrame({ 'Temps': ['Baseline', 'Jour 30'],'Score': [madrs_bl, madrs_fu if not pd.isna(madrs_fu) else np.nan]})
                    fig_madrs_total = px.bar( madrs_total_df.dropna(subset=['Score']), x='Temps', y='Score', title="Score Total MADRS", color='Temps', color_discrete_sequence=st.session_state.PASTEL_COLORS[:2], labels={"Score": "Score MADRS Total"})
                    st.plotly_chart(fig_madrs_total, use_container_width=True)
                with col2_madrs:
                    st.subheader("Scores par Item MADRS")
                    items_data = []; valid_items_found = False
                    for i in range(1, 11):
                         bl_col = f'madrs_{i}_bl'; fu_col = f'madrs_{i}_fu'; item_label = st.session_state.MADRS_ITEMS_MAPPING.get(str(i), f"Item {i}")
                         bl_val = pd.to_numeric(patient_data.get(bl_col), errors='coerce'); fu_val = pd.to_numeric(patient_data.get(fu_col), errors='coerce')
                         if not pd.isna(bl_val) or not pd.isna(fu_val): valid_items_found = True
                         items_data.append({'Item': item_label, 'Baseline': bl_val, 'Jour 30': fu_val })
                    if not valid_items_found: st.warning("Scores par item MADRS non disponibles.")
                    else:
                        madrs_items_df = pd.DataFrame(items_data)
                        madrs_items_df['Baseline'] = pd.to_numeric(madrs_items_df['Baseline'], errors='coerce'); madrs_items_df['Jour 30'] = pd.to_numeric(madrs_items_df['Jour 30'], errors='coerce')
                        madrs_items_long = madrs_items_df.melt(id_vars='Item', var_name='Temps', value_name='Score').dropna(subset=['Score'])
                        fig_items = px.bar( madrs_items_long, x='Item', y='Score', color='Temps', barmode='group', title="Scores par Item MADRS", template="plotly_white", color_discrete_sequence=st.session_state.PASTEL_COLORS[:2], labels={"Score": "Score (0-6)"})
                        fig_items.update_xaxes(tickangle=-45); fig_items.update_yaxes(range=[0,6])
                        st.plotly_chart(fig_items, use_container_width=True)
                st.markdown("---"); st.subheader("Comparaison avec d'autres patients")
                # ... (MADRS Comparison logic remains the same) ...

        with subtab_phq9:
            # (PHQ-9 logic remains the same)
            st.subheader("Progression PHQ-9 (Scores Quotidiens)")
            phq9_days = [5, 10, 15, 20, 25, 30]; phq9_scores_over_time = {}; phq9_cols_exist = True
            for day in phq9_days:
                 item_columns = [f'phq9_day{day}_item{item}' for item in range(1, 10)]
                 if not all(col in patient_data.index for col in item_columns): phq9_cols_exist = False; break
                 daily_score = pd.to_numeric(patient_data.get(item_columns), errors='coerce').fillna(0).sum()
                 phq9_scores_over_time[f'Jour {day}'] = daily_score
            if phq9_cols_exist and phq9_scores_over_time:
                 phq9_df = pd.DataFrame(list(phq9_scores_over_time.items()), columns=["Jour", "Score"])
                 fig_phq9 = px.line( phq9_df, x="Jour", y="Score", markers=True, title="Progression PHQ-9", template="plotly_white", labels={'Score': 'Score PHQ-9 Total'}, color_discrete_sequence=[st.session_state.PASTEL_COLORS[0]])
                 fig_phq9.update_layout(yaxis_range=[0, 27]); st.plotly_chart(fig_phq9, use_container_width=True)
            else: st.info("ℹ️ Données PHQ-9 journalières non disponibles.")

        # --- BFI MODIFICATION START: Add BFI tab logic ---
        with subtab_bfi:
            st.subheader("Inventaire BFI (Big Five)")

            # Define BFI factors and corresponding column prefixes
            bfi_factors_map = {
                'Ouverture': 'bfi_O',
                'Conscienciosité': 'bfi_C',
                'Extraversion': 'bfi_E',
                'Agréabilité': 'bfi_A',
                'Névrosisme': 'bfi_N'
            }
            categories = list(bfi_factors_map.keys())
            values_bl = []
            values_fu = []
            bfi_data_available = False

            # Check if data exists and extract scores
            if f"{list(bfi_factors_map.values())[0]}_bl" in patient_data.index: # Check if first factor exists
                bfi_data_available = True
                for factor_name, col_prefix in bfi_factors_map.items():
                    bl_score = pd.to_numeric(patient_data.get(f"{col_prefix}_bl"), errors='coerce')
                    fu_score = pd.to_numeric(patient_data.get(f"{col_prefix}_fu"), errors='coerce')
                    values_bl.append(bl_score if pd.notna(bl_score) else 0) # Use 0 for missing in plot
                    values_fu.append(fu_score if pd.notna(fu_score) else 0) # Use 0 for missing in plot
            else:
                st.info("ℹ️ Données BFI non disponibles pour ce patient.")

            if bfi_data_available:
                try:
                    fig_bfi_radar = go.Figure()

                    # Add Baseline trace
                    fig_bfi_radar.add_trace(go.Scatterpolar(
                        r=values_bl + [values_bl[0]], # Close the loop
                        theta=categories + [categories[0]], # Close the loop
                        fill='toself',
                        name='Baseline',
                        line_color=st.session_state.PASTEL_COLORS[0] # Example color
                    ))

                    # Add Follow-up trace
                    fig_bfi_radar.add_trace(go.Scatterpolar(
                        r=values_fu + [values_fu[0]], # Close the loop
                        theta=categories + [categories[0]], # Close the loop
                        fill='toself',
                        name='Jour 30',
                        line_color=st.session_state.PASTEL_COLORS[1] # Example color
                    ))

                    fig_bfi_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[1, 5] # BFI factor scores typically average 1-5
                            )),
                        showlegend=True,
                        title="Scores BFI (Baseline vs Jour 30)",
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_bfi_radar, use_container_width=True)

                    # Optionally display the table again
                    with st.expander("Voir les scores BFI détaillés"):
                         bfi_table_data = {'Facteur': categories, 'Baseline': values_bl, 'Jour 30': values_fu}
                         bfi_table_df = pd.DataFrame(bfi_table_data)
                         st.dataframe(bfi_table_df.round(2), hide_index=True, use_container_width=True)

                except Exception as e:
                    st.error(f"Erreur lors de la création du graphique radar BFI : {e}")
                    logging.exception(f"Error creating BFI radar chart for {patient_id}")
        # --- BFI MODIFICATION END ---

    # --- Tab 3: Symptom Network ---
    # (Remains the same)
    with tab_network:
        # ... (Network logic as before) ...
        st.header("🕸️ Réseau de Symptômes (Basé sur EMA)")
        if patient_ema.empty: st.warning("⚠️ Aucune donnée EMA dispo pour générer le réseau.")
        elif len(patient_ema) < 10: st.warning(f"⚠️ Pas assez de données EMA ({len(patient_ema)}) pour analyse fiable.")
        else:
            st.info("Influence potentielle des symptômes EMA au fil du temps.")
            threshold = st.slider( "Seuil connexions", 0.05, 0.5, 0.15, 0.05, key="network_thresh")
            if st.button("🔄 Générer/Actualiser Réseau"):
                 try:
                      if 'SYMPTOMS' not in st.session_state: st.error("Erreur: Liste symptômes EMA non définie.")
                      else:
                            symptoms_available = [s for s in st.session_state.SYMPTOMS if s in patient_ema.columns]
                            if not symptoms_available: st.error("❌ Aucune colonne symptôme valide trouvée.")
                            else:
                                fig_network = generate_person_specific_network( patient_ema, patient_id, symptoms_available, threshold=threshold)
                                st.plotly_chart(fig_network, use_container_width=True)
                                with st.expander("💡 Interprétation"): st.markdown("""... (interpretation text) ...""")
                 except Exception as e: st.error(f"❌ Erreur génération réseau: {e}"); logging.exception(f"Network gen failed {patient_id}")
            else: st.info("Cliquez sur bouton pour générer.")


    # --- Tab 4: EMA Progression ---
    # (Remains the same)
    with tab_progress:
        # ... (EMA Progress logic as before) ...
        st.header("⏳ Progression (Basé sur EMA)")
        treatment_progress(patient_ema)
        st.markdown("---")
        if patient_ema.empty: st.info("ℹ️ Aucune donnée EMA dispo.")
        elif 'Day' not in patient_ema.columns: st.warning("Colonne 'Day' manquante.")
        else:
            patient_ema['Day'] = pd.to_numeric(patient_ema['Day'], errors='coerce').dropna().astype(int)
            st.subheader("📉 Évolution Moyenne Quotidienne")
            if 'SYMPTOMS' not in st.session_state: st.error("Erreur: Liste symptômes EMA non définie."); available_categories={}; daily_symptoms=pd.DataFrame()
            else:
                symptoms_present = [s for s in st.session_state.SYMPTOMS if s in patient_ema.columns]
                daily_symptoms = pd.DataFrame()
                if not symptoms_present: st.warning("Aucune colonne symptôme EMA connue.")
                else:
                     numeric_cols = patient_ema[symptoms_present].select_dtypes(include=np.number).columns.tolist()
                     if not numeric_cols: st.warning("Aucune colonne symptôme EMA numérique.")
                     else:
                        try: daily_symptoms = patient_ema.groupby('Day')[numeric_cols].mean().reset_index()
                        except Exception as e: st.error(f"Erreur moyennes: {e}"); logging.exception(f"Error daily means {patient_id}")
                     if not daily_symptoms.empty:
                         symptom_categories = {"MADRS Items": [s for s in st.session_state.MADRS_ITEMS if s in numeric_cols],"Anxiety Items": [s for s in st.session_state.ANXIETY_ITEMS if s in numeric_cols],"Autres": [s for s in [st.session_state.SLEEP, st.session_state.ENERGY, st.session_state.STRESS] if s in numeric_cols]}
                         available_categories = {k: v for k, v in symptom_categories.items() if v}
                         if not available_categories: st.warning("Aucune catégorie EMA.")
                         else:
                              selected_category_avg = st.selectbox( "Afficher tendance:", list(available_categories.keys()), key="ema_cat_avg")
                              selected_symptoms_avg = available_categories[selected_category_avg]
                              fig_ema_trends = px.line( daily_symptoms, x="Day", y=selected_symptoms_avg, markers=True, title=f"Tendance: {selected_category_avg}", template="plotly_white", labels={"value": "Score Moyen", "variable": "Symptôme"})
                              st.plotly_chart(fig_ema_trends, use_container_width=True)
                     else: st.info("Aucune donnée moyenne.")
            st.markdown("---"); st.subheader("📈 Variabilité Quotidienne"); st.info("Fluctuation (écart-type glissant).")
            if not daily_symptoms.empty and available_categories:
                 rolling_window = st.slider("Fenêtre variabilité (j)", 3, 14, 7, key="ema_var_win")
                 if len(daily_symptoms) < rolling_window: st.warning(f"Pas assez de jours ({len(daily_symptoms)}).")
                 else:
                     selected_category_var = st.selectbox( "Afficher variabilité:", list(available_categories.keys()), key="ema_cat_var")
                     selected_symptoms_var = available_categories[selected_category_var]
                     try:
                         variability_df = daily_symptoms[['Day'] + selected_symptoms_var].copy()
                         for symptom in selected_symptoms_var: variability_df[symptom] = variability_df[symptom].rolling(window=rolling_window, min_periods=max(2, rolling_window // 2)).std()
                         variability_df.dropna(inplace=True)
                         if not variability_df.empty:
                             fig_ema_variability = px.line( variability_df, x='Day', y=selected_symptoms_var, markers=False, title=f"Variabilité ({rolling_window}j): {selected_category_var}", template="plotly_white", labels={"value": f"Écart-Type ({rolling_window}j)", "variable": "Symptôme"})
                             fig_ema_variability.update_layout(yaxis_range=[0, None])
                             st.plotly_chart(fig_ema_variability, use_container_width=True)
                         else: st.info(f"Pas assez de données post-fenêtre: {selected_category_var}")
                     except Exception as e: st.error(f"Erreur variabilité: {e}"); logging.exception(f"Error variability {patient_id}")
            else: st.info("Données moyennes non dispo.")
            st.markdown("---")
            if st.checkbox("Afficher heatmap corrélations EMA", key="show_ema_corr"):
                st.subheader("↔️ Corrélations Symptômes EMA")
                if available_categories:
                     selected_category_corr = st.selectbox( "Calculer corrélations:", list(available_categories.keys()), key="ema_cat_corr")
                     selected_symptoms_corr = available_categories.get(selected_category_corr, [])
                     if selected_symptoms_corr:
                          numeric_ema_cols = patient_ema[selected_symptoms_corr].select_dtypes(include=np.number).columns.tolist()
                          if len(numeric_ema_cols) < 2: st.warning("Pas assez de symptômes num.")
                          else:
                              try:
                                   corr_matrix = patient_ema[numeric_ema_cols].corr()
                                   fig_heatmap = px.imshow( corr_matrix, text_auto=".2f", aspect="auto", color_continuous_scale="Blues", title=f"Corrélations: {selected_category_corr.lower()} (EMA)")
                                   st.plotly_chart(fig_heatmap, use_container_width=True)
                              except Exception as e: st.error(f"Erreur heatmap: {e}"); logging.exception(f"Error heatmap {patient_id}")
                     else: st.warning("Aucun symptôme sélectionné.")
                else: st.warning("Aucune catégorie disponible.")


    # --- Tab 5: Treatment Plan (Latest) ---
    # (Remains the same)
    with tab_plan:
        # ... (Treatment Plan logic as before) ...
        st.header("🎯 Plan de Soins Actuel")
        st.info("Affiche la **dernière** entrée. Pour ajouter/modifier, allez à 'Plan de Soins et Entrées Infirmières'.")
        try:
             latest_plan = get_latest_nurse_inputs(patient_id)
             if latest_plan and latest_plan.get('timestamp'):
                 plan_date = pd.to_datetime(latest_plan.get('timestamp')).strftime('%Y-%m-%d %H:%M'); created_by = latest_plan.get('created_by', 'N/A')
                 st.subheader(f"Dernière MàJ: {plan_date} (par {created_by})")
                 col_stat, col_symp, col_int = st.columns([1,2,2])
                 with col_stat: st.metric("Statut Objectif", latest_plan.get('goal_status', 'N/A'))
                 with col_symp: st.markdown(f"**Sympt. Cibles:**\n> {latest_plan.get('target_symptoms', 'N/A')}")
                 with col_int: st.markdown(f"**Interv. Planifiées:**\n> {latest_plan.get('planned_interventions', 'N/A')}")
                 st.markdown("---"); st.markdown(f"**Objectifs:**\n_{latest_plan.get('objectives', 'N/A')}_"); st.markdown(f"**Tâches:**\n_{latest_plan.get('tasks', 'N/A')}_"); st.markdown(f"**Commentaires:**\n_{latest_plan.get('comments', 'N/A')}_")
             elif latest_plan: st.warning("Dernier plan trouvé mais date inconnue.")
             else: st.warning(f"ℹ️ Aucun plan trouvé pour {patient_id}.")
        except Exception as e: st.error(f"Erreur chargement plan: {e}"); logging.exception(f"Error loading care plan {patient_id}")


    # --- Tab 6: Side Effects (Summary) ---
    # (Remains the same)
    with tab_side_effects:
        # ... (Side Effects Summary logic as before) ...
         st.header("🩺 Suivi Effets Secondaires (Résumé)")
         st.info("💡 Résumé. Pour détails/ajout, voir page dédiée.")
         try:
             side_effects_history = get_side_effects_history(patient_id)
             if not side_effects_history.empty:
                 st.subheader("Effets Signalés (Fréq. & Max Sév.)")
                 severity_cols = ['headache', 'nausea', 'scalp_discomfort', 'dizziness']; summary_list = []
                 for col in severity_cols:
                      if col in side_effects_history.columns:
                           numeric_col = pd.to_numeric(side_effects_history[col], errors='coerce').fillna(0)
                           count = (numeric_col > 0).sum()
                           if count > 0: max_sev = numeric_col.max(); summary_list.append(f"{col.replace('_', ' ').capitalize()}: {count}x (max {max_sev:.0f}/10)")
                 if summary_list: st.markdown("- " + "\n- ".join(summary_list))
                 else: st.info("Aucun ES (> 0) signalé.")
                 latest_report = side_effects_history.iloc[0]; latest_note = latest_report.get('notes', ''); latest_other = latest_report.get('other_effects', '')
                 report_date = pd.to_datetime(latest_report['report_date']).strftime('%Y-%m-%d') if 'report_date' in latest_report and pd.notna(latest_report['report_date']) else "Inconnue"
                 if latest_note or latest_other:
                      with st.expander(f"Détails Dernier Rapport ({report_date})"):
                           if latest_other: st.write(f"**Autres:** {latest_other}")
                           if latest_note: st.write(f"**Notes:** {latest_note}")
             else: st.info(f"ℹ️ Aucun rapport ES trouvé pour {patient_id}.")
         except Exception as e: st.error(f"Erreur chargement résumé ES: {e}"); logging.exception(f"Error loading SE summary {patient_id}")

    # --- Tab 7: Nurse Notes History ---
    # (Remains the same)
    with tab_notes_history:
        # ... (Nurse Notes History logic as before) ...
         st.header("📝 Historique Notes Infirmières")
         st.info("Affiche notes/plans précédents.")
         try:
            notes_history_df = get_nurse_inputs_history(patient_id)
            if notes_history_df.empty: st.info(f"ℹ️ Aucune note historique pour {patient_id}.")
            else:
                st.info(f"Affichage {len(notes_history_df)} entrées.")
                display_columns = ['timestamp', 'goal_status', 'objectives', 'tasks', 'target_symptoms', 'planned_interventions', 'comments', 'created_by']
                display_columns = [col for col in display_columns if col in notes_history_df.columns]
                display_df_hist = notes_history_df[display_columns].copy()
                rename_map = { 'timestamp': 'Date/Heure', 'goal_status': 'Statut', 'objectives': 'Objectifs', 'tasks': 'Tâches','target_symptoms': 'Sympt. Cibles', 'planned_interventions': 'Interventions', 'comments': 'Comm.', 'created_by': 'Auteur' }
                display_df_hist.rename(columns={k: v for k, v in rename_map.items() if k in display_df_hist.columns}, inplace=True)
                if 'Date/Heure' in display_df_hist.columns: display_df_hist['Date/Heure'] = pd.to_datetime(display_df_hist['Date/Heure'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
                for index, row in display_df_hist.iterrows():
                    exp_title = f"Entrée {row.get('Date/Heure', 'N/A')} (Statut: {row.get('Statut', 'N/A')})"
                    author = row.get('Auteur', None);
                    if pd.notna(author) and author: exp_title += f" - {author}"
                    with st.expander(exp_title):
                        st.markdown(f"**Statut:** {row.get('Statut', 'N/A')} | **Sympt Cibles:** {row.get('Sympt. Cibles', 'N/A')} | **Interv:** {row.get('Interventions', 'N/A')}")
                        st.markdown(f"**Objectifs:**\n{row.get('Objectifs', 'N/A')}"); st.markdown(f"**Tâches:**\n{row.get('Tâches', 'N/A')}"); st.markdown(f"**Comm:**\n{row.get('Comm.', 'N/A')}")
         except Exception as e: st.error(f"Erreur historique notes: {e}"); logging.exception(f"Error loading notes history {patient_id}")