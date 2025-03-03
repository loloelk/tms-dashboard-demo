# services/network_analysis.py
import pandas as pd
import numpy as np
import networkx as nx
import plotly.graph_objects as go
import streamlit as st
from statsmodels.formula.api import mixedlm

@st.cache_data(ttl=3600, show_spinner=False)
def fit_multilevel_model(df, symptom, predictors):
    """
    Fit a multilevel (mixed effects) model for a given symptom.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing symptom data
    symptom : str
        Name of the symptom column to model
    predictors : list
        List of symptom names to use as predictors
        
    Returns:
    --------
    statsmodels.regression.linear_model.RegressionResultsWrapper or None
        Results of the fitted model, or None if fitting fails
    """
    # Shift predictors by one to represent t-1
    for predictor in predictors:
        df[f'{predictor}_lag'] = df[predictor].shift(1)
    
    # Drop rows with NaN values
    df_model = df.dropna()
    
    # If not enough data, return None
    if len(df_model) < 5:
        return None
    
    # Define the formula
    formula = f"{symptom} ~ " + " + ".join([f"{pred}_lag" for pred in predictors])
    
    # Fit the mixed effects model with random intercepts
    try:
        model = mixedlm(formula, df_model, groups=df_model['PatientID'])
        result = model.fit(disp=False)
        return result
    except Exception as e:
        print(f"Erreur lors de l'ajustement du modèle pour {symptom}: {e}")
        return None

def construct_network(coef_matrix, threshold=0.3):
    """
    Construct a symptom network from a coefficient matrix.
    
    Parameters:
    -----------
    coef_matrix : pd.DataFrame
        DataFrame with symptoms as rows and predictors as columns
    threshold : float, optional
        Minimum absolute coefficient to include an edge, by default 0.3
        
    Returns:
    --------
    networkx.DiGraph
        Directed graph representing the symptom network
    """
    G = nx.DiGraph()
    
    for symptom in coef_matrix.index:
        G.add_node(symptom)
        for predictor in coef_matrix.columns:
            coef = coef_matrix.loc[symptom, predictor]
            if pd.notnull(coef) and abs(coef) >= threshold:
                G.add_edge(predictor, symptom, weight=coef)
    
    return G

def plot_network(G, title="Symptom Network"):
    """
    Plot a network diagram using Plotly.
    
    Parameters:
    -----------
    G : networkx.Graph
        Graph to plot
    title : str, optional
        Title for the plot, by default "Symptom Network"
        
    Returns:
    --------
    plotly.graph_objects.Figure
        Plotly figure containing the network visualization
    """
    pos = nx.spring_layout(G, seed=42)  # Fixed layout for consistency

    edge_x = []
    edge_y = []
    edge_text = []
    
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        
        # Add edge weight as hover text
        weight = edge[2].get('weight', 0)
        edge_text.extend([f"{edge[0]} → {edge[1]}: {weight:.2f}", "", ""])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color='#888'),
        hoverinfo='text',
        text=edge_text,
        mode='lines'
    )

    node_x = []
    node_y = []
    node_text = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        # Create descriptive node labels
        connections = len(list(G.successors(node))) + len(list(G.predecessors(node)))
        node_text.append(f"{node}<br>Connexions: {connections}")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        text=[node.replace('madrs_', 'M').replace('anxiety_', 'A') for node in G.nodes()],
        textposition="top center",
        hovertext=node_text,
        hoverinfo='text',
        marker=dict(
            showscale=True,
            colorscale='YlGnBu',
            reversescale=True,
            color=[],  # To be filled based on node attributes
            size=20,
            colorbar=dict(
                thickness=15,
                title='Nombre de Connexions',
                xanchor='left',
                titleside='right'
            ),
            line_width=2
        )
    )

    # Calculate node degrees for coloring
    node_adjacencies = []
    for node in G.nodes():
        node_adjacencies.append(len(list(G.successors(node))) + len(list(G.predecessors(node))))

    node_trace.marker.color = node_adjacencies

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=title,
            titlefont_size=16,
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[dict(text="", showarrow=False, xref="paper", yref="paper")],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )

    # Add a legend explaining the abbreviations
    legend_text = "M = MADRS item, A = Anxiety item"
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.01, y=0.01,
        text=legend_text,
        showarrow=False,
        font=dict(size=12),
        align="left"
    )

    return fig

@st.cache_data(ttl=3600, show_spinner=False)
def generate_person_specific_network(patient_df, patient_id, symptoms, threshold=0.3):
    """
    Generate a person-specific symptom network for a given patient.
    
    Parameters:
    -----------
    patient_df : pd.DataFrame
        DataFrame containing patient symptom data
    patient_id : str
        Unique identifier for the patient
    symptoms : list
        List of symptom names to include in the network
    threshold : float, optional
        Minimum absolute coefficient to include an edge, by default 0.3
        
    Returns:
    --------
    plotly.graph_objects.Figure
        Plotly figure containing the network visualization
    """
    # Sort data by Timestamp
    df_patient = patient_df.sort_values('Timestamp')
    
    # Initialize a DataFrame to store coefficients
    coef_matrix = pd.DataFrame(index=symptoms, columns=symptoms, dtype=float)
    
    # Fit models for each symptom
    for symptom in symptoms:
        predictors = symptoms.copy()
        
        # Remove the current symptom from predictors to avoid self-loops
        if symptom in predictors:
            predictors.remove(symptom)
            
        result = fit_multilevel_model(df_patient, symptom, predictors)
        if result is not None:
            # Extract coefficients for lagged predictors
            coef = result.params.filter(regex='_lag$')
            for predictor in predictors:
                lag_col = f'{predictor}_lag'
                if lag_col in coef.index:
                    coef_value = coef[lag_col]
                    coef_matrix.loc[symptom, predictor] = coef_value
        else:
            coef_matrix.loc[symptom, predictors] = np.nan
    
    # Construct the network
    G = construct_network(coef_matrix, threshold=threshold)
    
    # Plot the network
    fig = plot_network(G, title=f"Réseau de Symptômes pour {patient_id}")
    
    return fig