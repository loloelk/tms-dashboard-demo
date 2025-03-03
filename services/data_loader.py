# services/data_loader.py
import pandas as pd
import logging
from utils.error_handler import handle_error

def load_patient_data(csv_file: str) -> pd.DataFrame:
    """
    Load patient data from a CSV file with appropriate encoding.
    
    Parameters:
    -----------
    csv_file : str
        Path to the CSV file containing patient data
        
    Returns:
    --------
    pd.DataFrame
        DataFrame containing patient data
    """
    try:
        data = pd.read_csv(csv_file, dtype={'ID': str}, encoding='utf-8')
        logging.debug(f"Patient data loaded successfully from {csv_file} with 'utf-8' encoding.")
        return data
    except UnicodeDecodeError:
        logging.warning(f"UnicodeDecodeError with 'utf-8' encoding for {csv_file}. Trying 'latin1'.")
        try:
            data = pd.read_csv(csv_file, dtype={'ID': str}, encoding='latin1')
            logging.debug(f"Patient data loaded successfully from {csv_file} with 'latin1' encoding.")
            return data
        except Exception as e:
            logging.error(f"Failed to load patient data from {csv_file}: {e}")
            return pd.DataFrame()
    except Exception as e:
        logging.error(f"Failed to load patient data from {csv_file}: {e}")
        return pd.DataFrame()

def validate_patient_data(data: pd.DataFrame):
    """
    Validate the structure and content of patient data.
    
    Parameters:
    -----------
    data : pd.DataFrame
        DataFrame containing patient data to validate
        
    Raises:
    -------
    ValueError
        If data validation fails
    """
    if 'ID' not in data.columns:
        error_msg = "La colonne 'ID' est manquante dans le fichier CSV des patients."
        logging.error("The 'ID' column is missing in the patient data.")
        raise ValueError(error_msg)

    if data['ID'].isnull().any():
        error_msg = "Certaines entrées de la colonne 'ID' sont vides. Veuillez les remplir."
        logging.error("There are empty entries in the 'ID' column.")
        raise ValueError(error_msg)

    if data['ID'].duplicated().any():
        error_msg = "Il y a des IDs dupliqués dans la colonne 'ID'. Veuillez assurer l'unicité."
        logging.error("There are duplicate IDs in the 'ID' column.")
        raise ValueError(error_msg)

    logging.debug("Patient data validation passed.")

def load_simulated_ema_data(csv_file: str) -> pd.DataFrame:
    """
    Load simulated EMA data from a CSV file with appropriate encoding.
    
    Parameters:
    -----------
    csv_file : str
        Path to the CSV file containing EMA data
        
    Returns:
    --------
    pd.DataFrame
        DataFrame containing EMA data
    """
    try:
        data = pd.read_csv(csv_file, dtype={'PatientID': str}, encoding='utf-8')
        logging.debug(f"Simulated EMA data loaded successfully from {csv_file} with 'utf-8' encoding.")
        return data
    except UnicodeDecodeError:
        logging.warning(f"UnicodeDecodeError with 'utf-8' encoding for {csv_file}. Trying 'latin1'.")
        try:
            data = pd.read_csv(csv_file, dtype={'PatientID': str}, encoding='latin1')
            logging.debug(f"Simulated EMA data loaded successfully from {csv_file} with 'latin1' encoding.")
            return data
        except Exception as e:
            logging.error(f"Failed to load simulated EMA data from {csv_file}: {e}")
            return pd.DataFrame()
    except Exception as e:
        logging.error(f"Failed to load simulated EMA data from {csv_file}: {e}")
        return pd.DataFrame()

def merge_simulated_data(final_df: pd.DataFrame, ema_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge simulated EMA data with the final patient data.
    
    Parameters:
    -----------
    final_df : pd.DataFrame
        DataFrame containing patient data
    ema_df : pd.DataFrame
        DataFrame containing EMA data
        
    Returns:
    --------
    pd.DataFrame
        Merged DataFrame
    """
    if ema_df.empty:
        logging.warning("Simulated EMA data is empty. Skipping merge.")
        return final_df
    
    # Assuming 'ID' in final_data corresponds to 'PatientID' in simulated_ema_data
    merged_df = final_df.merge(ema_df, how='left', left_on='ID', right_on='PatientID')
    return merged_df