import streamlit as st
import json
import pandas as pd
import os
import tempfile
from pathlib import Path
from parse import run_parser

# Set up paths
BASE_DIR = Path(__file__).parent
FROM_JSON = BASE_DIR / "from_address.json"

st.set_page_config(page_title="Shipping Label Tool", layout="centered")
st.title("Sender Setup")

# Default values if loading from existing JSON
default_values = {
    "FromCountry": "",
    "FromName": "",
    "FromCompany": "",
    "FromPhone": "",
    "FromStreet1": "",
    "FromStreet2": "",
    "FromCity": "",
    "FromZip": "",
    "FromState": ""
}

# Load from JSON if it exists
if FROM_JSON.exists():
    with open(FROM_JSON, "r") as f:
        saved_data = json.load(f)
        default_values.update(saved_data)

# Sender address form
with st.form("from_address_form"):
    col1, col2 = st.columns(2)
    with col1:
        from_name = st.text_input("From Name", value=default_values["FromName"])
        from_company = st.text_input("From Company", value=default_values["FromCompany"])
        from_phone = st.text_input("From Phone", value=default_values["FromPhone"])
        from_street1 = st.text_input("From Street 1", value=default_values["FromStreet1"])
        from_street2 = st.text_input("From Street 2", value=default_values["FromStreet2"])
    with col2:
        from_city = st.text_input("From City", value=default_values["FromCity"])
        from_state = st.text_input("From State", value=default_values["FromState"])
        from_zip = st.text_input("From Zip", value=default_values["FromZip"])
        from_country = st.text_input("From Country", value=default_values["FromCountry"])

    save_json = st.checkbox("Save as default for next time", value=True)
    submitted = st.form_submit_button("Save Sender Info")

if submitted:
    from_data = {
        "FromCountry": from_country,
        "FromName": from_name,
        "FromCompany": from_company,
        "FromPhone": from_phone,
        "FromStreet1": from_street1,
        "FromStreet2": from_street2,
        "FromCity": from_city,
        "FromZip": from_zip,
        "FromState": from_state
    }

    st.session_state.from_data = from_data

    if save_json:
        with open(FROM_JSON, "w") as f:
            json.dump(from_data, f, indent=2)

    st.success("Sender address saved and ready to use!")

# --- File Upload ---
st.title("Upload Your Customer Data")
uploaded_file = st.file_uploader("Upload your file (.xlsx, .csv, .txt)", type=["xlsx", "csv", "txt"])


# Clear stale session state if no file is uploaded
if not uploaded_file:
    st.session_state.pop("final_df", None)
    st.session_state.pop("invalid_df", None)






if uploaded_file:
    try:
        # Save temp file safely
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
            tmp.write(uploaded_file.read())
            temp_path = tmp.name

        # Check if sender info exists
        if not FROM_JSON.exists():
            st.error("You must first set up your Sender Address.")
        else:
            final_df, invalid_df = run_parser(temp_path, str(FROM_JSON))
            final_df["Copies"] = 1

            st.success("File parsed successfully!")
            st.subheader("Valid Rows")

            edited_valid_df = st.data_editor(final_df, num_rows="dynamic", use_container_width=True)
            st.session_state.final_df = edited_valid_df

            duplicated_df = edited_valid_df.loc[edited_valid_df.index.repeat(edited_valid_df["Copies"])].reset_index(drop=True)
            duplicated_df = duplicated_df.drop(columns=["Copies"], errors="ignore")

            st.download_button(
                label="Download Final CSV",
                data=duplicated_df.to_csv(index=False).encode("utf-8"),
                file_name="final_cleaned_output.csv",
                mime="text/csv"
            )

            if not invalid_df.empty:
                st.warning(f"{len(invalid_df)} rows were skipped due to missing required fields.")
                st.subheader("Rows with Missing Fields")

            # Show which fields are missing for each invalid row
            st.markdown("### Missing Field Breakdown")
            missing_fields_report = []

            required_fields = ['ToName', 'ToStreet1', 'ToCity', 'ToZip', 'ToState', 'ToCountry']
            for idx, row in invalid_df.iterrows():
                missing = [field for field in required_fields if pd.isna(row.get(field, "")) or str(row.get(field)).strip() == ""]
                if missing:
                    missing_fields_report.append(f"Row {idx + 1}: Missing → {', '.join(missing)}")

            if missing_fields_report:
                st.code("\n".join(missing_fields_report))

                expected_columns = final_df.columns.tolist()

                for col in expected_columns:
                    if col not in invalid_df.columns:
                       # invalid_df[col] = ""
                        invalid_df[col] = 0 if col in ['Length', 'Height', 'Width', 'Weight'] else ""

                for dim in ['Length', 'Height', 'Width', 'Weight']:
                    if dim not in invalid_df.columns:
                        invalid_df[dim] = 0

        
                invalid_df = invalid_df[expected_columns]
                invalid_df["Copies"] = 1

                from_data = default_values.copy()
                from_columns = [col for col in final_df.columns if col.startswith("From")]
                for col in from_columns:
                    invalid_df[col] = invalid_df[col].apply(lambda x: from_data.get(col, "") if pd.isna(x) or x == "" else x)

                edited_invalid_df = st.data_editor(invalid_df, num_rows="dynamic", use_container_width=True)
                st.session_state.edited_invalid_df = edited_invalid_df

                edited_invalid_df["Copies"] = pd.to_numeric(
                    edited_invalid_df.get("Copies", 1), errors="coerce"
                ).fillna(1).astype(int)

                duplicated_invalid_df = edited_invalid_df.loc[
                    edited_invalid_df.index.repeat(edited_invalid_df["Copies"])
                ].reset_index(drop=True)

                duplicated_invalid_df = duplicated_invalid_df.drop(columns=["Copies"], errors="ignore")

                st.download_button(
                    label="Download Rows with Missing Fields",
                    data=duplicated_invalid_df.to_csv(index=False).encode("utf-8"),
                    file_name="rows_with_missing_fields.csv",
                    mime="text/csv"
                )

            st.session_state.invalid_df = invalid_df

    except FileNotFoundError:
        st.error("Could not find required file. Make sure your sender info is saved.")
    except KeyError as e:
        st.error(f"Missing required column: {str(e)}")
    except ValueError as e:
        st.error(f"File error: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)





























