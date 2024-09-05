import pandas as pd
import os
import re
from timsdata import oneOverK0ToCCSforMz
from tkinter import messagebox
from data_processing import extract_column_name, process_folder, extract_voltage_from_method_file

# Defaults for use_recalibrated_state = True and pressure_compensation_strategy = AnalysisGlobalPressureCompensation for both single file and batch processing
def process_data(input_folder, mzmin, mzmax, progress_var, status_var, process_button, root, extraction_method, sort_columns, ccs_conversion=False, charge=None, mz_value=None, use_recalibrated_state=True, pressure_compensation_strategy="AnalysisGlobalPressureCompensation"):
    master_df = pd.DataFrame()
    folder_names = {}
    column_numbers = {}

    folder_list = [f for f in os.listdir(input_folder) if os.path.isdir(os.path.join(input_folder, f))]
    total_folders = len(folder_list)

    for idx, folder_name in enumerate(folder_list):
        folder_path = os.path.join(input_folder, folder_name)
        full_folder_path = os.path.abspath(folder_path)

        if extraction_method == "method":
            column_name = extract_voltage_from_method_file(full_folder_path)
        else:
            match = re.search(r"(\d+)V", folder_name)
            if match:
                column_name = match.group(1)
            else:
                column_name = folder_name

        if column_name is None:
            column_name = "unknown"

        column_name = str(column_name)

        print(f"Extracted column name: {column_name}")

        if column_name:
            status_message = f"Processing folder: {folder_name}"
            process_data.update_status(status_message)
            result_df = process_folder(full_folder_path, mzmin, mzmax, use_recalibrated_state=use_recalibrated_state, pressure_compensation_strategy=pressure_compensation_strategy)

            if result_df is not None:
                if ccs_conversion:
                    result_df['ko'] = result_df['ko'].apply(lambda x: oneOverK0ToCCSforMz(x, charge, mz_value))

                result_df.rename(columns={'intensity': column_name}, inplace=True)

                if master_df.empty:
                    master_df = result_df[['ko', column_name]].copy()
                else:
                    master_df = pd.merge(master_df, result_df[['ko', column_name]], on='ko', how='outer')

                folder_names[column_name] = folder_name
                column_numbers[column_name] = column_name
            else:
                print(f"Columns 'ko' and '{column_name}' not found in result_df.")

            progress_var.set((idx + 1) / total_folders * 100)
            root.update_idletasks()

    if master_df.empty:
        messagebox.showerror("Error", "No data to process.")
        status_var.set("Error: No data to process.")
        root.update_idletasks()
        return

    master_df.fillna(0, inplace=True)

    if sort_columns:
        column_order = ['ko'] + sorted(
            [col for col in master_df.columns if col != 'ko'],
            key=lambda x: float(re.search(r'^(\d+(\.\d+)?)', x).group(1)) if re.search(r'^(\d+(\.\d+)?)', x) else float('inf')
        )
        master_df = master_df[column_order]

    if ccs_conversion:
        master_df.rename(columns={'ko': 'CCS'}, inplace=True)
    else:
        master_df.rename(columns={'ko': 'Mobility'}, inplace=True)

    # Prepare header rows
    mz_range = f"_mz{int(mzmin)}-{int(mzmax)}"
    output_file_name = f"{os.path.basename(input_folder)}{mz_range}_raw.csv"
    output_file_path = os.path.join(input_folder, output_file_name)

    mzmin_max_row = ['#mz range'] + [f'{mzmin}-{mzmax}'] * (len(master_df.columns) - 1)
    folder_row = ['#Raw file name'] + [folder_names[col] for col in master_df.columns if col != 'Mobility' and col != 'CCS']
    number_row = ['Mobility' if not ccs_conversion else 'CCS'] + [column_numbers[col] for col in master_df.columns if col != 'Mobility' and col != 'CCS']

    # Create DataFrame for the additional rows and concatenate
    additional_rows = pd.DataFrame([mzmin_max_row, folder_row, number_row], columns=master_df.columns)
    final_df = pd.concat([additional_rows, master_df], ignore_index=True)

    final_df.to_csv(output_file_path, index=False, header=False)
    print(f"Data saved to {output_file_path}")

    status_var.set("Processing complete")
    root.update_idletasks()
    process_button.config(text="Select folder containing .d files", state="normal")


def process_batch_data(batch_data, progress_var, status_var, batch_button, root):
    total_folders = len(batch_data)
    
    for idx, row in batch_data.iterrows():
        try:
            input_folder = row['Parent Folder']
            mzmin = float(row['mzmin'])
            mzmax = float(row['mzmax'])
            extraction_method = row['Extraction Method']
            sort_columns = bool(row['Sort Columns'])
            ccs_conversion = bool(row['Convert to CCS'])
            charge = int(row['Charge']) if ccs_conversion else None
            mz_value = float(row['mz']) if ccs_conversion else None
            use_recalibrated_state = bool(row.get('Use Recalibrated State', True))
            pressure_compensation_strategy = row.get('Pressure Compensation Strategy', 'AnalysisGlobalPressureCompensation')
            
            status_var.set(f"Processing folder {input_folder} ({idx + 1}/{total_folders})")
            root.update_idletasks()

            process_data(input_folder, mzmin, mzmax, progress_var, status_var, batch_button, root, extraction_method, sort_columns, ccs_conversion, charge, mz_value, use_recalibrated_state, pressure_compensation_strategy)

        except Exception as e:
            status_var.set(f"Error processing folder {input_folder}: {e}")
            root.update_idletasks()

        progress_var.set((idx + 1) / total_folders * 100)
        root.update_idletasks()

    status_var.set("Batch processing complete")
    batch_button.config(text="Batch Extraction", state="normal")
    root.update_idletasks()
