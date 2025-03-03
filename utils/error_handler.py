# utils/error_handler.py
import logging
import streamlit as st

def handle_error(error, error_type, user_message=None):
    """
    Central function to handle all errors in the application.
    
    Parameters:
    -----------
    error : Exception
        The actual error that occurred
    error_type : str
        What kind of error it is (e.g., "Data Loading Error")
    user_message : str, optional
        Optional message to show to the user, by default None
    """
    # Log the error for developers
    logging.error(f"{error_type}: {error}")
    
    # Show a message to the user
    if user_message:
        st.error(user_message)
    else:
        st.error(f"Une erreur s'est produite: {error}")
        
    # For debugging in development environment
    if st.secrets.get("environment", "production") == "development":
        st.exception(error)