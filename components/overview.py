# components/overview.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def main_dashboard_page():
    """Main overview dashboard with key metrics"""
    st.header("Vue d'Ensemble")
    
    if not hasattr(st.session_state, 'final_data') or st.session_state.final_data.empty:
        st.error("Aucune donnée patient chargée.")
        return
    
    # Top metrics in three columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Count total patients
        total_patients = len(st.session_state.final_data)
        st.metric("Nombre Total de Patients", total_patients)
    
    with col2:
        # Calculate average MADRS improvement
        madrs_df = st.session_state.final_data[
            st.session_state.final_data['madrs_score_bl'].notna() & 
            st.session_state.final_data['madrs_score_fu'].notna()
        ]
        
        if not madrs_df.empty:
            improvement = madrs_df['madrs_score_bl'] - madrs_df['madrs_score_fu']
            avg_improvement = improvement.mean()
            st.metric("Amélioration MADRS Moyenne", f"{avg_improvement:.1f} points")
        else:
            st.metric("Amélioration MADRS Moyenne", "N/A")
    
    with col3:
        # Calculate response rate (>= 50% improvement)
        if not madrs_df.empty:
            percent_improvement = (improvement / madrs_df['madrs_score_bl']) * 100
            response_rate = (percent_improvement >= 50).mean() * 100
            st.metric("Taux de Réponse", f"{response_rate:.1f}%")
        else:
            st.metric("Taux de Réponse", "N/A")
    
    # Create tabs for different overview sections
    tab1, tab2, tab3 = st.tabs([
        "📊 Distribution", 
        "📈 Tendances", 
        "📋 Données Récentes"
    ])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Protocol distribution
            st.subheader("Distribution des Protocoles")
            
            if 'protocol' in st.session_state.final_data.columns:
                # Count patients by protocol
                protocol_counts = st.session_state.final_data['protocol'].value_counts().reset_index()
                protocol_counts.columns = ['Protocole', 'Nombre de Patients']
                
                # Create a pie chart
                fig = px.pie(
                    protocol_counts, 
                    values='Nombre de Patients',
                    names='Protocole',
                    title="Répartition des Patients par Protocole"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("La colonne 'protocol' n'existe pas dans les données.")
        
        with col2:
            # Age distribution
            st.subheader("Distribution des Âges")
            
            if 'age' in st.session_state.final_data.columns:
                fig_age = px.histogram(
                    st.session_state.final_data,
                    x='age',
                    nbins=10,
                    title="Distribution des Âges",
                    labels={'age': 'Âge', 'count': 'Nombre de Patients'},
                    color_discrete_sequence=[st.session_state.PASTEL_COLORS[2]]
                )
                st.plotly_chart(fig_age, use_container_width=True)
            else:
                st.warning("La colonne 'age' n'existe pas dans les données.")
    
    with tab2:
        st.subheader("Évolution des Scores MADRS")
        
        if 'madrs_score_bl' in st.session_state.final_data.columns and 'madrs_score_fu' in st.session_state.final_data.columns:
            # Create a waterfall chart to show overall improvement
            madrs_scores = st.session_state.final_data[['ID', 'madrs_score_bl', 'madrs_score_fu']].dropna()
            
            if not madrs_scores.empty:
                madrs_scores['improvement'] = madrs_scores['madrs_score_bl'] - madrs_scores['madrs_score_fu']
                madrs_scores['improvement_pct'] = (madrs_scores['improvement'] / madrs_scores['madrs_score_bl'] * 100).round(1)
                madrs_scores = madrs_scores.sort_values('improvement_pct', ascending=False)
                
                # Create bar chart
                fig_improvement = px.bar(
                    madrs_scores,
                    x='ID',
                    y='improvement_pct',
                    title="Pourcentage d'amélioration MADRS par patient",
                    labels={'improvement_pct': "Amélioration (%)", 'ID': "Patient ID"},
                    color='improvement_pct',
                    color_continuous_scale='Blues'
                )
                
                # Update layout for better display
                fig_improvement.update_layout(
                    xaxis={'categoryorder': 'total descending'}
                )
                
                st.plotly_chart(fig_improvement, use_container_width=True)
                
                # Add threshold lines for response and remission
                madrs_scores_sorted = madrs_scores.sort_values('ID')
                
                fig_before_after = go.Figure()
                fig_before_after.add_trace(go.Scatter(
                    x=madrs_scores_sorted['ID'],
                    y=madrs_scores_sorted['madrs_score_bl'],
                    mode='lines+markers',
                    name='Baseline',
                    line=dict(color=st.session_state.PASTEL_COLORS[0], width=2)
                ))
                fig_before_after.add_trace(go.Scatter(
                    x=madrs_scores_sorted['ID'],
                    y=madrs_scores_sorted['madrs_score_fu'],
                    mode='lines+markers',
                    name='Jour 30',
                    line=dict(color=st.session_state.PASTEL_COLORS[1], width=2)
                ))
                
                # Add threshold lines
                fig_before_after.add_shape(
                    type="line", line=dict(dash='dash', color='green', width=2),
                    x0=0, x1=1, xref="paper",
                    y0=10, y1=10, yref="y"
                )
                fig_before_after.add_annotation(
                    xref="paper", yref="y",
                    x=0.01, y=10,
                    text="Seuil de rémission (10)",
                    showarrow=False,
                    font=dict(color="green")
                )
                
                fig_before_after.update_layout(
                    title="Scores MADRS avant et après traitement",
                    xaxis_title="Patient ID",
                    yaxis_title="Score MADRS"
                )
                
                st.plotly_chart(fig_before_after, use_container_width=True)
            else:
                st.warning("Données MADRS insuffisantes pour l'analyse.")
        else:
            st.warning("Les colonnes MADRS n'existent pas dans les données.")
    
    with tab3:
        st.subheader("Patients Récemment Ajoutés")
        
        if 'Timestamp' in st.session_state.final_data.columns:
            # Convert to datetime if not already
            if not pd.api.types.is_datetime64_dtype(st.session_state.final_data['Timestamp']):
                st.session_state.final_data['Timestamp'] = pd.to_datetime(
                    st.session_state.final_data['Timestamp'], 
                    errors='coerce'
                )
            
            # Sort by timestamp and get the 5 most recent
            recent_patients = st.session_state.final_data.sort_values(
                'Timestamp', 
                ascending=False
            ).head(5)[['ID', 'Timestamp', 'age', 'protocol']]
            
            if not recent_patients.empty:
                # Format for display
                display_df = recent_patients.copy()
                display_df.columns = ['ID Patient', 'Date d\'ajout', 'Âge', 'Protocole']
                
                # Display the table
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info("Aucun patient avec horodatage valide.")
        else:
            # Alternative: just show the first 5 patients
            st.info("Pas d'horodatage disponible. Affichage des premiers patients:")
            display_df = st.session_state.final_data[['ID', 'age', 'protocol']].head(5)
            display_df.columns = ['ID Patient', 'Âge', 'Protocole']
            st.dataframe(display_df, use_container_width=True)