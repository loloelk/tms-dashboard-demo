# Patient Dashboard for TMS Treatment Monitoring

A comprehensive clinical dashboard for monitoring patients undergoing Transcranial Magnetic Stimulation (TMS) for depression treatment. This application enables clinicians to track patient outcomes across different TMS protocols (HF-10Hz, iTBS, BR-18Hz), visualize symptom networks, and record clinical observations.

## Features

- **Patient Overview**: Detailed view of individual patient demographics, clinical history, and treatment progress
- **Clinical Assessments**: Visualization of MADRS, PHQ-9, and PID-5 scores with baseline and follow-up comparisons
- **Symptom Networks**: Interactive visualization of relationships between symptoms based on ecological momentary assessment (EMA) data
- **Protocol Analysis**: Statistical comparison of treatment effectiveness across different TMS protocols
- **Nurse Input Management**: Interface for recording clinical objectives, behavioral activation tasks, and notes
- **Side Effect Tracking**: Monitoring and visualization of treatment side effects over time

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/patient-dashboard.git
cd patient-dashboard
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The application uses a YAML configuration file located at `config/config.yaml` that specifies:

- Data file paths
- MADRS item mappings
- PID-5 dimension mappings

## Data Preparation

The application requires the following data files:

1. **Patient Data**: CSV file with patient demographics, clinical history, and assessment scores
2. **EMA Data**: CSV file with daily mood and symptom tracking data
3. **Nurse Inputs**: CSV file with clinical notes and objectives

You can generate simulated data for testing:

```bash
python enhanced_simulate_patient_data.py
```

## Usage

Run the application:

```bash
streamlit run app.py
```

The dashboard will be available at [http://localhost:8501](http://localhost:8501).

## Directory Structure

```
patient-dashboard/
├── app.py                        # Main application entry point
├── components/                   # UI components
│   ├── sidebar.py                # Navigation and patient selection
│   ├── dashboard.py              # Main patient dashboard view
│   ├── nurse_inputs.py           # Nurse notes and objectives UI
│   ├── pid5_details.py           # PID-5 personality inventory analysis
│   ├── protocol_analysis.py      # Protocol comparison statistics
│   ├── side_effects.py           # Side effect tracking interface
│   └── overview.py               # Summary statistics dashboard
├── services/                     # Business logic
│   ├── data_loader.py            # Data loading and validation
│   ├── network_analysis.py       # Symptom network analysis
│   └── nurse_service.py          # Nurse input management
├── utils/                        # Utility functions
│   ├── error_handler.py          # Centralized error handling
│   ├── logging_config.py         # Logging configuration
│   ├── config_manager.py         # Configuration management
│   └── visualization.py          # Shared visualization utilities
├── assets/                       # Static assets
│   └── styles.css                # CSS styling
├── config/                       # Configuration files
│   └── config.yaml               # Application configuration
├── data/                         # Data storage (gitignored)
│   ├── patient_data_simulated.csv
│   ├── patient_data_with_protocol_simulated.csv
│   ├── simulated_ema_data.csv
│   └── nurse_inputs.csv
├── enhanced_simulate_patient_data.py  # Data simulation script
└── requirements.txt              # Python dependencies
```

## Data Structure

### Patient Data
Contains demographics, clinical history, and assessment scores:
- Demographics (age, sex, etc.)
- Treatment history (psychotherapy, ECT, rTMS, tDCS)
- Assessment scores (MADRS, PHQ-9, PID-5)
- Both baseline and follow-up measurements

### EMA Data
Daily mood and symptom tracking including:
- MADRS item scores (1-10)
- Anxiety item scores (1-5)
- Sleep, energy, and stress scores
- Timestamp and day information

### Nurse Inputs
Clinical observations and treatment objectives:
- SMART objectives
- Behavioral activation tasks
- Clinical comments

## Development

### Adding New Features

1. Create component in the appropriate file under `components/`
2. Add business logic in `services/` if needed
3. Register new pages in the sidebar navigation in `sidebar.py`
4. Update the routing in `app.py`

### Data Processing Pipeline

The application follows this data flow:
1. Load data via `data_loader.py`
2. Process and analyze with service modules
3. Present in UI components
4. Store user inputs back to CSV files

## Deployment

The application can be deployed in several ways:

1. **Streamlit Cloud**: For simple cloud hosting
   ```
   streamlit deploy
   ```

2. **Docker Deployment**: For containerized environments
   ```
   docker build -t patient-dashboard .
   docker run -p 8501:8501 patient-dashboard
   ```

3. **On-Premises**: For clinical environments with private data
   - Deploy on a secure, HIPAA-compliant server
   - Implement appropriate authentication and encryption

## Acknowledgments

- Clinical data structure based on standard depression treatment protocols
- Symptom network analysis inspired by current research in dynamic symptom interactions
- Developed for research and clinical monitoring purposes
