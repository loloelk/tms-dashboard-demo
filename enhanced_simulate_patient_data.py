# enhanced_simulate_patient_data.py

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import random
import math
import logging # Import logging

# --- Import functions to save data directly to DB ---
# Ensure services/nurse_service.py is accessible (adjust path if needed)
try:
    from services.nurse_service import save_nurse_inputs, save_side_effect_report, initialize_database
    DB_INTERACTION_ENABLED = True
except ImportError as e:
    logging.warning(f"Could not import from services.nurse_service: {e}. Will save to CSV instead.")
    DB_INTERACTION_ENABLED = False


# --- Configuration Parameters ---
NUM_PATIENTS = 50
PROTOCOLS = ['HF - 10Hz', 'iTBS', 'BR - 18Hz']
START_DATE = datetime(2024, 1, 1)
SIMULATION_DURATION_DAYS = 30 # How many days of EMA/Notes/Effects to simulate

# Protocol response probabilities (HF > BR > iTBS)
PROTOCOL_RESPONSE_RATES = {'HF - 10Hz': 0.65, 'BR - 18Hz': 0.48, 'iTBS': 0.36}
PROTOCOL_REMISSION_RATES = {'HF - 10Hz': 0.42, 'BR - 18Hz': 0.28, 'iTBS': 0.20}

# EMA Simulation Parameters
EMA_MISSING_DAY_PROB = 0.05 # 5% chance to miss all entries for a day
EMA_MISSING_ENTRY_PROB = 0.10 # 10% chance to miss an individual entry (if >1 planned)
EMA_ENTRIES_PER_DAY_WEIGHTS = [0.1, 0.6, 0.3] # Weights for [1, 2, 3] entries/day

# Side Effect Simulation Parameters
SIDE_EFFECT_PROB_INITIAL = 0.4 # 40% chance of *some* side effect on early days
SIDE_EFFECT_PROB_LATER = 0.1 # 10% chance later
SIDE_EFFECT_DECAY_DAY = 10 # Day by which side effect probability reduces

# Create data directory if needed
os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True) # For logging

# Configure basic logging for the script
log_file = os.path.join('logs', f'simulation_{datetime.now():%Y-%m-%d_%H%M%S}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)

# --- Helper Functions ---

def distribute_phq9_score(total_score):
    """Distribute a total PHQ-9 score into 9 item scores realistically (Unchanged)"""
    if total_score <= 0: return [0] * 9
    weights = [1.5, 1.5, 1.0, 1.0, 0.8, 1.0, 1.0, 0.8, 0.5]
    normalized_weights = [w/sum(weights) for w in weights]
    raw_distribution = [total_score * w for w in normalized_weights]
    items = [min(3, max(0, round(val))) for val in raw_distribution]
    current_sum = sum(items)
    # Adjust sum up
    while current_sum < total_score and max(items) < 3:
        eligible_indices = [i for i, score in enumerate(items) if score < 3]
        if not eligible_indices: break
        idx = random.choices(eligible_indices, [normalized_weights[i] for i in eligible_indices])[0]
        items[idx] += 1; current_sum += 1
    # Adjust sum down
    while current_sum > total_score and min(items) > 0:
        eligible_indices = [i for i, score in enumerate(items) if score > 0]
        if not eligible_indices: break
        inverse_weights = [1/normalized_weights[i] for i in eligible_indices]
        idx = random.choices(eligible_indices, [w/sum(inverse_weights) for w in inverse_weights])[0]
        items[idx] -= 1; current_sum -= 1
    return items

def generate_pid5_scores(patient, will_respond):
    """Generate PID-5 personality inventory scores (Unchanged)"""
    domains = { 'Affect Négatif': [8, 9, 10, 11, 15], 'Détachement': [4, 13, 14, 16, 18],
                'Antagonisme': [17, 19, 20, 22, 25], 'Désinhibition': [1, 2, 3, 5, 6],
                'Psychoticisme': [7, 12, 21, 23, 24] }
    pid5_bl = random.randint(65, 95)
    improvement = random.uniform(0.15, 0.25) if will_respond else random.uniform(0.05, 0.15)
    pid5_fu = int(pid5_bl * (1 - improvement))
    patient['pid5_score_bl'] = pid5_bl; patient['pid5_score_fu'] = pid5_fu
    domain_weights = {'Affect Négatif': 1.3, 'Détachement': 1.1, 'Antagonisme': 0.8, 'Désinhibition': 0.9, 'Psychoticisme': 0.7}
    normalized_weights = {k: v/sum(domain_weights.values()) for k, v in domain_weights.items()}
    for domain, items in domains.items():
        for item in items:
            item_bl = random.randint(1, 4)
            if will_respond: item_fu = max(0, item_bl - random.randint(0, 2))
            else: item_fu = max(0, item_bl - random.randint(0, 1))
            patient[f'pid5_{item}_bl'] = item_bl; patient[f'pid5_{item}_fu'] = item_fu
    return patient

# --- Main Data Generation Functions ---

def generate_patient_data():
    """Generate main patient data"""
    logging.info("Generating patient main data...")
    patients = []
    for i in range(1, NUM_PATIENTS + 1):
        patient_id = f'P{str(i).zfill(3)}'
        age = max(18, min(75, int(np.random.normal(43.2, 12.5))))
        sex = random.choices(['1', '2'], weights=[0.42, 0.58])[0]
        protocol = random.choice(PROTOCOLS)
        psychotherapie = random.choices(['0', '1'], weights=[0.35, 0.65])[0]
        ect = random.choices(['0', '1'], weights=[0.92, 0.08])[0]
        rtms = random.choices(['0', '1'], weights=[0.85, 0.15])[0]
        tdcs = random.choices(['0', '1'], weights=[0.95, 0.05])[0]
        will_respond = random.random() < PROTOCOL_RESPONSE_RATES[protocol]
        will_remit = random.random() < PROTOCOL_REMISSION_RATES[protocol]
        phq9_bl = max(10, min(27, int(np.random.normal(18.2, 4.3))))
        improvement = random.uniform(0.51, 0.85) if will_respond else random.uniform(0.15, 0.49)
        phq9_fu = max(0, int(phq9_bl * (1 - improvement)))
        madrs_bl = max(15, min(40, int(phq9_bl * 1.4)))
        madrs_improvement = improvement * random.uniform(0.8, 1.2)
        madrs_fu = random.randint(4, 9) if will_remit else max(10, int(madrs_bl * (1 - madrs_improvement)))

        patient = { 'ID': patient_id, 'age': age, 'sexe': sex, 'protocol': protocol,
                    'Timestamp': (START_DATE + timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'), # Base start date
                    'psychotherapie_bl': psychotherapie, 'ect_bl': ect, 'rtms_bl': rtms, 'tdcs_bl': tdcs,
                    'phq9_score_bl': phq9_bl, 'phq9_score_fu': phq9_fu,
                    'madrs_score_bl': madrs_bl, 'madrs_score_fu': madrs_fu,
                    'will_respond': will_respond, 'will_remit': will_remit # Store outcome for other sims
                  }
        # Add comorbidities
        comorbidities = ["None", "Anxiety", "PTSD", "Substance use", "Personality disorder", "Bipolar II"]
        patient['comorbidities'] = random.choices(comorbidities, weights=[0.30, 0.35, 0.15, 0.10, 0.07, 0.03])[0]
        # Add other demographics
        patient['pregnant'] = '0' if sex == '1' else random.choices(['0', '1'], weights=[0.94, 0.06])[0]
        patient['cigarette_bl'] = random.choices(['0', '1'], weights=[0.74, 0.26])[0]
        patient['alcool_bl'] = random.choices(['0', '1'], weights=[0.85, 0.15])[0]
        patient['cocaine_bl'] = random.choices(['0', '1'], weights=[0.93, 0.07])[0]
        patient['hospitalisation_bl'] = random.choices(['0', '1'], weights=[0.75, 0.25])[0]
        patient['annees_education_bl'] = max(8, min(20, int(np.random.normal(14.2, 3.1))))
        patient['revenu_bl'] = max(12000, min(150000, int(np.random.lognormal(10.5, 0.8))))

        # Generate MADRS items
        for item in range(1, 11):
            if item in [1, 2, 7, 9]: baseline_mean = 3.5
            elif item in [4, 5, 6]: baseline_mean = 2.8
            else: baseline_mean = 2.2
            baseline_item = max(0, min(6, int(np.random.normal(baseline_mean, 1.0))))
            followup_mean = baseline_item * (1 - madrs_improvement)
            followup_item = max(0, min(6, int(np.random.normal(followup_mean, 0.8))))
            patient[f'madrs_{item}_bl'] = baseline_item
            patient[f'madrs_{item}_fu'] = followup_item
        # Adjust MADRS items to sum approx to total (Unchanged)
        madrs_items_bl_sum = sum(patient[f'madrs_{item}_bl'] for item in range(1, 11))
        adj_factor_bl = madrs_bl / max(1, madrs_items_bl_sum)
        for item in range(1, 11): patient[f'madrs_{item}_bl'] = min(6, max(0, int(patient[f'madrs_{item}_bl'] * adj_factor_bl)))
        madrs_items_fu_sum = sum(patient[f'madrs_{item}_fu'] for item in range(1, 11))
        adj_factor_fu = madrs_fu / max(1, madrs_items_fu_sum)
        for item in range(1, 11): patient[f'madrs_{item}_fu'] = min(6, max(0, int(patient[f'madrs_{item}_fu'] * adj_factor_fu)))

        # Generate PHQ9 daily items (Unchanged)
        days = [5, 10, 15, 20, 25, 30]
        improvement_curve = []
        for day in days:
            progress = day / 30.0
            day_improvement = improvement * (1 / (1 + math.exp(-10 * (progress - 0.5))))
            improvement_curve.append(max(0, int(phq9_bl * (1 - day_improvement))))
        for i in range(1, len(improvement_curve)): # Add noise
             delta = improvement_curve[i-1] - improvement_curve[i]
             improvement_curve[i] = improvement_curve[i-1] - max(0, int(delta + random.randint(-1, 1)))
        for day_idx, day in enumerate(days):
             phq9_items = distribute_phq9_score(improvement_curve[day_idx])
             for item, score in enumerate(phq9_items, 1): patient[f'phq9_day{day}_item{item}'] = score

        # Generate PID5 scores (Unchanged)
        patient = generate_pid5_scores(patient, will_respond)

        patients.append(patient)

    logging.info(f"Generated main data for {len(patients)} patients.")
    return pd.DataFrame(patients)

def generate_ema_data(patient_df):
    """Generate simulated EMA data with missing data simulation"""
    logging.info("Generating EMA data...")
    MADRS_ITEMS = [f'madrs_{i}' for i in range(1, 11)]
    ANXIETY_ITEMS = [f'anxiety_{i}' for i in range(1, 6)]
    SLEEP, ENERGY, STRESS = 'sleep', 'energy', 'stress'
    SYMPTOMS = MADRS_ITEMS + ANXIETY_ITEMS + [SLEEP, ENERGY, STRESS]
    ema_entries = []

    for _, patient in patient_df.iterrows():
        patient_id = patient['ID']
        protocol = patient['protocol']
        improved = patient['will_respond'] # Use stored outcome
        baseline_severity = patient['madrs_score_bl'] / 40.0
        current_severity = baseline_severity
        protocol_effect = {'HF - 10Hz': 0.8, 'BR - 18Hz': 0.65, 'iTBS': 0.5}
        stability = protocol_effect[protocol]
        patient_start_date = pd.to_datetime(patient['Timestamp'])

        for day in range(1, SIMULATION_DURATION_DAYS + 1):
            # --- Simulate Missing Day ---
            if random.random() < EMA_MISSING_DAY_PROB:
                logging.debug(f"Patient {patient_id} missing EMA for Day {day}")
                continue # Skip this day entirely

            # --- Calculate Target Severity ---
            day_effect = day / float(SIMULATION_DURATION_DAYS)
            improvement_factor = 0.7 if improved else 0.2 # Responders improve more
            target_severity = baseline_severity * (1 - day_effect * improvement_factor)

            # Move current severity toward target + noise (More variability early)
            noise_level = 0.15 * (1 - day_effect * 0.5) # More noise early on
            current_severity = current_severity * stability + target_severity * (1 - stability)
            current_severity += random.uniform(-noise_level, noise_level)
            current_severity = max(0, min(1, current_severity))

            # --- Generate Entries for the Day ---
            n_entries_planned = random.choices([1, 2, 3], weights=EMA_ENTRIES_PER_DAY_WEIGHTS)[0]
            entries_today = 0
            for entry_num in range(1, n_entries_planned + 1):
                 # --- Simulate Missing Entry ---
                 if n_entries_planned > 1 and random.random() < EMA_MISSING_ENTRY_PROB:
                      logging.debug(f"Patient {patient_id} missing EMA Entry {entry_num}/{n_entries_planned} on Day {day}")
                      continue # Skip this specific entry

                 hour = random.randint(8, 21); minute = random.randint(0, 59)
                 # Ensure timestamp uses patient's specific start date
                 timestamp = patient_start_date + timedelta(days=day - 1, hours=hour, minutes=minute)

                 entry_severity = max(0, min(1, current_severity * random.uniform(0.9, 1.1)))
                 ema_entry = {'PatientID': patient_id, 'Timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                              'Day': day, 'Entry': entry_num}

                 # Add symptom scores (same logic as before)
                 for item in range(1, 11): ema_entry[f'madrs_{item}'] = int(max(0, min(6, (entry_severity*6) + random.uniform(-1.5, 1.5))))
                 for item in range(1, 6): ema_entry[f'anxiety_{item}'] = int(max(0, min(4, (entry_severity*4) + random.uniform(-1, 1))))
                 ema_entry[SLEEP] = int(max(0, min(4, ((1-entry_severity)*4) + random.uniform(-1, 1))))
                 ema_entry[ENERGY] = int(max(0, min(4, ((1-entry_severity)*4) + random.uniform(-1, 1))))
                 ema_entry[STRESS] = int(max(0, min(4, (entry_severity*4) + random.uniform(-1, 1))))

                 ema_entries.append(ema_entry)
                 entries_today += 1

            logging.debug(f"Patient {patient_id} Day {day}: Target Sev {target_severity:.2f}, Actual Entries {entries_today}/{n_entries_planned}")


    logging.info(f"Generated {len(ema_entries)} EMA entries.")
    return pd.DataFrame(ema_entries)

def generate_side_effects_data(patient_df):
    """Generate simulated side effect reports and save to DB."""
    logging.info("Generating side effects data...")
    if not DB_INTERACTION_ENABLED:
        logging.warning("Database interaction disabled. Skipping side effect DB insertion.")
        # Optionally save to CSV as fallback
        # side_effects_list = [] ... append dicts ... pd.DataFrame(side_effects_list).to_csv(...)
        return

    num_saved = 0
    for _, patient in patient_df.iterrows():
        patient_id = patient['ID']
        patient_start_date = pd.to_datetime(patient['Timestamp'])

        # Simulate a few reports per patient, mostly early on
        num_reports = random.randint(1, 5)
        for i in range(num_reports):
            # Effects more likely early, less likely later
            day_offset = random.randint(1, SIMULATION_DURATION_DAYS)
            prob_cutoff = SIDE_EFFECT_PROB_INITIAL if day_offset <= SIDE_EFFECT_DECAY_DAY else SIDE_EFFECT_PROB_LATER

            if random.random() < prob_cutoff:
                report_date = patient_start_date + timedelta(days=day_offset)
                report_data = {'patient_id': patient_id, 'report_date': report_date.strftime('%Y-%m-%d')}

                # Simulate severity (mostly mild)
                report_data['headache'] = random.choices([0, 1, 2, 3, 4], weights=[0.6, 0.2, 0.1, 0.05, 0.05])[0]
                report_data['nausea'] = random.choices([0, 1, 2], weights=[0.8, 0.15, 0.05])[0]
                report_data['scalp_discomfort'] = random.choices([0, 1, 2, 3], weights=[0.5, 0.3, 0.15, 0.05])[0]
                report_data['dizziness'] = random.choices([0, 1, 2], weights=[0.75, 0.15, 0.10])[0]
                report_data['other_effects'] = random.choice(['', 'Fatigue légère', '']) if random.random() < 0.1 else ''
                report_data['notes'] = random.choice(['', 'Mentionné en passant', 'Semble tolérer ok', '']) if random.random() < 0.2 else ''

                # Save to DB using the imported function
                try:
                    save_side_effect_report(report_data)
                    num_saved += 1
                except Exception as e:
                    logging.error(f"Failed to save side effect report for {patient_id} via service: {e}")

    logging.info(f"Generated and attempted to save {num_saved} side effect reports to database.")


def generate_nurse_notes_data(patient_df):
    """Generate simulated nurse notes/plan updates and save to DB."""
    logging.info("Generating nurse notes data...")
    if not DB_INTERACTION_ENABLED:
        logging.warning("Database interaction disabled. Skipping nurse note DB insertion.")
        return

    num_saved = 0
    for _, patient in patient_df.iterrows():
        patient_id = patient['ID']
        patient_start_date = pd.to_datetime(patient['Timestamp'])
        will_respond = patient['will_respond']
        will_remit = patient['will_remit']
        protocol = patient['protocol']

        # --- Initial Note (Day 1-3) ---
        initial_day = random.randint(1, 3)
        initial_ts = patient_start_date + timedelta(days=initial_day)
        initial_note = {
            'patient_id': patient_id,
            'objectives': f"Initiation protocole {protocol}. Objectif: Réduction MADRS >50%. Surveillance effets secondaires.",
            'tasks': "Compléter questionnaires journaliers (EMA). Rapporter effets secondaires.",
            'comments': "Patient motivé pour commencer le traitement.",
            'target_symptoms': "Humeur dépressive, Anhédonie, Insomnie",
            'planned_interventions': f"Protocole TMS standard {protocol}.",
            'goal_status': "Not Started",
            # Add timestamp explicitly if needed by save function signature (or let DB handle it)
        }
        try:
            # Assuming save_nurse_inputs handles timestamp via DEFAULT CURRENT_TIMESTAMP
            save_nurse_inputs(**initial_note) # Use dictionary unpacking
            num_saved += 1
        except Exception as e:
             logging.error(f"Failed to save initial nurse note for {patient_id} via service: {e}")


        # --- Mid-Treatment Note (Day 12-18) ---
        mid_day = random.randint(12, 18)
        mid_ts = patient_start_date + timedelta(days=mid_day)
        mid_status = "In Progress"
        mid_comment = "Amélioration légère du sommeil rapportée." if random.random() < 0.6 else "Stabilité des symptômes."
        if not will_respond and random.random() < 0.3:
             mid_comment = "Patient exprime frustration, peu d'amélioration ressentie."
             mid_status = "On Hold" # Example status change

        mid_note = {
            'patient_id': patient_id,
            'objectives': initial_note['objectives'], # Carry over objectives for simplicity
            'tasks': initial_note['tasks'],
            'comments': mid_comment,
            'target_symptoms': initial_note['target_symptoms'],
            'planned_interventions': initial_note['planned_interventions'],
            'goal_status': mid_status
        }
        try:
            save_nurse_inputs(**mid_note)
            num_saved += 1
        except Exception as e:
             logging.error(f"Failed to save mid-treatment nurse note for {patient_id} via service: {e}")


        # --- Final Note (Day 28-30) ---
        final_day = random.randint(28, 30)
        final_ts = patient_start_date + timedelta(days=final_day)
        if will_remit:
             final_status = "Achieved"
             final_comment = "Rémission obtenue selon MADRS. Discussion fin de traitement."
        elif will_respond:
             final_status = "Achieved" # Or maybe 'Partially Achieved' if adding status
             final_comment = "Réponse significative au traitement. MADRS amélioré >50%."
        else:
             final_status = "Revised" # Example status
             final_comment = "Réponse insuffisante. Discussion d'options alternatives."

        final_note = {
            'patient_id': patient_id,
            'objectives': initial_note['objectives'],
            'tasks': "Planification suivi post-traitement.",
            'comments': final_comment,
            'target_symptoms': initial_note['target_symptoms'],
            'planned_interventions': "Fin protocole TMS standard." if will_respond else "Réévaluation / Changement de stratégie",
            'goal_status': final_status
        }
        try:
            save_nurse_inputs(**final_note)
            num_saved += 1
        except Exception as e:
             logging.error(f"Failed to save final nurse note for {patient_id} via service: {e}")


    logging.info(f"Generated and attempted to save {num_saved} nurse notes to database.")


# --- Main Execution ---
if __name__ == "__main__":
    logging.info("--- Starting Data Simulation ---")

    # Initialize DB schema (ensure tables/columns exist)
    if DB_INTERACTION_ENABLED:
        logging.info("Initializing database schema...")
        initialize_database()
    else:
         logging.warning("DB interaction disabled, schema not initialized by script.")

    # Generate main patient data
    patient_data_df = generate_patient_data()
    # Remove columns no longer needed (objectives, tasks, comments were placeholders)
    cols_to_drop = ['objectives', 'tasks', 'comments']
    patient_data_df = patient_data_df.drop(columns=[col for col in cols_to_drop if col in patient_data_df.columns])
    # Save main patient data to CSV
    patient_csv_path = 'data/patient_data_with_protocol_simulated.csv'
    patient_data_df.to_csv(patient_csv_path, index=False)
    logging.info(f"Saved main patient data for {len(patient_data_df)} patients to {patient_csv_path}")

    # Generate EMA data
    ema_data_df = generate_ema_data(patient_data_df)
    ema_csv_path = 'data/simulated_ema_data.csv'
    ema_data_df.to_csv(ema_csv_path, index=False)
    logging.info(f"Saved {len(ema_data_df)} EMA entries to {ema_csv_path}")

    # Generate and save Side Effects data (directly to DB if possible)
    generate_side_effects_data(patient_data_df)

    # Generate and save Nurse Notes data (directly to DB if possible)
    generate_nurse_notes_data(patient_data_df)

    # Create/Update config.yaml file (Unchanged)
    config_content = """
paths:
  patient_data_with_protocol: "data/patient_data_with_protocol_simulated.csv"
  # patient_data field might be redundant if same as above, keep for now
  patient_data: "data/patient_data_with_protocol_simulated.csv"
  # nurse_inputs: field no longer used by app - database is source
  simulated_ema_data: "data/simulated_ema_data.csv"

mappings:
  madrs_items:
    1: "Tristesse Apparente"
    2: "Tristesse Signalée"
    3: "Tension Intérieure"
    4: "Sommeil Réduit"
    5: "Appétit Réduit"
    6: "Difficultés de Concentration"
    7: "Lassitude"
    8: "Incapacité à Ressentir"
    9: "Pensées Pessimistes"
    10: "Pensées Suicidaires"

  pid5_dimensions:
    Affect Négatif: [8, 9, 10, 11, 15]
    Détachement: [4, 13, 14, 16, 18]
    Antagonisme: [17, 19, 20, 22, 25]
    Désinhibition: [1, 2, 3, 5, 6]
    Psychoticisme: [7, 12, 21, 23, 24]
"""
    os.makedirs('config', exist_ok=True)
    with open('config/config.yaml', 'w') as f: f.write(config_content)
    logging.info("Updated config.yaml file")

    logging.info("--- Simulation complete. ---")
    print("\nSimulation complete. You can now run the application with 'streamlit run app.py'")
    print(f"Log file generated at: {log_file}")