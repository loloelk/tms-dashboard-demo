# enhanced_simulate_patient_data.py

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import random
import math

# Configuration Parameters
NUM_PATIENTS = 50
PROTOCOLS = ['HF - 10Hz', 'iTBS', 'BR - 18Hz']

# Protocol response probabilities (HF > BR > iTBS)
PROTOCOL_RESPONSE_RATES = {
    'HF - 10Hz': 0.65,    # 65% response rate
    'BR - 18Hz': 0.48,    # 48% response rate
    'iTBS': 0.36          # 36% response rate
}

PROTOCOL_REMISSION_RATES = {
    'HF - 10Hz': 0.42,    # 42% remission rate
    'BR - 18Hz': 0.28,    # 28% remission rate
    'iTBS': 0.20          # 20% remission rate
}

START_DATE = datetime(2024, 1, 1)

# Create data directory if needed
os.makedirs('data', exist_ok=True)

def generate_patient_data():
    """Generate patient data with realistic clinical distributions"""
    patients = []
    
    for i in range(1, NUM_PATIENTS + 1):
        patient_id = f'P{str(i).zfill(3)}'
        
        # Basic patient information with age distribution similar to clinical sample
        age = int(np.random.normal(43.2, 12.5))  # Mean 43.2, SD 12.5
        age = max(18, min(age, 75))  # Limit to reasonable range
        
        sex = random.choices(['1', '2'], weights=[0.42, 0.58])[0]  # More female patients (58%)
        protocol = random.choice(PROTOCOLS)
        
        # Treatment history (based on common distributions in depression trials)
        psychotherapie = random.choices(['0', '1'], weights=[0.35, 0.65])[0]  # 65% had previous therapy
        ect = random.choices(['0', '1'], weights=[0.92, 0.08])[0]  # 8% had ECT
        rtms = random.choices(['0', '1'], weights=[0.85, 0.15])[0]  # 15% had rTMS
        tdcs = random.choices(['0', '1'], weights=[0.95, 0.05])[0]  # 5% had tDCS
        
        # Response probability based on protocol
        will_respond = random.random() < PROTOCOL_RESPONSE_RATES[protocol]
        will_remit = random.random() < PROTOCOL_REMISSION_RATES[protocol]
        
        # PHQ-9 scores
        phq9_bl = int(np.random.normal(18.2, 4.3))  # Moderately severe to severe
        phq9_bl = max(10, min(phq9_bl, 27))  # Range 10-27
        
        if will_respond:
            # >50% improvement
            improvement = random.uniform(0.51, 0.85)
        else:
            # <50% improvement
            improvement = random.uniform(0.15, 0.49)
            
        phq9_fu = max(0, int(phq9_bl * (1 - improvement)))
        
        # MADRS scores - realistic baseline and improvement based on PHQ-9
        # Convert PHQ-9 to MADRS scale (approximate conversion)
        madrs_bl = int(phq9_bl * 1.4)  # PHQ-9 to MADRS approximate conversion
        madrs_bl = max(15, min(madrs_bl, 40))  # Reasonable MADRS range
        
        # MADRS improvement typically aligns with PHQ-9 improvement but with some variation
        madrs_improvement = improvement * random.uniform(0.8, 1.2)
        
        # If the patient will reach remission, ensure MADRS score goes below 10
        if will_remit:
            madrs_fu = random.randint(4, 9)
        else:
            madrs_fu = max(10, int(madrs_bl * (1 - madrs_improvement)))
        
        # Create patient record
        patient = {
            'ID': patient_id,
            'age': age,
            'sexe': sex,
            'protocol': protocol,
            'Timestamp': (START_DATE + timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S'),
            'psychotherapie_bl': psychotherapie,
            'ect_bl': ect,
            'rtms_bl': rtms,
            'tdcs_bl': tdcs,
            'phq9_score_bl': phq9_bl,
            'phq9_score_fu': phq9_fu,
            'madrs_score_bl': madrs_bl,
            'madrs_score_fu': madrs_fu,
            'objectives': '',
            'tasks': '',
            'comments': ''
        }
        
        # Add comorbidities with realistic distribution
        comorbidities = ["None", "Anxiety", "PTSD", "Substance use", "Personality disorder", "Bipolar II"]
        weights = [0.30, 0.35, 0.15, 0.10, 0.07, 0.03]  # Anxiety most common comorbidity
        patient['comorbidities'] = random.choices(comorbidities, weights=weights)[0]
        
        # Additional demographics
        patient['pregnant'] = '0' if sex == '1' else random.choices(['0', '1'], weights=[0.94, 0.06])[0]
        patient['cigarette_bl'] = random.choices(['0', '1'], weights=[0.74, 0.26])[0]  # 26% smokers
        patient['alcool_bl'] = random.choices(['0', '1'], weights=[0.85, 0.15])[0]  # 15% alcohol issues
        patient['cocaine_bl'] = random.choices(['0', '1'], weights=[0.93, 0.07])[0]  # 7% cocaine use
        patient['hospitalisation_bl'] = random.choices(['0', '1'], weights=[0.75, 0.25])[0]  # 25% prior hospitalization
        
        # Education and income with realistic distributions
        patient['annees_education_bl'] = max(8, min(20, int(np.random.normal(14.2, 3.1))))
        patient['revenu_bl'] = int(np.random.lognormal(10.5, 0.8))  # Lognormal distribution for income
        patient['revenu_bl'] = max(12000, min(150000, patient['revenu_bl']))  # Range 12k-150k
        
        # Generate MADRS item scores
        for item in range(1, 11):
            # Different items have different typical severities
            if item in [1, 2, 7, 9]:  # Core depression items often higher
                baseline_mean = 3.5
            elif item in [4, 5, 6]:  # Functional items moderate
                baseline_mean = 2.8
            else:  # Other items more variable
                baseline_mean = 2.2
                
            # Add some noise around the mean
            baseline_item = max(0, min(6, int(np.random.normal(baseline_mean, 1.0))))
            
            # Follow-up scores show relative improvement 
            followup_mean = baseline_item * (1 - madrs_improvement)
            followup_item = max(0, min(6, int(np.random.normal(followup_mean, 0.8))))
            
            patient[f'madrs_{item}_bl'] = baseline_item
            patient[f'madrs_{item}_fu'] = followup_item
        
        # Make sure item scores sum to total score (approximately)
        # Adjust to match the total MADRS score
        madrs_items_bl_sum = sum(patient[f'madrs_{item}_bl'] for item in range(1, 11))
        adjustment_factor = madrs_bl / max(1, madrs_items_bl_sum)
        
        for item in range(1, 11):
            patient[f'madrs_{item}_bl'] = min(6, max(0, int(patient[f'madrs_{item}_bl'] * adjustment_factor)))
        
        # Do the same for follow-up scores
        madrs_items_fu_sum = sum(patient[f'madrs_{item}_fu'] for item in range(1, 11))
        adjustment_factor = madrs_fu / max(1, madrs_items_fu_sum)
        
        for item in range(1, 11):
            patient[f'madrs_{item}_fu'] = min(6, max(0, int(patient[f'madrs_{item}_fu'] * adjustment_factor)))
        
        # Generate PHQ-9 daily scores showing proper trajectory
        days = [5, 10, 15, 20, 25, 30]
        
        # Create a realistic improvement curve (not necessarily linear)
        # Usually more improvement in the beginning, then plateau
        improvement_curve = []
        for day in days:
            # Sigmoid-like improvement curve
            progress = day / 30.0
            day_improvement = improvement * (1 / (1 + math.exp(-10 * (progress - 0.5))))
            expected_score = max(0, int(phq9_bl * (1 - day_improvement)))
            improvement_curve.append(expected_score)
            
        # Make minor adjustments to create natural variation
        for i in range(1, len(improvement_curve)):
            # Add slight noise but maintain general downward trend
            delta = improvement_curve[i-1] - improvement_curve[i]
            improvement_curve[i] = improvement_curve[i-1] - max(0, int(delta + random.randint(-1, 1)))
        
        # Distribute PHQ-9 items for each day
        for day_idx, day in enumerate(days):
            expected_score = improvement_curve[day_idx]
            
            # Create item-level scores that sum to the expected total
            phq9_items = distribute_phq9_score(expected_score)
            
            for item, score in enumerate(phq9_items, 1):
                patient[f'phq9_day{day}_item{item}'] = score
        
        # Add PID-5 scores
        generate_pid5_scores(patient, will_respond)
        
        patients.append(patient)
    
    return pd.DataFrame(patients)

def distribute_phq9_score(total_score):
    """Distribute a total PHQ-9 score into 9 item scores realistically"""
    # PHQ-9 items 1 (anhedonia) and 2 (depressed mood) are often higher
    # Item 9 (suicidal thoughts) is often lower
    
    if total_score == 0:
        return [0] * 9
    
    # Start with weight distribution for items
    weights = [1.5, 1.5, 1.0, 1.0, 0.8, 1.0, 1.0, 0.8, 0.5]  # Higher weight for core symptoms
    normalized_weights = [w/sum(weights) for w in weights]
    
    # First pass distribution
    raw_distribution = [total_score * w for w in normalized_weights]
    
    # Round and ensure within 0-3 range
    items = [min(3, max(0, round(val))) for val in raw_distribution]
    
    # Adjust to match the target total score
    current_sum = sum(items)
    
    # If we need to add points
    while current_sum < total_score and max(items) < 3:
        # Prioritize increasing items that aren't at maximum yet
        eligible_indices = [i for i, score in enumerate(items) if score < 3]
        if eligible_indices:
            idx = random.choices(eligible_indices, 
                                [normalized_weights[i] for i in eligible_indices])[0]
            items[idx] += 1
            current_sum += 1
        else:
            break
            
    # If we need to remove points
    while current_sum > total_score and min(items) > 0:
        # Prioritize decreasing items with lower weights
        eligible_indices = [i for i, score in enumerate(items) if score > 0]
        if eligible_indices:
            # Choose indices with probability inversely proportional to weights
            inverse_weights = [1/normalized_weights[i] for i in eligible_indices]
            sum_inverse = sum(inverse_weights)
            inv_normalized = [w/sum_inverse for w in inverse_weights]
            
            idx = random.choices(eligible_indices, inv_normalized)[0]
            items[idx] -= 1
            current_sum -= 1
        else:
            break
    
    return items

def generate_pid5_scores(patient, will_respond):
    """Generate PID-5 personality inventory scores"""
    # Define domains and their items
    domains = {
        'Affect Négatif': [8, 9, 10, 11, 15],
        'Détachement': [4, 13, 14, 16, 18],
        'Antagonisme': [17, 19, 20, 22, 25],
        'Désinhibition': [1, 2, 3, 5, 6],
        'Psychoticisme': [7, 12, 21, 23, 24]
    }
    
    # Initialize PID-5 total scores
    pid5_bl = random.randint(65, 95)
    
    # PID-5 typically improves less dramatically than symptom measures
    if will_respond:
        improvement = random.uniform(0.15, 0.25)
    else:
        improvement = random.uniform(0.05, 0.15)
        
    pid5_fu = int(pid5_bl * (1 - improvement))
    
    patient['pid5_score_bl'] = pid5_bl
    patient['pid5_score_fu'] = pid5_fu
    
    # Generate domain-level scores that sum approximately to total
    domain_weights = {
        'Affect Négatif': 1.3,      # Higher in depression
        'Détachement': 1.1,         # Higher in depression
        'Antagonisme': 0.8,
        'Désinhibition': 0.9,
        'Psychoticisme': 0.7
    }
    
    # Normalize weights
    total_weight = sum(domain_weights.values())
    normalized_weights = {k: v/total_weight for k, v in domain_weights.items()}
    
    # Distribute PID-5 scores by domain
    for domain, items in domains.items():
        # Domain baseline score (approximately)
        domain_bl_target = int(pid5_bl * normalized_weights[domain])
        
        # Generate item-level scores
        for item in items:
            # Items vary from 0 to 4
            item_bl = random.randint(1, 4)
            
            # Follow-up scores show some improvement if patient responds to treatment
            if will_respond:
                item_fu = max(0, item_bl - random.randint(0, 2))
            else:
                item_fu = max(0, item_bl - random.randint(0, 1))
                
            patient[f'pid5_{item}_bl'] = item_bl
            patient[f'pid5_{item}_fu'] = item_fu
    
    return patient

def generate_ema_data():
    """Generate simulated EMA data for patients"""
    # Define symptoms
    MADRS_ITEMS = [f'madrs_{i}' for i in range(1, 11)]
    ANXIETY_ITEMS = [f'anxiety_{i}' for i in range(1, 6)]
    SLEEP = 'sleep'
    ENERGY = 'energy'
    STRESS = 'stress'
    SYMPTOMS = MADRS_ITEMS + ANXIETY_ITEMS + [SLEEP, ENERGY, STRESS]
    
    ema_entries = []
    
    # Get patient data to align EMA trends with outcomes
    patient_df = pd.read_csv('data/patient_data_simulated.csv')
    
    for _, patient in patient_df.iterrows():
        patient_id = patient['ID']
        protocol = patient['protocol']
        
        # Calculate if patient improved (based on MADRS)
        improved = patient['madrs_score_fu'] < patient['madrs_score_bl']
        
        # Protocol effectiveness influences daily fluctuations
        protocol_effect = {
            'HF - 10Hz': 0.8,  # Good stability
            'BR - 18Hz': 0.65, # Moderate stability
            'iTBS': 0.5        # More fluctuation
        }
        
        stability = protocol_effect[protocol]
        
        # Baseline symptom levels (from MADRS)
        baseline_severity = patient['madrs_score_bl'] / 40  # Normalize to 0-1 scale
        
        # Track ongoing severity that will change over time
        current_severity = baseline_severity
        
        for day in range(1, 31):
            # Number of entries per day varies, with higher compliance early in treatment
            n_entries = random.choices([1, 2, 3], 
                                     weights=[0.2, 0.5, 0.3])[0]
            
            # Treatment effect increases over time
            day_effect = day / 30
            
            if improved:
                # Improving trajectory
                target_severity = baseline_severity * (1 - day_effect * 0.6)
            else:
                # Non-improving trajectory
                target_severity = baseline_severity * (1 - day_effect * 0.2)
            
            # Move current severity toward target with some noise
            current_severity = current_severity * stability + target_severity * (1-stability)
            current_severity += random.uniform(-0.1, 0.1)  # Add noise
            current_severity = max(0, min(1, current_severity))  # Keep in range 0-1
            
            for entry in range(1, n_entries+1):
                # Create timestamp
                hour = random.randint(8, 21)
                minute = random.randint(0, 59)
                timestamp = START_DATE + timedelta(days=day-1, hours=hour, minutes=minute)
                
                # Entry-level severity fluctuates slightly
                entry_severity = current_severity * random.uniform(0.9, 1.1)
                entry_severity = max(0, min(1, entry_severity))
                
                # Create entry
                ema_entry = {
                    'PatientID': patient_id,
                    'Timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'Day': day,
                    'Entry': entry
                }
                
                # Add symptom scores with realistic correlations
                # MADRS items (scaled to 0-6)
                for item in range(1, 11):
                    base_score = entry_severity * 6
                    item_score = int(max(0, min(6, base_score + random.uniform(-1.5, 1.5))))
                    ema_entry[f'madrs_{item}'] = item_score
                
                # Anxiety items (scaled to 0-4)
                for item in range(1, 6):
                    # Anxiety correlates with depression but has own fluctuations
                    base_score = entry_severity * 4
                    item_score = int(max(0, min(4, base_score + random.uniform(-1, 1))))
                    ema_entry[f'anxiety_{item}'] = item_score
                
                # Sleep and energy are inversely related to severity
                sleep_score = int(max(0, min(4, (1 - entry_severity) * 4 + random.uniform(-1, 1))))
                energy_score = int(max(0, min(4, (1 - entry_severity) * 4 + random.uniform(-1, 1))))
                
                # Stress positively correlates with severity
                stress_score = int(max(0, min(4, entry_severity * 4 + random.uniform(-1, 1))))
                
                ema_entry[SLEEP] = sleep_score
                ema_entry[ENERGY] = energy_score
                ema_entry[STRESS] = stress_score
                
                ema_entries.append(ema_entry)
    
    return pd.DataFrame(ema_entries)

def generate_whoqol_data(patients_df):
    """Add WHOQOL-BREF quality of life data to patient records"""
    
    for index, row in patients_df.iterrows():
        # Get improvement status from MADRS
        madrs_improvement = (row['madrs_score_bl'] - row['madrs_score_fu']) / row['madrs_score_bl']
        
        # WHOQOL items (1-26)
        for item in range(1, 27):
            # Baseline scores tend to be low when depression is high
            whoqol_bl = random.randint(1, 3)
            
            # Follow-up scores improve in relation to symptom improvement
            if madrs_improvement > 0.5:  # Good improvement
                whoqol_fu = min(5, whoqol_bl + random.randint(1, 2))
            elif madrs_improvement > 0.3:  # Moderate improvement
                whoqol_fu = min(5, whoqol_bl + random.randint(0, 2))
            else:  # Little improvement
                whoqol_fu = min(5, whoqol_bl + random.randint(0, 1))
            
            patients_df.at[index, f'whoqol_bref_item{item}_bl'] = whoqol_bl
            patients_df.at[index, f'whoqol_bref_item{item}_fu'] = whoqol_fu
        
        # Calculate domain scores
        domains = {
            1: list(range(3, 10)),       # Physical health: items 3-9
            2: list(range(10, 16)),      # Psychological: items 10-15
            3: list(range(16, 19)),      # Social relationships: items 16-18
            4: list(range(19, 27))       # Environment: items 19-26
        }
        
        for domain, items in domains.items():
            # Calculate raw domain scores
            domain_bl_raw = sum(patients_df.at[index, f'whoqol_bref_item{item}_bl'] for item in items)
            domain_fu_raw = sum(patients_df.at[index, f'whoqol_bref_item{item}_fu'] for item in items)
            
            # Save raw scores
            patients_df.at[index, f'whoqol_bref_domain{domain}_raw_bl'] = domain_bl_raw
            patients_df.at[index, f'whoqol_bref_domain{domain}_raw_fu'] = domain_fu_raw
            
            # Calculate standardized scores (0-100)
            # Formula: (raw score - 4) × (100/16) for domain 1
            # Formula: (raw score - 5) × (100/20) for domain 2
            # Formula: (raw score - 3) × (100/12) for domain 3
            # Formula: (raw score - 8) × (100/32) for domain 4
            
            if domain == 1:
                domain_bl_std = (domain_bl_raw - 4) * (100/16)
                domain_fu_std = (domain_fu_raw - 4) * (100/16)
            elif domain == 2:
                domain_bl_std = (domain_bl_raw - 5) * (100/20)
                domain_fu_std = (domain_fu_raw - 5) * (100/20)
            elif domain == 3:
                domain_bl_std = (domain_bl_raw - 3) * (100/12)
                domain_fu_std = (domain_fu_raw - 3) * (100/12)
            else:
                domain_bl_std = (domain_bl_raw - 8) * (100/32)
                domain_fu_std = (domain_fu_raw - 8) * (100/32)
            
            # Save standardized scores
            patients_df.at[index, f'whoqol_bref_domain{domain}_std_bl'] = domain_bl_std
            patients_df.at[index, f'whoqol_bref_domain{domain}_std_fu'] = domain_fu_std
        
        # Calculate total scores
        total_bl_std = sum(patients_df.at[index, f'whoqol_bref_domain{domain}_std_bl'] for domain in domains) / 4
        total_fu_std = sum(patients_df.at[index, f'whoqol_bref_domain{domain}_std_fu'] for domain in domains) / 4
        
        patients_df.at[index, 'whoqol_bref_total_std_bl'] = total_bl_std
        patients_df.at[index, 'whoqol_bref_total_std_fu'] = total_fu_std
    
    return patients_df

# Main execution
if __name__ == "__main__":
    print("Generating patient data...")
    patient_data = generate_patient_data()
    
    # Add WHOQOL-BREF data
    patient_data = generate_whoqol_data(patient_data)
    
    # Fill any missing columns with NaN to ensure compatibility
    patient_data.to_csv('data/patient_data_simulated.csv', index=False)
    patient_data.to_csv('data/patient_data_with_protocol_simulated.csv', index=False)
    print(f"Saved patient data for {len(patient_data)} patients")
    
    # Generate and save EMA data
    print("Generating EMA data...")
    ema_data = generate_ema_data()
    ema_data.to_csv('data/simulated_ema_data.csv', index=False)
    print(f"Saved {len(ema_data)} EMA entries")
    
    # Create empty nurse inputs file if it doesn't exist
    if not os.path.exists('data/nurse_inputs.csv'):
        pd.DataFrame(columns=['ID', 'objectives', 'tasks', 'comments']).to_csv('data/nurse_inputs.csv', index=False)
        print("Created empty nurse inputs file")
    
    # Create config.yaml file
    config_content = """
paths:
  patient_data_with_protocol: "data/patient_data_with_protocol_simulated.csv"
  patient_data: "data/patient_data_simulated.csv"
  nurse_inputs: "data/nurse_inputs.csv"
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
    with open('config/config.yaml', 'w') as f:
        f.write(config_content)
    print("Updated config.yaml file")
    
    print("\nSimulation complete. You can now run the application with 'streamlit run app.py'")