# components/protocol_analysis.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np # Ensure numpy is imported

def protocol_analysis_page():
    """Page for analyzing treatment protocols"""
    st.header("📊 Analyse des Protocoles TMS")

    # --- Data Check ---
    if 'final_data' not in st.session_state or st.session_state.final_data.empty:
        st.error("❌ Aucune donnée patient chargée. Impossible d'analyser les protocoles.")
        return

    # Check if essential columns exist
    required_cols = ['protocol', 'madrs_score_bl', 'madrs_score_fu']
    if not all(col in st.session_state.final_data.columns for col in required_cols):
        st.error(f"❌ Colonnes requises manquantes dans les données: {', '.join(required_cols)}. Vérifiez le fichier CSV.")
        return

    all_protocols = sorted(st.session_state.final_data['protocol'].dropna().unique().tolist())
    if not all_protocols:
         st.warning("⚠️ Aucune information de protocole trouvée dans les données.")
         return


    # --- Create Tabs ---
    tab_dist, tab_efficacy, tab_compare = st.tabs([
        "👥 Distribution",
        "📈 Efficacité Moyenne",
        "🆚 Comparaison Détaillée"
    ])

    # --- Tab 1: Distribution ---
    with tab_dist:
        st.subheader("Distribution des Patients par Protocole")

        protocol_counts = st.session_state.final_data['protocol'].value_counts().reset_index()
        protocol_counts.columns = ['Protocole', 'Nombre de Patients']

        fig_dist = px.bar(
            protocol_counts, x='Protocole', y='Nombre de Patients',
            color='Protocole', title="Répartition des Patients par Protocole",
            text='Nombre de Patients' # Show count on bars
        )
        fig_dist.update_traces(textposition='outside')
        st.plotly_chart(fig_dist, use_container_width=True)

        st.dataframe(protocol_counts, hide_index=True, use_container_width=True)

        if st.checkbox("Afficher en diagramme circulaire", key="dist_pie_cb"):
            fig_pie = px.pie(
                protocol_counts, values='Nombre de Patients', names='Protocole',
                title="Distribution des Protocoles"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # Prepare data for Efficacy and Comparison tabs (MADRS improvement)
    madrs_df = st.session_state.final_data[required_cols].copy()
    madrs_df.dropna(subset=['madrs_score_bl', 'madrs_score_fu'], inplace=True) # Use only patients with both scores

    if madrs_df.empty:
         st.warning("⚠️ Aucune donnée MADRS complète (baseline et suivi) disponible pour l'analyse d'efficacité.")
         # Prevent errors in subsequent tabs if data is missing
         valid_data_for_analysis = False
    else:
         valid_data_for_analysis = True
         # Calculate improvement only if baseline > 0 to avoid division by zero
         madrs_df['improvement'] = madrs_df['madrs_score_bl'] - madrs_df['madrs_score_fu']
         madrs_df['improvement_pct'] = np.where(
             madrs_df['madrs_score_bl'] > 0,
             (madrs_df['improvement'] / madrs_df['madrs_score_bl'] * 100),
             0 # Assign 0% improvement if baseline is 0
         )
         madrs_df['responder'] = madrs_df['improvement_pct'] >= 50
         madrs_df['remission'] = madrs_df['madrs_score_fu'] < 10


    # --- Tab 2: Efficacy ---
    with tab_efficacy:
        st.subheader("Efficacité Moyenne des Protocoles (Basée sur MADRS)")

        if not valid_data_for_analysis:
             st.warning("Données MADRS insuffisantes pour l'analyse.")
        else:
            # Group by protocol
            protocol_metrics = madrs_df.groupby('protocol').agg(
                 N=('protocol', 'size'),
                 Amelioration_Pts_Moyenne=('improvement', 'mean'),
                 Amelioration_Pct_Moyenne=('improvement_pct', 'mean'),
                 Taux_Reponse_Pct=('responder', lambda x: x.mean() * 100), # Calculate percentage directly
                 Taux_Remission_Pct=('remission', lambda x: x.mean() * 100) # Calculate percentage directly
            ).reset_index()

            # Format columns
            protocol_metrics['Amelioration_Pts_Moyenne'] = protocol_metrics['Amelioration_Pts_Moyenne'].round(1)
            protocol_metrics['Amelioration_Pct_Moyenne'] = protocol_metrics['Amelioration_Pct_Moyenne'].round(1)
            protocol_metrics['Taux_Reponse_Pct'] = protocol_metrics['Taux_Reponse_Pct'].round(1)
            protocol_metrics['Taux_Remission_Pct'] = protocol_metrics['Taux_Remission_Pct'].round(1)

            protocol_metrics.rename(columns={
                 'protocol': 'Protocole',
                 'N': 'Nb Patients (MADRS Complet)',
                 'Amelioration_Pts_Moyenne': 'Amélioration Moyenne (Points)',
                 'Amelioration_Pct_Moyenne': 'Amélioration Moyenne (%)',
                 'Taux_Reponse_Pct': 'Taux Réponse (>50%)',
                 'Taux_Remission_Pct': 'Taux Rémission (<10)'
            }, inplace=True)


            st.dataframe(protocol_metrics, hide_index=True, use_container_width=True)

            # Bar chart for improvement percentage
            fig_imp = px.bar(
                 protocol_metrics, x='Protocole', y='Amélioration Moyenne (%)',
                 color='Protocole', title="Pourcentage d'Amélioration MADRS Moyen par Protocole",
                 text='Amélioration Moyenne (%)'
            )
            fig_imp.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig_imp, use_container_width=True)

            # Grouped bar chart for response and remission rates
            rates_long = pd.melt(
                protocol_metrics,
                id_vars=['Protocole'],
                value_vars=['Taux Réponse (>50%)', 'Taux Rémission (<10)'],
                var_name='Mesure', value_name='Pourcentage'
            )
            fig_rates = px.bar(
                rates_long, x='Protocole', y='Pourcentage', color='Mesure',
                barmode='group', title="Taux de Réponse et Rémission par Protocole",
                text='Pourcentage'
            )
            fig_rates.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_rates.update_layout(yaxis_title="Pourcentage (%)")
            st.plotly_chart(fig_rates, use_container_width=True)


    # --- Tab 3: Detailed Comparison ---
    with tab_compare:
        st.subheader("Comparaison Détaillée des Protocoles")

        if not valid_data_for_analysis:
             st.warning("Données MADRS insuffisantes pour l'analyse détaillée.")
        else:
            # Let user select which protocols to compare
            selected_protocols = st.multiselect(
                "Sélectionner les protocoles à comparer:",
                options=all_protocols,
                default=all_protocols, # Select all by default
                key="protocol_compare_multiselect"
            )

            if not selected_protocols:
                st.warning("Veuillez sélectionner au moins un protocole.")
            else:
                # Filter data for selected protocols
                comparison_df = madrs_df[madrs_df['protocol'].isin(selected_protocols)].copy()

                if comparison_df.empty:
                     st.warning("Aucune donnée pour les protocoles sélectionnés.")
                else:
                    # Let user select which metric to focus on (simplified to Improvement %)
                    st.markdown("#### Comparaison basée sur l'Amélioration MADRS (%)")

                    col_box, col_strip = st.columns(2)
                    with col_box:
                         # Box plot for distribution
                         st.markdown("**Distribution des Améliorations**")
                         fig_box = px.box(
                              comparison_df, x='protocol', y='improvement_pct',
                              color='protocol', title="Distribution (%)",
                              labels={'protocol': 'Protocole', 'improvement_pct': 'Amélioration MADRS (%)'},
                              points="all" # Show individual points
                         )
                         st.plotly_chart(fig_box, use_container_width=True)
                    with col_strip:
                         # Strip plot (alternative view of individual points)
                         st.markdown("**Points Individuels**")
                         fig_strip = px.strip(
                              comparison_df, x='protocol', y='improvement_pct',
                              color='protocol', title="Points Individuels (%)",
                              labels={'protocol': 'Protocole', 'improvement_pct': 'Amélioration MADRS (%)'}
                         )
                         st.plotly_chart(fig_strip, use_container_width=True)


                    # Statistical summary
                    st.markdown("---")
                    st.subheader("Résumé Statistique - Amélioration MADRS (%)")
                    stats_df = comparison_df.groupby('protocol')['improvement_pct'].describe().reset_index()
                    # Rename columns for clarity
                    stats_df.rename(columns={
                         'protocol':'Protocole', 'count':'N', 'mean':'Moyenne (%)', 'std':'Écart-Type',
                         'min':'Min (%)', '25%':'25ème Perc.', '50%':'Médiane (%)', '75%':'75ème Perc.', 'max':'Max (%)'
                    }, inplace=True)
                    # Format numeric columns
                    num_cols = stats_df.columns.drop(['Protocole', 'N'])
                    stats_df[num_cols] = stats_df[num_cols].round(1)
                    st.dataframe(stats_df, hide_index=True, use_container_width=True)

                    # --- Mean Difference Comparison ---
                    st.markdown("---")
                    st.subheader("Comparaison Directe des Moyennes d'Amélioration (%)")

                    if len(selected_protocols) < 2:
                        st.info("Sélectionnez au moins deux protocoles pour voir une comparaison directe.")
                    elif len(selected_protocols) == 2:
                         # Direct comparison for two protocols
                         proto1 = selected_protocols[0]
                         proto2 = selected_protocols[1]
                         mean1 = stats_df.loc[stats_df['Protocole'] == proto1, 'Moyenne (%)'].iloc[0]
                         mean2 = stats_df.loc[stats_df['Protocole'] == proto2, 'Moyenne (%)'].iloc[0]
                         diff = mean1 - mean2

                         st.metric(
                              label=f"Différence Moyenne ({proto1} vs {proto2})",
                              value=f"{diff:.1f}%",
                              help=f"Une valeur positive signifie que {proto1} a une amélioration moyenne supérieure à {proto2} dans cet échantillon."
                         )
                    else:
                         # Matrix comparison for more than two protocols
                         st.write("Différences moyennes entre les protocoles (Ligne - Colonne):")
                         # Pivot table for easy lookup
                         means_pivot = stats_df.set_index('Protocole')['Moyenne (%)']
                         # Create empty matrix
                         diff_matrix = pd.DataFrame(index=selected_protocols, columns=selected_protocols, dtype=float)

                         for p1 in selected_protocols:
                              for p2 in selected_protocols:
                                   if p1 != p2:
                                        mean1 = means_pivot.get(p1, np.nan)
                                        mean2 = means_pivot.get(p2, np.nan)
                                        if not pd.isna(mean1) and not pd.isna(mean2):
                                             diff_matrix.loc[p1, p2] = round(mean1 - mean2, 1)
                                        else:
                                             diff_matrix.loc[p1, p2] = np.nan # Mark as NaN if mean missing
                                   else:
                                        diff_matrix.loc[p1, p2] = 0.0 # Difference with self is 0

                         # Display matrix (using Streamlit's dataframe for better formatting)
                         # ***** CORRECTED LINE *****
                         st.dataframe(diff_matrix.style.format("{:.1f}", na_rep="-").highlight_null(color='lightgray'))
                         # ***** END OF CORRECTION *****
                         st.caption("Les valeurs positives indiquent que le protocole en ligne a une meilleure amélioration moyenne que le protocole en colonne.")

                    st.info("ℹ️ Note: Ces différences sont basées sur les moyennes de cet échantillon simulé. Une analyse statistique plus rigoureuse (tests t, ANOVA) serait nécessaire pour déterminer la significativité statistique dans un contexte réel.")