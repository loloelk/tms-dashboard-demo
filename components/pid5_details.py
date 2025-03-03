# components/pid5_details.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def details_pid5_page():
    """Detailed page for PID-5 assessment visualizations"""
    if not st.session_state.get("selected_patient_id"):
        st.warning("Aucun patient sélectionné.")
        return

    if not any(col.startswith('pid5_') for col in st.session_state.final_data.columns):
        st.info("Les données PID-5 ne sont pas disponibles.")
        return

    patient_row = st.session_state.final_data[st.session_state.final_data["ID"] == st.session_state.selected_patient_id]
    if patient_row.empty:
        st.error("Données du patient non trouvées.")
        return
        
    patient_data = patient_row.iloc[0]

    # Check if PID-5 columns exist
    pid5_columns = []
    for dimension, items in st.session_state.PID5_DIMENSIONS_MAPPING.items():
        pid5_columns += [f'pid5_{item}_bl' for item in items] + [f'pid5_{item}_fu' for item in items]

    if not set(pid5_columns).issubset(st.session_state.final_data.columns):
        st.warning("Données PID-5 incomplètes pour ce patient.")
        return

    # Calculate dimension scores
    dimension_scores_bl = {}
    dimension_scores_fu = {}
    for dimension, items in st.session_state.PID5_DIMENSIONS_MAPPING.items():
        baseline_score = patient_data[[f'pid5_{item}_bl' for item in items]].sum()
        followup_score = patient_data[[f'pid5_{item}_fu' for item in items]].sum()
        dimension_scores_bl[dimension] = baseline_score.sum()
        dimension_scores_fu[dimension] = followup_score.sum()

    # Prepare data for the table
    table_data = []
    for dimension in st.session_state.PID5_DIMENSIONS_MAPPING.keys():
        table_data.append({
            "Domaine": dimension,
            "Total Baseline": f"{dimension_scores_bl[dimension]:,}",
            "Total Jour 30": f"{dimension_scores_fu[dimension]:,}",
            "Variation": f"{dimension_scores_fu[dimension] - dimension_scores_bl[dimension]:+,}"
        })

    pid5_df = pd.DataFrame(table_data)

    st.subheader("Scores PID-5 par Domaine")
    st.dataframe(pid5_df, use_container_width=True)

    # Create the spider (radar) chart
    tab1, tab2 = st.tabs(["Graphique Radar", "Détail des Items"])
    
    with tab1:
        categories = list(st.session_state.PID5_DIMENSIONS_MAPPING.keys())
        values_bl = list(dimension_scores_bl.values())
        values_fu = list(dimension_scores_fu.values())

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
            polar=dict(
                radialaxis=dict(
                    visible=False,
                    range=[0, 15]
                )
            ),
            showlegend=True,
            title="Scores par Dimension PID-5",
            template="plotly_white"
        )
        st.plotly_chart(fig_spider, use_container_width=True)
    
    with tab2:
        # Show item-level detail
        selected_dimension = st.selectbox(
            "Sélectionner une dimension", 
            options=list(st.session_state.PID5_DIMENSIONS_MAPPING.keys())
        )
        
        # Get items for selected dimension
        dimension_items = st.session_state.PID5_DIMENSIONS_MAPPING[selected_dimension]
        
        # Create a DataFrame with item-level scores
        item_data = []
        for item in dimension_items:
            bl_value = patient_data.get(f'pid5_{item}_bl', 0)
            fu_value = patient_data.get(f'pid5_{item}_fu', 0)
            item_data.append({
                "Item": f"Item {item}",
                "Baseline": bl_value,
                "Jour 30": fu_value,
                "Variation": fu_value - bl_value
            })
        
        item_df = pd.DataFrame(item_data)
        
        # Display item table
        st.dataframe(item_df, use_container_width=True)
        
        # Create bar chart for item comparison
        fig_items = go.Figure()
        fig_items.add_trace(go.Bar(
            x=item_df["Item"],
            y=item_df["Baseline"],
            name="Baseline",
            marker_color=st.session_state.PASTEL_COLORS[0]
        ))
        fig_items.add_trace(go.Bar(
            x=item_df["Item"],
            y=item_df["Jour 30"],
            name="Jour 30",
            marker_color=st.session_state.PASTEL_COLORS[1]
        ))
        
        fig_items.update_layout(
            title=f"Scores par Item: {selected_dimension}",
            xaxis_title="Item",
            yaxis_title="Score",
            barmode='group'
        )
        
        st.plotly_chart(fig_items, use_container_width=True)

    # Add interpretation of PID-5 scores
    with st.expander("Interprétation des Scores PID-5"):
        st.markdown("""
        ### Guide d'interprétation des Dimensions PID-5
        
        **Affect Négatif**: Tendance à manifester des émotions négatives fréquentes et intenses.
        
        **Détachement**: Tendance à s'isoler et à éviter les interactions sociales.
        
        **Antagonisme**: Tendance à s'opposer aux autres et à manifester des comportements hostiles.
        
        **Désinhibition**: Tendance à agir de façon impulsive sans considération des conséquences.
        
        **Psychoticisme**: Tendance à manifester des comportements et perceptions étranges ou inhabituels.
        
        Un score plus bas lors du suivi (Jour 30) par rapport à la baseline indique une amélioration dans cette dimension.
        """)