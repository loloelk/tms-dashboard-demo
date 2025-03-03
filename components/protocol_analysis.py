# components/protocol_analysis.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

def protocol_analysis_page():
    """Page for analyzing treatment protocols"""
    st.header("Analyse des Protocoles")
    
    if not hasattr(st.session_state, 'final_data') or st.session_state.final_data.empty:
        st.error("Aucune donnée patient chargée.")
        return
    
    # Check if protocol column exists
    if 'protocol' not in st.session_state.final_data.columns:
        st.error("La colonne 'protocol' n'existe pas dans les données.")
        return
    
    # Create tabs for different analyses
    tab1, tab2, tab3 = st.tabs([
        "📊 Distribution", 
        "📈 Efficacité", 
        "📋 Comparaison Détaillée"
    ])
    
    with tab1:
        st.subheader("Distribution des Patients par Protocole")
        
        # Count patients by protocol
        protocol_counts = st.session_state.final_data['protocol'].value_counts().reset_index()
        protocol_counts.columns = ['Protocole', 'Nombre de Patients']
        
        # Create a bar chart
        fig = px.bar(
            protocol_counts, 
            x='Protocole', 
            y='Nombre de Patients',
            color='Protocole',
            title="Répartition des Patients par Protocole"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Show as a table too
        st.dataframe(protocol_counts, use_container_width=True)
        
        # Add pie chart option
        if st.checkbox("Afficher en diagramme circulaire"):
            fig_pie = px.pie(
                protocol_counts,
                values='Nombre de Patients',
                names='Protocole',
                title="Distribution des Protocoles"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with tab2:
        st.subheader("Efficacité des Protocoles")
        
        # Filter for patients with both baseline and follow-up MADRS scores
        madrs_df = st.session_state.final_data[
            st.session_state.final_data['madrs_score_bl'].notna() & 
            st.session_state.final_data['madrs_score_fu'].notna()
        ].copy()
        
        if madrs_df.empty:
            st.warning("Données MADRS insuffisantes pour l'analyse.")
            return
        
        # Calculate improvement
        madrs_df['improvement'] = madrs_df['madrs_score_bl'] - madrs_df['madrs_score_fu']
        madrs_df['improvement_pct'] = (madrs_df['improvement'] / madrs_df['madrs_score_bl'] * 100).round(1)
        
        # Group by protocol
        protocol_improvement = madrs_df.groupby('protocol')[['improvement', 'improvement_pct']].mean().reset_index()
        protocol_improvement.columns = ['Protocole', 'Amélioration Moyenne (points)', 'Amélioration Moyenne (%)']
        
        # Display as a table
        st.dataframe(protocol_improvement, use_container_width=True)
        
        # Create a bar chart for improvement percentage
        fig = px.bar(
            protocol_improvement, 
            x='Protocole', 
            y='Amélioration Moyenne (%)',
            color='Protocole',
            title="Pourcentage d'Amélioration MADRS par Protocole"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Calculate response and remission rates by protocol
        madrs_df['responder'] = madrs_df['improvement_pct'] >= 50
        madrs_df['remission'] = madrs_df['madrs_score_fu'] < 10
        
        response_rates = madrs_df.groupby('protocol')[['responder', 'remission']].mean().reset_index()
        response_rates['responder'] = (response_rates['responder'] * 100).round(1)
        response_rates['remission'] = (response_rates['remission'] * 100).round(1)
        response_rates.columns = ['Protocole', 'Taux de Réponse (%)', 'Taux de Rémission (%)']
        
        st.subheader("Taux de Réponse et Rémission par Protocole")
        st.dataframe(response_rates, use_container_width=True)
        
        # Grouped bar chart for response and remission
        response_long = pd.melt(
            response_rates, 
            id_vars=['Protocole'], 
            value_vars=['Taux de Réponse (%)', 'Taux de Rémission (%)'],
            var_name='Mesure', 
            value_name='Pourcentage'
        )
        
        fig_rates = px.bar(
            response_long,
            x='Protocole',
            y='Pourcentage',
            color='Mesure',
            barmode='group',
            title="Taux de Réponse et Rémission par Protocole"
        )
        st.plotly_chart(fig_rates, use_container_width=True)
    
    with tab3:
        st.subheader("Comparaison Détaillée des Protocoles")
        
        # Let user select which protocols to compare
        protocols = st.session_state.final_data['protocol'].unique().tolist()
        selected_protocols = st.multiselect(
            "Sélectionner les protocoles à comparer", 
            options=protocols,
            default=protocols
        )
        
        if not selected_protocols:
            st.warning("Veuillez sélectionner au moins un protocole.")
            return
            
        # Filter data for selected protocols
        filtered_data = st.session_state.final_data[
            st.session_state.final_data['protocol'].isin(selected_protocols)
        ]
        
        # Let user select which metrics to compare
        metrics = {
            "MADRS": ['madrs_score_bl', 'madrs_score_fu'],
            "PHQ-9": ['phq9_score_bl', 'phq9_score_fu'],
            "PID-5": ['pid5_score_bl', 'pid5_score_fu'],
            "CGI": ['cgi_score_bl', 'cgi_score_fu']
        }
        
        selected_metric = st.selectbox(
            "Sélectionner la métrique à comparer", 
            options=list(metrics.keys())
        )
        
        # Get the columns for the selected metric
        selected_columns = metrics[selected_metric]
        
        # Check if columns exist
        if not all(col in filtered_data.columns for col in selected_columns):
            st.warning(f"Données {selected_metric} incomplètes.")
            return
            
        # Create a copy to avoid modifying the original
        comparison_df = filtered_data[['ID', 'protocol'] + selected_columns].copy()
        
        # Calculate improvement
        baseline_col = selected_columns[0]
        followup_col = selected_columns[1]
        comparison_df['improvement'] = comparison_df[baseline_col] - comparison_df[followup_col]
        comparison_df['improvement_pct'] = (comparison_df['improvement'] / comparison_df[baseline_col] * 100).round(1)
        
        # Group by protocol for boxplot
        if st.checkbox("Afficher les distributions"):
            st.subheader(f"Distribution des valeurs {selected_metric} par Protocole")
            
            # Create a box plot
            fig_box = px.box(
                comparison_df,
                x='protocol',
                y='improvement_pct',
                color='protocol',
                title=f"Distribution des Améliorations {selected_metric} (%)"
            )
            st.plotly_chart(fig_box, use_container_width=True)
            
            # Add individual points
            fig_scatter = px.strip(
                comparison_df,
                x='protocol',
                y='improvement_pct',
                color='protocol',
                title=f"Points Individuels d'Amélioration {selected_metric} (%)"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Statistical summary with enhanced explanation
        st.subheader("Résumé Statistique")
        stats_df = comparison_df.groupby('protocol')['improvement_pct'].describe().reset_index()
        stats_df.columns = ['Protocole', 'Nombre', 'Moyenne (%)', 'Écart-Type', 'Min (%)', '25%', '50%', '75%', 'Max (%)']
        
        # Format columns for better readability
        for col in ['Moyenne (%)', 'Écart-Type', 'Min (%)', '25%', '50%', '75%', 'Max (%)']:
            stats_df[col] = stats_df[col].round(1)
        
        # Display the dataframe
        st.dataframe(stats_df, use_container_width=True)
        
        # Add detailed explanation of the statistical table
        st.markdown("""
        ### Explication du Résumé Statistique

        Ce tableau présente les mesures statistiques de l'amélioration en pourcentage pour chaque protocole :

        - **Protocole** : Le type de traitement rTMS appliqué
        - **Nombre** : Le nombre de patients ayant reçu ce protocole
        - **Moyenne (%)** : Le pourcentage d'amélioration moyen des scores MADRS
        - **Écart-Type** : La dispersion des réponses au traitement (plus élevé = plus de variabilité)
        - **Min (%)** : L'amélioration minimum observée parmi les patients
        - **25%** : Le premier quartile (25% des patients ont une amélioration inférieure à cette valeur)
        - **50%** : La médiane (50% des patients ont une amélioration inférieure à cette valeur)
        - **75%** : Le troisième quartile (75% des patients ont une amélioration inférieure à cette valeur)
        - **Max (%)** : L'amélioration maximum observée parmi les patients

        Un pourcentage d'amélioration plus élevé indique une meilleure réponse au traitement. Une réponse est définie comme une amélioration ≥ 50%, et une rémission comme un score final < 10.
        """)
        
        # Add statistical test information for researchers
        with st.expander("Information sur les Tests Statistiques"):
            st.markdown("""
            ### Tests Statistiques pour Comparer les Protocoles
            
            Pour comparer statistiquement l'efficacité de différents protocoles, les tests suivants sont recommandés:
            
            1. **ANOVA** (ANalysis Of VAriance) : Pour comparer simultanément les moyennes de plus de deux groupes
            2. **Test t de Student** : Pour comparer les moyennes de deux groupes indépendants
            3. **Tests non-paramétriques** (Kruskal-Wallis ou Mann-Whitney) : Si les données ne suivent pas une distribution normale
            
            Pour une analyse statistique plus approfondie, exportez les données et utilisez un logiciel statistique spécialisé comme R ou SPSS.
            """)
            
            # Simple statistical comparison between protocols
            if len(selected_protocols) > 1:
                st.subheader("Comparaison rapide")
                
                # For two protocols, perform t-test (simplified)
                if len(selected_protocols) == 2:
                    group1 = comparison_df[comparison_df['protocol'] == selected_protocols[0]]['improvement_pct']
                    group2 = comparison_df[comparison_df['protocol'] == selected_protocols[1]]['improvement_pct']
                    
                    # Calculate mean difference and convert to percentage
                    mean_diff = group1.mean() - group2.mean()
                    
                    st.write(f"Différence moyenne entre {selected_protocols[0]} et {selected_protocols[1]}: {mean_diff:.1f}%")
                    
                    if abs(mean_diff) > 10:
                        st.write("Cette différence peut être cliniquement significative.")
                    else:
                        st.write("Cette différence peut ne pas être cliniquement significative.")
                
                # For more than two, show all pairwise differences
                else:
                    st.write("Différences moyennes entre les protocoles:")
                    
                    # Create a matrix of differences
                    protocols = selected_protocols
                    diff_matrix = pd.DataFrame(index=protocols, columns=protocols)
                    
                    for p1 in protocols:
                        for p2 in protocols:
                            if p1 != p2:
                                group1 = comparison_df[comparison_df['protocol'] == p1]['improvement_pct']
                                group2 = comparison_df[comparison_df['protocol'] == p2]['improvement_pct']
                                diff_matrix.loc[p1, p2] = round(group1.mean() - group2.mean(), 1)
                            else:
                                diff_matrix.loc[p1, p2] = 0.0
                                
                    st.dataframe(diff_matrix)
                    
                    st.write("Les valeurs positives indiquent que le protocole en ligne a une meilleure amélioration moyenne que le protocole en colonne.")