import pandas as pd
import json
import os
import re

# Local replacement for `us.states.lookup()`
US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY"
}
def lookup_state_abbr(state_name):
    key = state_name.strip().lower()
    return US_STATES.get(key, state_name.upper())

def load_input_file(input_path):
    ext = os.path.splitext(input_path)[1].lower()
    if ext == '.xlsx':
        df = pd.read_excel(input_path)
    elif ext == '.csv':
        df = pd.read_csv(input_path)
    elif ext == '.txt':
        df = pd.read_csv(input_path, delimiter='\t')
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    df.columns = df.columns.map(lambda col: re.sub(r'\s+', ' ', col).strip().lower())
    if df.empty:
        raise ValueError("Uploaded file is empty or unreadable.")
    return df

def extract_to_fields(df):
    required = [
        "customer name", "ship to address 1", "ship to address 2",
        "city", "state", "zip", "ship to country"
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")
    return pd.DataFrame({
        'ToName':    df['customer name'],
        'ToStreet1': df['ship to address 1'],
        'ToStreet2': df['ship to address 2'],
        'ToCity':    df['city'],
        'ToState':   df['state'],
        'ToZip':     df['zip'],
        'ToCountry': df['ship to country'],
    })

def clean_and_validate(parsed):
    parsed = parsed.fillna('').apply(lambda col: col.str.strip() if col.dtype == "object" else col)
    for col in ['ToStreet1', 'ToStreet2', 'ToCity', 'ToState']:
        parsed[col] = parsed[col].str.upper()
    parsed['ToState'] = parsed['ToState'].apply(lookup_state_abbr)
    return parsed

def validate_rows(parsed):
    required_fields = ['ToName', 'ToStreet1', 'ToCity', 'ToZip', 'ToState', 'ToCountry']
    validation_df = parsed.copy().fillna('').astype(str)
    missing_mask = validation_df[required_fields].apply(lambda row: row.str.strip() == '', axis=1)
    invalid_rows = parsed[missing_mask.any(axis=1)]
    valid_rows = parsed[~missing_mask.any(axis=1)]
    return valid_rows, invalid_rows

def merge_from_data(parsed, from_data):
    final_columns = [
        'FromCountry', 'FromName', 'FromCompany', 'FromPhone',
        'FromStreet1', 'FromStreet2', 'FromCity', 'FromZip', 'FromState',
        'ToCountry', 'ToName', 'ToCompany',
        'ToStreet1', 'ToStreet2', 'ToCity', 'ToZip', 'ToState',
        'Length', 'Height', 'Width', 'Weight'
    ]
    final_df = pd.DataFrame(columns=final_columns)
    final_df['ToName'] = parsed['ToName']
    final_df['ToStreet1'] = parsed['ToStreet1']
    final_df['ToStreet2'] = parsed['ToStreet2']
    final_df['ToCity'] = parsed['ToCity']
    final_df['ToState'] = parsed['ToState']
    final_df['ToZip'] = parsed['ToZip']
    final_df['ToCountry'] = parsed['ToCountry']
    final_df['ToCompany'] = ""
    for key, value in from_data.items():
        if key in final_df.columns:
            final_df[key] = value
    final_df['Length'] = 0
    final_df['Height'] = 0
    final_df['Width'] = 0
    final_df['Weight'] = 0
    final_df = final_df.fillna('')
    return final_df

def run_parser(input_path, from_json_path):
    df_raw = load_input_file(input_path)
    parsed = extract_to_fields(df_raw)
    parsed = clean_and_validate(parsed)
    valid_rows, invalid_rows = validate_rows(parsed)
    with open(from_json_path, 'r') as f:
        from_data = json.load(f)
    final_df = merge_from_data(valid_rows, from_data)
    return final_df, invalid_rows

