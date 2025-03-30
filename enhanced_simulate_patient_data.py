# enhanced_simulate_patient_data.py

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import random
import math
import logging
import sys

# --- Import functions to save data directly to DB ---
try:
    from services.nurse_service import save_nurse_inputs, save_side_effect_report, initialize_database
    DB_INTERACTION_ENABLED = True
except ImportError as e:
    print(f"WARNING: Could not import from services.nurse_service: {e}. Will save to CSV instead (Nurse/Side Effect data won't populate DB).")
    DB_INTERACTION_ENABLED = False
    def save_nurse_inputs(*args, **kwargs): pass
    def save_side_effect_report(*args, **kwargs): pass
    def initialize_database(): pass


# --- Configuration Parameters ---
NUM_PATIENTS = 50
PROTOCOLS = ['HF - 10Hz', 'iTBS', 'BR - 18Hz']
START_DATE = datetime(2024, 1, 1)
SIMULATION_DURATION_DAYS = 30

# Protocol response probabilities (BASE rates)
PROTOCOL_RESPONSE_RATES = {'HF - 10Hz': 0.65, 'BR - 18Hz': 0.48, 'iTBS': 0.36}
PROTOCOL_REMISSION_RATES = {'HF - 10Hz': 0.42, 'BR - 18Hz': 0.28, 'iTBS': 0.20} # Remission linked to Neuroticism less directly for simplicity now

# EMA Simulation Parameters
EMA_MISSING_DAY_PROB = 0.05
EMA_MISSING_ENTRY_PROB = 0.10
EMA_ENTRIES_PER_DAY_WEIGHTS = [0.1, 0.6, 0.3]

# Side Effect Simulation Parameters
SIDE_EFFECT_PROB_INITIAL = 0.4
SIDE_EFFECT_PROB_LATER = 0.1
SIDE_EFFECT_DECAY_DAY = 10

# BFI Simulation Parameters
BFI_BASELINE_MEAN = 3.0 # General mean for items (1-5 scale)
BFI_BASELINE_STD = 1.0
NEUROTICISM_RESPONSE_FACTOR = 0.15 # How much N score (1-5) reduces response probability (e.g., score of 4 reduces by (4-3)*0.15 = 15%)
NEUROTICISM_CHANGE_RESPONDER = -0.4 # Average change in N score for responders
NEUROTICISM_CHANGE_NON_RESPONDER = 0.1 # Average change in N score for non-responders
OTHER_FACTOR_CHANGE_STD = 0.2 # Std dev of change for other factors

# BFI-10 Items Mapping (R = Reverse scored)
BFI_ITEMS_MAP = {
    'Extraversion': {'items': [1, 6], 'reverse': [6]},
    'Agreeableness': {'items': [2, 7], 'reverse': [2]},
    'Conscientiousness': {'items': [3, 8], 'reverse': [8]},
    'Neuroticism': {'items': [4, 9], 'reverse': [9]},
    'Openness': {'items': [5, 10], 'reverse': [10]}
}


# Create data directory if needed
os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Configure basic logging for the script
log_file = os.path.join('logs', f'simulation_{datetime.now():%Y-%m-%d_%H%M%S}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()]
)

# --- Helper Functions ---

def distribute_phq9_score(total_score):
    """Distribute a total PHQ-9 score into 9 item scores realistically"""
    # (Implementation remains the same as before)
    if total_score <= 0: return [0] * 9
    weights=[1.5, 1.5, 1.0, 1.0, 0.8, 1.0, 1.0, 0.8, 0.5]; norm_w=[w/sum(weights) for w in weights]
    raw=[total_score*w for w in norm_w]; items=[min(3,max(0,round(v))) for v in raw]
    curr=sum(items)
    while curr<total_score and max(items)<3:
        el=[i for i,s in enumerate(items) if s<3];
        if not el: break
        idx=random.choices(el,[norm_w[i] for i in el])[0]; items[idx]+=1; curr+=1
    while curr>total_score and min(items)>0:
        el=[i for i,s in enumerate(items) if s>0];
        if not el: break
        inv_w=[1/norm_w[i] if norm_w[i]>0 else float('inf') for i in el]; sum_inv=sum(w for w in inv_w if w!=float('inf'))
        if sum_inv==0: break
        inv_n=[w/sum_inv if w!=float('inf') else 0 for w in inv_w]; idx=random.choices(el,inv_n)[0]; items[idx]-=1; curr-=1
    return items

# --- BFI Generation Function ---
def generate_bfi_scores(patient, provisional_neuroticism_score_bl, will_respond):
    """Generate BFI-10 scores, using provisional N score and response status."""
    factor_scores_bl = {}
    factor_scores_fu = {}

    # Use the provided provisional baseline Neuroticism score
    factor_scores_bl['Neuroticism'] = provisional_neuroticism_score_bl

    for factor, details in BFI_ITEMS_MAP.items():
        item_scores_bl_calc = [] # For calculating final factor score BL
        item_scores_fu_calc = [] # For calculating final factor score FU

        for item_num in details['items']:
            # Simulate baseline score (1-5) - slightly adjusted variance possible per factor
            bl_score = int(round(np.random.normal(BFI_BASELINE_MEAN, BFI_BASELINE_STD)))
            bl_score = max(1, min(5, bl_score))
            patient[f'bfi10_{item_num}_bl'] = bl_score

            # Simulate follow-up score based on response status for Neuroticism
            if factor == 'Neuroticism':
                if will_respond:
                    # Decrease Neuroticism more significantly
                    change = np.random.normal(NEUROTICISM_CHANGE_RESPONDER, 0.2) # Mean change, some variance
                else:
                    # Slight change, can go up or down slightly
                    change = np.random.normal(NEUROTICISM_CHANGE_NON_RESPONDER, 0.15)
                fu_score = bl_score + change
            else:
                # Other factors: less change, not directly tied to response
                change = np.random.normal(0, OTHER_FACTOR_CHANGE_STD) # Centered around 0 change
                fu_score = bl_score + change

            fu_score = int(round(fu_score))
            fu_score = max(1, min(5, fu_score)) # Ensure score is within 1-5 range
            patient[f'bfi10_{item_num}_fu'] = fu_score

            # Handle reverse scoring for factor calculation
            bl_calc_score = (6 - bl_score) if item_num in details.get('reverse', []) else bl_score
            fu_calc_score = (6 - fu_score) if item_num in details.get('reverse', []) else fu_score
            item_scores_bl_calc.append(bl_calc_score)
            item_scores_fu_calc.append(fu_calc_score)

        # Calculate final factor score BL (except for Neuroticism which was pre-calculated)
        if factor != 'Neuroticism':
            factor_scores_bl[factor] = np.mean(item_scores_bl_calc) if item_scores_bl_calc else np.nan
        # Calculate factor score FU for all factors
        factor_scores_fu[factor] = np.mean(item_scores_fu_calc) if item_scores_fu_calc else np.nan

        # Recalculate final Neuroticism BL score based on generated items to ensure consistency
        # (Provisional score influenced 'will_respond', final score based on actual generated items)
        if factor == 'Neuroticism':
             factor_scores_bl['Neuroticism'] = np.mean(item_scores_bl_calc) if item_scores_bl_calc else np.nan


    # Add final factor scores to patient dictionary
    patient['bfi_O_bl'] = factor_scores_bl.get('Openness', np.nan)
    patient['bfi_C_bl'] = factor_scores_bl.get('Conscientiousness', np.nan)
    patient['bfi_E_bl'] = factor_scores_bl.get('Extraversion', np.nan)
    patient['bfi_A_bl'] = factor_scores_bl.get('Agreeableness', np.nan)
    patient['bfi_N_bl'] = factor_scores_bl.get('Neuroticism', np.nan) # Final calculated BL score
    patient['bfi_O_fu'] = factor_scores_fu.get('Openness', np.nan)
    patient['bfi_C_fu'] = factor_scores_fu.get('Conscientiousness', np.nan)
    patient['bfi_E_fu'] = factor_scores_fu.get('Extraversion', np.nan)
    patient['bfi_A_fu'] = factor_scores_fu.get('Agreeableness', np.nan)
    patient['bfi_N_fu'] = factor_scores_fu.get('Neuroticism', np.nan)

    return patient

# --- Main Data Generation Function ---
def generate_patient_data():
    """Generate main patient data"""
    logging.info("Generating patient main data...")
    patients = []
    base_start_date = START_DATE
    liste_comorbidites = [
        "HTA", "DLP", "DBTII", "Diabète", "Trouble Anxieux NS",
        "TPL", "TU ROH", "TOC", "Asthme", "Hypothyroïdie",
        "Migraine", "Syndrome de l'Intestin Irritable"
    ]

    for i in range(1, NUM_PATIENTS + 1):
        patient_id = f'P{str(i).zfill(3)}'
        age = max(18, min(75, int(np.random.normal(43.2, 12.5))))
        sex = random.choices(['1', '2'], weights=[0.42, 0.58])[0]
        protocol = random.choice(PROTOCOLS)
        psychotherapie = random.choices(['0', '1'], weights=[0.35, 0.65])[0]
        ect = random.choices(['0', '1'], weights=[0.92, 0.08])[0]
        rtms = random.choices(['0', '1'], weights=[0.85, 0.15])[0]
        tdcs = random.choices(['0', '1'], weights=[0.95, 0.05])[0]

        # --- Refined Response Logic ---
        # 1. Simulate Provisional Baseline Neuroticism Score
        n_items = BFI_ITEMS_MAP['Neuroticism']['items']
        n_rev = BFI_ITEMS_MAP['Neuroticism']['reverse']
        prov_n_items_bl = []
        prov_n_items_bl_calc = []
        for item_num in n_items:
            bl_score = max(1, min(5, int(round(np.random.normal(BFI_BASELINE_MEAN, BFI_BASELINE_STD)))))
            prov_n_items_bl.append(bl_score) # Store raw score temporarily if needed, not strictly required
            bl_calc_score = (6 - bl_score) if item_num in n_rev else bl_score
            prov_n_items_bl_calc.append(bl_calc_score)
        provisional_neuroticism_score_bl = np.mean(prov_n_items_bl_calc) if prov_n_items_bl_calc else 3.0 # Default if error

        # 2. Determine Response Probability based on Protocol AND Neuroticism
        base_response_prob = PROTOCOL_RESPONSE_RATES[protocol]
        # Adjust prob based on neuroticism score (deviation from mean of 3)
        neuroticism_adjustment = (provisional_neuroticism_score_bl - 3.0) * NEUROTICISM_RESPONSE_FACTOR
        adjusted_response_prob = base_response_prob - neuroticism_adjustment
        # Clamp probability between 0.01 and 0.99
        adjusted_response_prob = max(0.01, min(0.99, adjusted_response_prob))

        # 3. Determine Actual Response
        will_respond = random.random() < adjusted_response_prob
        # --- End Refined Response Logic ---

        # Determine Remission (keep simpler link to base protocol rate for now)
        will_remit = random.random() < PROTOCOL_REMISSION_RATES[protocol]

        # --- Continue with other data generation ---
        phq9_bl = max(10, min(27, int(np.random.normal(18.2, 4.3))))
        improvement = random.uniform(0.51, 0.85) if will_respond else random.uniform(0.15, 0.49)
        phq9_fu = max(0, int(phq9_bl * (1 - improvement)))
        madrs_bl = max(15, min(40, int(phq9_bl * 1.4)))
        madrs_improvement = improvement * random.uniform(0.8, 1.2)
        madrs_fu = random.randint(4, 9) if will_remit else max(10, int(madrs_bl * (1 - madrs_improvement)))
        patient_start_date = base_start_date + timedelta(days=random.randint(0, 10) + (i // 5))

        patient = { 'ID': patient_id, 'age': age, 'sexe': sex, 'protocol': protocol,
                    'Timestamp': patient_start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'psychotherapie_bl': psychotherapie, 'ect_bl': ect, 'rtms_bl': rtms, 'tdcs_bl': tdcs,
                    'phq9_score_bl': phq9_bl, 'phq9_score_fu': phq9_fu,
                    'madrs_score_bl': madrs_bl, 'madrs_score_fu': madrs_fu,
                    # Store actual response determined above
                    'will_respond': will_respond,
                    'will_remit': will_remit }

        # Assign Comorbidities (Specific for P001-P005)
        if patient_id == 'P001': patient_comorbidities_list = ["HTA"]
        elif patient_id == 'P002': patient_comorbidities_list = ["Trouble Anxieux NS"]
        elif patient_id == 'P003': patient_comorbidities_list = ["DLP", "Diabète"]
        elif patient_id == 'P004': patient_comorbidities_list = ["TPL"]
        elif patient_id == 'P005': patient_comorbidities_list = ["TU ROH", "HTA"]
        else: # Random assignment for others
            num_comorbidities = random.choices([0, 1, 2], weights=[0.40, 0.40, 0.20])[0]
            if num_comorbidities == 0: patient_comorbidities_list = ["Aucune"]
            else:
                if num_comorbidities <= len(liste_comorbidites): patient_comorbidities_list = random.sample(liste_comorbidites, num_comorbidities)
                else: patient_comorbidities_list = random.choices(liste_comorbidites, k=num_comorbidities)
        patient['comorbidities'] = "; ".join(patient_comorbidities_list)

        # Add other demographics
        patient['pregnant'] = '0' if sex == '1' else random.choices(['0', '1'], weights=[0.94, 0.06])[0]
        patient['cigarette_bl'] = random.choices(['0', '1'], weights=[0.74, 0.26])[0]
        patient['alcool_bl'] = random.choices(['0', '1'], weights=[0.85, 0.15])[0]
        patient['cocaine_bl'] = random.choices(['0', '1'], weights=[0.93, 0.07])[0]
        patient['hospitalisation_bl'] = random.choices(['0', '1'], weights=[0.75, 0.25])[0]
        patient['annees_education_bl'] = max(8, min(20, int(np.random.normal(14.2, 3.1))))
        patient['revenu_bl'] = max(12000, min(150000, int(np.random.lognormal(10.5, 0.8))))

        # Generate MADRS items (same as before)
        for item in range(1, 11):
            if item in [1, 2, 7, 9]: baseline_mean = 3.5
            elif item in [4, 5, 6]: baseline_mean = 2.8
            else: baseline_mean = 2.2
            baseline_item = max(0, min(6, int(np.random.normal(baseline_mean, 1.0))))
            followup_mean = baseline_item * (1 - madrs_improvement)
            followup_item = max(0, min(6, int(np.random.normal(followup_mean, 0.8))))
            patient[f'madrs_{item}_bl'] = baseline_item; patient[f'madrs_{item}_fu'] = followup_item
        madrs_bl_sum = sum(patient[f'madrs_{item}_bl'] for item in range(1, 11))
        adj_bl = madrs_bl / max(1, madrs_bl_sum) if madrs_bl_sum > 0 else 0
        for item in range(1, 11): patient[f'madrs_{item}_bl'] = min(6, max(0, int(patient[f'madrs_{item}_bl'] * adj_bl)))
        madrs_fu_sum = sum(patient[f'madrs_{item}_fu'] for item in range(1, 11))
        adj_fu = madrs_fu / max(1, madrs_fu_sum) if madrs_fu_sum > 0 else 0
        for item in range(1, 11): patient[f'madrs_{item}_fu'] = min(6, max(0, int(patient[f'madrs_{item}_fu'] * adj_fu)))

        # Generate PHQ9 daily items (same as before)
        days = [5, 10, 15, 20, 25, 30]; improvement_curve = []
        for day in days: progress = day/30.0; day_imp = improvement*(1/(1+math.exp(-10*(progress-0.5)))); improvement_curve.append(max(0, int(phq9_bl*(1-day_imp))))
        for k in range(1, len(improvement_curve)): delta=improvement_curve[k-1]-improvement_curve[k]; improvement_curve[k]=max(0, improvement_curve[k-1] - max(0, int(delta+random.randint(-1, 1))))
        for day_idx, day in enumerate(days): phq9_items=distribute_phq9_score(improvement_curve[day_idx]); [patient.update({f'phq9_day{day}_item{item}':score}) for item,score in enumerate(phq9_items,1)]

        # Generate final BFI scores, using the provisional N score and actual response
        patient = generate_bfi_scores(patient, provisional_neuroticism_score_bl, will_respond)

        patients.append(patient)

    logging.info(f"Generated main data for {len(patients)} patients.")
    return pd.DataFrame(patients)

# --- EMA, Side Effects, Nurse Notes Generation (Unchanged from previous full version) ---

def generate_ema_data(patient_df):
    # (Code as provided in previous response)
    logging.info("Generating EMA data...")
    MADRS_ITEMS = [f'madrs_{i}' for i in range(1, 11)]
    ANXIETY_ITEMS = [f'anxiety_{i}' for i in range(1, 6)]
    SLEEP, ENERGY, STRESS = 'sleep', 'energy', 'stress'
    SYMPTOMS = MADRS_ITEMS + ANXIETY_ITEMS + [SLEEP, ENERGY, STRESS]
    ema_entries = []
    if patient_df.empty: logging.warning("Patient DF empty for EMA generation."); return pd.DataFrame()
    for _, patient in patient_df.iterrows():
        patient_id = patient['ID']; protocol = patient['protocol']; improved = patient.get('will_respond', False)
        baseline_severity = patient.get('madrs_score_bl', 25) / 40.0; current_severity = baseline_severity
        protocol_effect={'HF - 10Hz': 0.8, 'BR - 18Hz': 0.65, 'iTBS': 0.5}; stability = protocol_effect.get(protocol, 0.6)
        patient_start_date = pd.to_datetime(patient['Timestamp'])
        for day in range(1, SIMULATION_DURATION_DAYS + 1):
            if random.random() < EMA_MISSING_DAY_PROB: continue
            day_effect = day / float(SIMULATION_DURATION_DAYS); improvement_factor = 0.7 if improved else 0.2
            target_severity = baseline_severity * (1 - day_effect * improvement_factor)
            noise_level = 0.15 * (1 - day_effect * 0.5)
            current_severity = current_severity * stability + target_severity * (1 - stability) + random.uniform(-noise_level, noise_level)
            current_severity = max(0, min(1, current_severity))
            n_entries_planned = random.choices([1, 2, 3], weights=EMA_ENTRIES_PER_DAY_WEIGHTS)[0]
            for entry_num in range(1, n_entries_planned + 1):
                if n_entries_planned > 1 and random.random() < EMA_MISSING_ENTRY_PROB: continue
                hour = random.randint(8, 21); minute = random.randint(0, 59)
                timestamp = patient_start_date + timedelta(days=day - 1, hours=hour, minutes=minute)
                entry_severity = max(0, min(1, current_severity * random.uniform(0.9, 1.1)))
                ema_entry = {'PatientID': patient_id, 'Timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'Day': day, 'Entry': entry_num}
                for item in range(1, 11): ema_entry[f'madrs_{item}'] = int(max(0, min(6, (entry_severity*6) + random.uniform(-1.5, 1.5))))
                for item in range(1, 6): ema_entry[f'anxiety_{item}'] = int(max(0, min(4, (entry_severity*4) + random.uniform(-1, 1))))
                ema_entry[SLEEP] = int(max(0, min(4, ((1-entry_severity)*4) + random.uniform(-1, 1)))); ema_entry[ENERGY] = int(max(0, min(4, ((1-entry_severity)*4) + random.uniform(-1, 1)))); ema_entry[STRESS] = int(max(0, min(4, (entry_severity*4) + random.uniform(-1, 1))))
                ema_entries.append(ema_entry)
    logging.info(f"Generated {len(ema_entries)} EMA entries.")
    return pd.DataFrame(ema_entries)

def generate_side_effects_data(patient_df):
    # (Code as provided in previous response - including specific P001-P003 profiles)
    logging.info("Generating side effects data (specific profiles for P001-P003)...")
    if not DB_INTERACTION_ENABLED: logging.warning("DB disabled, skipping SE DB insertion."); return
    num_saved = 0
    if patient_df.empty: logging.warning("Patient DF empty for SE generation."); return
    for _, patient in patient_df.iterrows():
        patient_id = patient['ID']; patient_start_date = pd.to_datetime(patient['Timestamp'])
        if patient_id == 'P001': logging.info(f"Skipping SE for P001."); continue
        elif patient_id == 'P002':
            num_reports = random.randint(1, 2); logging.info(f"Generating {num_reports} mild/mod SE report(s) for P002.")
            for i in range(num_reports):
                day_offset=random.randint(3, 15); report_date=patient_start_date+timedelta(days=day_offset)
                report_data={'patient_id':patient_id, 'report_date':report_date.strftime('%Y-%m-%d'), 'created_by':'Simulation (P002)'}
                report_data['headache']=random.choices([0,1,2],weights=[0.3,0.5,0.2])[0]; report_data['nausea']=random.choices([0,1],weights=[0.8,0.2])[0]
                report_data['scalp_discomfort']=random.choices([0,1,2],weights=[0.4,0.4,0.2])[0]; report_data['dizziness']=random.choices([0,1],weights=[0.9,0.1])[0]
                report_data['other_effects']=random.choice(['', 'Légère fatigue passagère']) if random.random()<0.3 else ''; report_data['notes']=random.choice(['Signalé.', 'Observé.'])
                try: save_side_effect_report(report_data); num_saved+=1
                except Exception as e: logging.error(f"Failed P002 SE report: {e}")
        elif patient_id == 'P003':
            num_reports = random.randint(3, 4); logging.info(f"Generating {num_reports} sig SE report(s) for P003.")
            for i in range(num_reports):
                day_offset=random.randint(2, 20); report_date=patient_start_date+timedelta(days=day_offset)
                report_data={'patient_id':patient_id, 'report_date':report_date.strftime('%Y-%m-%d'), 'created_by':'Simulation (P003)'}
                report_data['headache']=random.choices([0,1,2,3,4,5],weights=[0.1,0.2,0.3,0.2,0.1,0.1])[0]; report_data['nausea']=random.choices([0,1,2],weights=[0.5,0.3,0.2])[0]
                report_data['scalp_discomfort']=random.choices([0,1,2,3],weights=[0.2,0.3,0.3,0.2])[0]; report_data['dizziness']=random.choices([0,1,2,3],weights=[0.6,0.2,0.1,0.1])[0]
                report_data['other_effects']=random.choice(['','Fatigue marquée','Diff concentration','Acouphènes légers']) if random.random()<0.5 else ''; report_data['notes']=random.choice(['Gêne importante.', 'Pause nécessaire.', 'Estompent après 1h.'])
                try: save_side_effect_report(report_data); num_saved+=1
                except Exception as e: logging.error(f"Failed P003 SE report: {e}")
        else: # Random for others
            num_reports = random.randint(1, 5)
            for i in range(num_reports):
                day_offset=random.randint(1, SIMULATION_DURATION_DAYS); prob_cutoff=SIDE_EFFECT_PROB_INITIAL if day_offset<=SIDE_EFFECT_DECAY_DAY else SIDE_EFFECT_PROB_LATER
                if random.random()<prob_cutoff:
                    report_date=patient_start_date+timedelta(days=day_offset)
                    report_data={'patient_id':patient_id, 'report_date':report_date.strftime('%Y-%m-%d'), 'created_by':'Simulation (Random)'}
                    report_data['headache']=random.choices([0,1,2,3,4],weights=[0.6,0.2,0.1,0.05,0.05])[0]; report_data['nausea']=random.choices([0,1,2],weights=[0.8,0.15,0.05])[0]
                    report_data['scalp_discomfort']=random.choices([0,1,2,3],weights=[0.5,0.3,0.15,0.05])[0]; report_data['dizziness']=random.choices([0,1,2],weights=[0.75,0.15,0.10])[0]
                    report_data['other_effects']=random.choice(['','Fatigue légère','']) if random.random()<0.1 else ''; report_data['notes']=random.choice(['','Mentionné passé.','Tolère ok','']) if random.random()<0.2 else ''
                    try: save_side_effect_report(report_data); num_saved+=1
                    except Exception as e: logging.error(f"Failed random SE report for {patient_id}: {e}")
    logging.info(f"Generated/attempted {num_saved} SE reports.")

def generate_nurse_notes_data(patient_df):
    # (Code as provided in previous response)
    logging.info("Generating nurse notes data...")
    if not DB_INTERACTION_ENABLED: logging.warning("DB disabled, skipping nurse note DB insertion."); return
    num_saved=0
    if patient_df.empty: logging.warning("Patient DF empty for nurse notes."); return
    for _,patient in patient_df.iterrows():
        patient_id=patient['ID']; patient_start_date=pd.to_datetime(patient['Timestamp'])
        will_respond=patient.get('will_respond',False); will_remit=patient.get('will_remit',False); protocol=patient.get('protocol','Unknown')
        initial_day=random.randint(1,3); initial_note={'patient_id':patient_id,'created_by':'Simulation','goal_status':"Not Started",'objectives':f"Init {protocol}. Obj: Réduc MADRS >50%.",'tasks':"EMA. Rapporter ES.",'comments':"Motivé.",'target_symptoms':"Humeur, Anhédonie, Insomnie",'planned_interventions':f"TMS {protocol}."}
        try: save_nurse_inputs(**initial_note); num_saved+=1
        except Exception as e: logging.error(f"Failed init note {patient_id}: {e}")
        mid_day=random.randint(12,18); mid_status="In Progress"; mid_comment="Amélio légère." if random.random()<0.6 else "Stabilité."
        if not will_respond and random.random()<0.3: mid_comment="Frustration."; mid_status="On Hold"
        mid_note=initial_note.copy(); mid_note.update({'goal_status':mid_status,'comments':mid_comment,'created_by':'Simulation'})
        try: save_nurse_inputs(**mid_note); num_saved+=1
        except Exception as e: logging.error(f"Failed mid note {patient_id}: {e}")
        final_day=random.randint(28,30)
        if will_remit: final_status="Achieved"; final_comment="Rémission."
        elif will_respond: final_status="Achieved"; final_comment="Réponse >50%."
        else: final_status="Revised"; final_comment="Réponse insuffisante."
        final_note=initial_note.copy(); final_note.update({'goal_status':final_status,'comments':final_comment,'created_by':'Simulation','tasks':"Planif suivi.",'planned_interventions':"Fin protocole." if will_respond else "Réévaluation."})
        try: save_nurse_inputs(**final_note); num_saved+=1
        except Exception as e: logging.error(f"Failed final note {patient_id}: {e}")
    logging.info(f"Generated/attempted {num_saved} nurse notes.")

# --- Main Execution ---
if __name__ == "__main__":
    logging.info("--- Starting Data Simulation ---")
    if DB_INTERACTION_ENABLED: logging.info("Init DB schema..."); initialize_database()
    else: logging.warning("DB disabled, schema not init.")

    patient_data_df = generate_patient_data() # Includes BFI
    cols_to_drop = ['will_respond', 'will_remit'] # Keep flags if needed by downstream funcs, else drop before saving final
    patient_data_df_clean = patient_data_df.drop(columns=[col for col in cols_to_drop if col in patient_data_df.columns])

    patient_csv_path = os.path.join('data', 'patient_data_with_protocol_simulated.csv')
    patient_data_simple_csv_path = os.path.join('data', 'patient_data_simulated.csv')
    patient_data_df_clean.to_csv(patient_csv_path, index=False)
    patient_data_df_clean.to_csv(patient_data_simple_csv_path, index=False)
    logging.info(f"Saved main patient data ({len(patient_data_df_clean)}) to CSVs.")

    # Pass original df if EMA needs 'will_respond'
    ema_data_df = generate_ema_data(patient_data_df)
    ema_csv_path = os.path.join('data', 'simulated_ema_data.csv')
    ema_data_df.to_csv(ema_csv_path, index=False)
    logging.info(f"Saved {len(ema_data_df)} EMA entries.")

    generate_side_effects_data(patient_data_df) # Pass original if needed
    generate_nurse_notes_data(patient_data_df) # Pass original if needed

    config_content = f"""
paths:
  patient_data_with_protocol: "{patient_csv_path}"
  patient_data: "{patient_data_simple_csv_path}"
  simulated_ema_data: "{ema_csv_path}"
mappings:
  madrs_items:
    1: Tristesse Apparente
    2: Tristesse Signalée
    3: Tension Intérieure
    4: Sommeil Réduit
    5: Appétit Réduit
    6: Difficultés de Concentration
    7: Lassitude
    8: Incapacité à Ressentir
    9: Pensées Pessimistes
    10: Pensées Suicidaires
"""
    os.makedirs('config', exist_ok=True); config_path = os.path.join('config', 'config.yaml')
    try:
        with open(config_path, 'w', encoding='utf-8') as f: f.write(config_content)
        logging.info(f"Updated {config_path}")
    except Exception as e: logging.error(f"Failed write {config_path}: {e}")
    logging.info("--- Simulation complete. ---")
    print("\nSim complete. Run app: 'streamlit run app.py'")
    print(f"Log: {log_file}")