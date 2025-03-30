# services/nurse_service.py
import streamlit as st
import sqlite3
import pandas as pd
import logging
import os
from typing import Dict, Optional, List

DATABASE_PATH = 'data/dashboard_data.db'

# --- Database Connection and Initialization ---
def get_db():
    """Establish database connection."""
    os.makedirs('data', exist_ok=True)
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        logging.debug("Database connection established.")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        st.error(f"Database connection error: {e}")
        st.stop()

def _add_column_if_not_exists(cursor, table_name, column_name, column_type):
    """Helper function to add a column if it doesn't exist."""
    try:
        cursor.execute(f"SELECT {column_name} FROM {table_name} LIMIT 1")
        logging.debug(f"Column '{column_name}' already exists in '{table_name}'.")
    except sqlite3.OperationalError:
        # Column does not exist, add it
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            logging.info(f"Added column '{column_name}' to table '{table_name}'.")
        except sqlite3.Error as e:
            logging.error(f"Error adding column '{column_name}' to '{table_name}': {e}")
            st.warning(f"Could not add column {column_name} to {table_name}. Manual check might be needed.")


def initialize_database():
    """Initialize the database tables and add new columns if needed."""
    logging.info("Initializing database...")
    conn = get_db()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        # Create Nurse Inputs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nurse_inputs (
                input_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                objectives TEXT,
                tasks TEXT,
                comments TEXT,
                created_by TEXT -- Optional: Track who made the entry
                -- New columns will be added below by _add_column_if_not_exists
                -- FOREIGN KEY (patient_id) REFERENCES patients (ID) ON DELETE CASCADE -- Add FK later if needed
            );
        """)
        logging.info("Table 'nurse_inputs' checked/created.")

        # Add new columns for treatment planning to nurse_inputs if they don't exist
        _add_column_if_not_exists(cursor, 'nurse_inputs', 'target_symptoms', 'TEXT')
        _add_column_if_not_exists(cursor, 'nurse_inputs', 'planned_interventions', 'TEXT')
        _add_column_if_not_exists(cursor, 'nurse_inputs', 'goal_status', 'TEXT') # e.g., 'Not Started', 'In Progress', 'Achieved'


        # Create Side Effects Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS side_effects (
                effect_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                report_date DATE NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                headache INTEGER DEFAULT 0,
                nausea INTEGER DEFAULT 0,
                scalp_discomfort INTEGER DEFAULT 0,
                dizziness INTEGER DEFAULT 0,
                other_effects TEXT,
                notes TEXT,
                created_by TEXT -- Optional
                -- FOREIGN KEY (patient_id) REFERENCES patients (ID) ON DELETE CASCADE -- Add FK later if needed
            );
        """)
        logging.info("Table 'side_effects' checked/created.")

        # Create placeholder patients table (simplified)
        cursor.execute("""
             CREATE TABLE IF NOT EXISTS patients (
                 ID TEXT PRIMARY KEY NOT NULL,
                 name TEXT
             );
         """)
        logging.info("Table 'patients' checked/created.")

        conn.commit()
        logging.info("Database initialization complete.")

    except sqlite3.Error as e:
        logging.error(f"Error initializing database tables: {e}")
        st.error(f"Error initializing database tables: {e}")
    finally:
        if conn:
            conn.close()
            logging.debug("Database connection closed after initialization.")


# --- Nurse Service Functions ---

def get_latest_nurse_inputs(patient_id: str) -> Optional[Dict[str, str]]:
    """Retrieve the most recent nurse inputs (including planning fields) for a specific patient."""
    if not patient_id: return None
    conn = get_db()
    if conn is None: return None
    try:
        cursor = conn.cursor()
        # Select all relevant columns, including new ones
        cursor.execute("""
            SELECT objectives, tasks, comments, timestamp,
                   target_symptoms, planned_interventions, goal_status
            FROM nurse_inputs
            WHERE patient_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (patient_id,))
        row = cursor.fetchone()
        logging.debug(f"Fetched latest nurse inputs for {patient_id}")
        # Provide default empty strings if a field wasn't present in the fetched row (e.g., older entries)
        if row:
            result = dict(row)
            result.setdefault('target_symptoms', '')
            result.setdefault('planned_interventions', '')
            result.setdefault('goal_status', 'Not Set') # Default status if not set
            return result
        else:
             # Return defaults if no entries exist
             return {
                 "objectives": "", "tasks": "", "comments": "",
                 "target_symptoms": "", "planned_interventions": "", "goal_status": "Not Set"
             }
    except sqlite3.Error as e:
        logging.error(f"Error fetching nurse inputs for {patient_id}: {e}")
        st.error(f"Error fetching nurse inputs: {e}")
        return None
    finally:
        if conn: conn.close()

def save_nurse_inputs(patient_id: str, objectives: str, tasks: str, comments: str,
                      target_symptoms: str, planned_interventions: str, goal_status: str,
                      created_by: str = "Clinician"):
    """Save new nurse inputs including treatment planning fields."""
    if not patient_id:
        st.error("Patient ID cannot be empty.")
        return False
    conn = get_db()
    if conn is None: return False
    try:
        cursor = conn.cursor()
        # Ensure patient exists in placeholder table (or handle FK appropriately)
        cursor.execute("INSERT OR IGNORE INTO patients (ID) VALUES (?)", (patient_id,))

        cursor.execute("""
            INSERT INTO nurse_inputs (
                patient_id, objectives, tasks, comments, created_by,
                target_symptoms, planned_interventions, goal_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, objectives, tasks, comments, created_by,
              target_symptoms, planned_interventions, goal_status))
        conn.commit()
        logging.info(f"Nurse inputs saved successfully for Patient ID {patient_id}.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Failed to save nurse inputs for Patient ID {patient_id}: {e}")
        st.error(f"Failed to save nurse inputs: {e}")
        return False
    finally:
        if conn: conn.close()

def get_nurse_inputs_history(patient_id: str) -> pd.DataFrame:
    """Retrieve all historical nurse inputs, including new planning fields."""
    if not patient_id: return pd.DataFrame()
    conn = get_db()
    if conn is None: return pd.DataFrame()
    try:
        # Select all columns including new ones
        query = """
            SELECT timestamp, objectives, tasks, comments, created_by,
                   target_symptoms, planned_interventions, goal_status, patient_id
            FROM nurse_inputs
            WHERE patient_id = ?
            ORDER BY timestamp DESC
        """ # Added patient_id to select
        df = pd.read_sql_query(query, conn, params=(patient_id,))
        logging.debug(f"Fetched nurse input history for {patient_id}, {len(df)} entries.")
        # Convert timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Fill NaN in new columns for older entries if necessary
        for col in ['target_symptoms', 'planned_interventions', 'goal_status']:
            if col in df.columns:
                df[col] = df[col].fillna('') # Replace potential NaN with empty string

        return df
    except Exception as e:
        logging.error(f"Error fetching nurse input history for {patient_id}: {e}")
        st.error(f"Error fetching nurse input history: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()


# --- Side Effect Service Functions ---

def save_side_effect_report(report_data: Dict):
    """Save a new side effect report to the database."""
    required_keys = ['patient_id', 'report_date', 'headache', 'nausea', 'scalp_discomfort', 'dizziness']
    if not all(key in report_data for key in required_keys):
        st.error("Missing required fields in side effect report data.")
        return False

    conn = get_db()
    if conn is None: return False

    try:
        cursor = conn.cursor()
         # Ensure the patient exists in the placeholder table
        cursor.execute("INSERT OR IGNORE INTO patients (ID) VALUES (?)", (report_data['patient_id'],))

        cursor.execute("""
            INSERT INTO side_effects (
                patient_id, report_date, headache, nausea, scalp_discomfort,
                dizziness, other_effects, notes, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_data['patient_id'],
            report_data['report_date'],
            report_data['headache'],
            report_data['nausea'],
            report_data['scalp_discomfort'],
            report_data['dizziness'],
            report_data.get('other_effects', ''), # Use .get for optional fields
            report_data.get('notes', ''),
            report_data.get('created_by', 'Clinician')
        ))
        conn.commit()
        logging.info(f"Side effect report saved successfully for Patient ID {report_data['patient_id']}.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Failed to save side effect report for Patient ID {report_data['patient_id']}: {e}")
        st.error(f"Failed to save side effect report: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_side_effects_history(patient_id: str) -> pd.DataFrame:
    """Retrieve all historical side effect reports for a specific patient."""
    if not patient_id: return pd.DataFrame()

    conn = get_db()
    if conn is None: return pd.DataFrame()

    try:
        # ***** CORRECTED QUERY: Includes patient_id *****
        query = """
            SELECT patient_id, report_date, headache, nausea, scalp_discomfort, dizziness,
                   other_effects, notes, timestamp, created_by
            FROM side_effects
            WHERE patient_id = ?
            ORDER BY report_date DESC, timestamp DESC
        """
        # ***** END OF CORRECTION *****
        df = pd.read_sql_query(query, conn, params=(patient_id,))
        logging.debug(f"Fetched side effect history for {patient_id}, {len(df)} entries.")
        # Convert date/timestamp columns if needed
        if 'report_date' in df.columns:
            df['report_date'] = pd.to_datetime(df['report_date'])
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df
    except Exception as e: # Catch pandas and sqlite errors
        logging.error(f"Error fetching side effect history for {patient_id}: {e}")
        st.error(f"Error fetching side effect history: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()