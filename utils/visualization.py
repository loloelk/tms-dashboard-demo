# utils/visualization.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def create_bar_chart(data, x_column, y_column, title, color_column=None, barmode='group'):
    """
    Create a bar chart using Plotly Express.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Data to plot
    x_column : str
        Column to use for x-axis
    y_column : str or list
        Column(s) to use for y-axis
    title : str
        Chart title
    color_column : str, optional
        Column to use for color, by default None
    barmode : str, optional
        Bar mode ('group', 'stack', etc.), by default 'group'
        
    Returns:
    --------
    plotly.graph_objects.Figure
        Plotly figure containing the bar chart
    """
    fig = px.bar(
        data,
        x=x_column,
        y=y_column,
        color=color_column,
        title=title,
        barmode=barmode
    )
    
    # Update layout for better appearance
    fig.update_layout(
        xaxis_title=x_column,
        yaxis_title=y_column if isinstance(y_column, str) else "Value",
        legend_title_text=color_column if color_column else None
    )
    
    return fig

def create_line_chart(data, x_column, y_column, title, color_column=None, markers=True):
    """
    Create a line chart using Plotly Express.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Data to plot
    x_column : str
        Column to use for x-axis
    y_column : str or list
        Column(s) to use for y-axis
    title : str
        Chart title
    color_column : str, optional
        Column to use for color, by default None
    markers : bool, optional
        Whether to show markers, by default True
        
    Returns:
    --------
    plotly.graph_objects.Figure
        Plotly figure containing the line chart
    """
    fig = px.line(
        data,
        x=x_column,
        y=y_column,
        color=color_column,
        title=title,
        markers=markers
    )
    
    # Update layout for better appearance
    fig.update_layout(
        xaxis_title=x_column,
        yaxis_title=y_column if isinstance(y_column, str) else "Value",
        legend_title_text=color_column if color_column else None
    )
    
    return fig

def create_radar_chart(categories, datasets, title):
    """
    Create a radar chart using Plotly Graph Objects.
    
    Parameters:
    -----------
    categories : list
        List of category names
    datasets : list of dict
        List of dictionaries with 'name', 'values', and 'color' keys
    title : str
        Chart title
        
    Returns:
    --------
    plotly.graph_objects.Figure
        Plotly figure containing the radar chart
    """
    # Create a copy of categories and close the loop
    cat_closed = categories.copy()
    cat_closed.append(categories[0])
    
    fig = go.Figure()
    
    for dataset in datasets:
        # Close the loop for values too
        values_closed = dataset['values'].copy()
        values_closed.append(dataset['values'][0])
        
        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=cat_closed,
            fill='toself',
            name=dataset['name'],
            line_color=dataset['color']
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max([max(d['values']) for d in datasets]) * 1.1]
            )
        ),
        showlegend=True,
        title=title
    )
    
    return fig

def create_heatmap(data, title, colorscale='Blues', text_auto='.2f'):
    """
    Create a heatmap using Plotly Express.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Data to plot as a matrix
    title : str
        Chart title
    colorscale : str, optional
        Color scale to use, by default 'Blues'
    text_auto : str, optional
        Format for text values, by default '.2f'
        
    Returns:
    --------
    plotly.graph_objects.Figure
        Plotly figure containing the heatmap
    """
    fig = px.imshow(
        data,
        text_auto=text_auto,
        color_continuous_scale=colorscale,
        title=title
    )
    
    return fig