import pandas as pd
import os
import re
import numpy as np
from tkinter import messagebox
from data_processing import extract_column_name, process_folder
from timsdata import oneOverK0ToCCSforMz

def bin_mobility_axis(df, num_bins):
    bins = np.linspace(df["Mobility"].min(), df["Mobility"].max(), num_bins+1)
    bin_midpoints = (bins[:-1] + bins[1:]) / 2
    df["mobility_bin"] = pd.cut(df["Mobility"], bins=bins, labels=bin_midpoints, include_lowest=True)
    intensity_cols = [col for col in df.columns if col not in ["Mobility", "mobility_bin"]]
    aggregated = df.groupby("mobility_bin")[intensity_cols].sum().reset_index()
    aggregated.rename(columns={"mobility_bin": "Mobility"}, inplace=True)
    aggregated["Mobility"] = aggregated["Mobility"].astype(float)
    return aggregated

def process_data(input_folder, mzmin, mzmax, progress_var, status_var, process_button, root,
                 extraction_method, sort_columns, use_recalibrated_state, pressure_compensation_strategy,
                 do_binning, num_bins, ccs_conversion, charge, mz_value,
                 sum_mode=False, mobmin=None, mobmax=None, batch_mode=False, output_dir=None):
    # Determine where to save output files.
    save_folder = output_dir if output_dir and os.path.isdir(output_dir) else input_folder

    if sum_mode:
        rows = []
        # Determine if input_folder is a .d folder or a container of subfolders.
        if os.path.basename(input_folder).endswith(".d"):
            folder_list = [input_folder]
        else:
            folder_list = [os.path.join(input_folder, f) for f in os.listdir(input_folder)
                           if os.path.isdir(os.path.join(input_folder, f))]
        total_folders = len(folder_list)
        for idx, folder_path in enumerate(folder_list):
            full_folder_path = os.path.abspath(folder_path)
            status_message = f"Processing folder: {os.path.basename(folder_path)}"
            process_data.update_status(status_message)
            result_df = process_folder(full_folder_path, mzmin, mzmax, use_recalibrated_state,
                                       pressure_compensation_strategy, sum_mode=True, mobmin=mobmin, mobmax=mobmax)
            if result_df is not None:
                from file_utils import extract_voltage_from_method_file
                try:
                    voltage = extract_voltage_from_method_file(full_folder_path)
                except Exception as e:
                    voltage = "unknown"
                voltage_val = voltage[0] if isinstance(voltage, list) else voltage
                result_df.insert(0, "Voltage", voltage_val)
                rows.append(result_df)
            else:
                print(f"Folder {folder_path} returned no data.")
            progress_var.set((idx + 1) / total_folders * 100)
            root.update_idletasks()
        if not rows:
            messagebox.showerror("Error", "No data to process.")
            status_var.set("Error: No data to process.")
            root.update_idletasks()
            return
        master_df = pd.concat(rows, ignore_index=True)
        master_df.sort_values("Voltage", inplace=True)
        # Drop the "Voltage" column for output.
        data_values = master_df.iloc[0, 1:]
        seg_headers = list(master_df.columns[1:])
        mz_range_str = f"{mzmin:.2f}-{mzmax:.2f}"
        mob_range_str = f"{mobmin:.2f}-{mobmax:.2f}"
        raw_name = os.path.basename(input_folder)
        nseg = len(seg_headers)
        row1 = ['#mz range'] + [mz_range_str] * nseg
        row2 = ['#mobility range'] + [mob_range_str] * nseg
        row3 = ['#Raw file name'] + [raw_name] * nseg
        row4 = ["Voltage"] + seg_headers
        row5 = ["Summed_intensity"] + list(data_values)
        header_df = pd.DataFrame([row1, row2, row3, row4, row5], columns=range(1+nseg))
        output_file_name = f"{os.path.basename(input_folder)}_mz{mz_range_str}_mob{mob_range_str}_summed_intensity.csv"
        output_file_path = os.path.join(save_folder, output_file_name)
        header_df.to_csv(output_file_path, index=False, header=False)
        print(f"Data saved to {output_file_path}")
        status_var.set("Processing complete")
        root.update_idletasks()
        if not batch_mode:
            process_button.config(text="Select folder containing .d files", state="normal")
    else:
        master_df = pd.DataFrame()
        folder_names = {}
        column_numbers = {}
        folder_list = [os.path.join(input_folder, f) for f in os.listdir(input_folder)
                       if os.path.isdir(os.path.join(input_folder, f))]
        total_folders = len(folder_list)
        for idx, folder_path in enumerate(folder_list):
            full_folder_path = os.path.abspath(folder_path)
            column_name = extract_column_name(full_folder_path, extraction_method)
            if column_name is None:
                column_name = "unknown"
            column_name = str(column_name)
            status_message = f"Processing folder: {os.path.basename(folder_path)}"
            process_data.update_status(status_message)
            result_df = process_folder(full_folder_path, mzmin, mzmax, use_recalibrated_state,
                                       pressure_compensation_strategy)
            if result_df is not None:
                if len(result_df.columns) > 2:
                    if master_df.empty:
                        master_df = result_df.copy()
                    else:
                        master_df = pd.merge(master_df, result_df, on='Mobility', how='outer')
                elif 'intensity' in result_df.columns:
                    result_df.rename(columns={'intensity': column_name}, inplace=True)
                    if master_df.empty:
                        master_df = result_df[['Mobility', column_name]].copy()
                    else:
                        master_df = pd.merge(master_df, result_df[['Mobility', column_name]], on='Mobility', how='outer')
                    folder_names[column_name] = os.path.basename(folder_path)
                    column_numbers[column_name] = column_name
                else:
                    if master_df.empty:
                        master_df = result_df.copy()
                    else:
                        master_df = pd.merge(master_df, result_df, on='Mobility', how='outer')
            else:
                print(f"Columns 'Mobility' and '{column_name}' not found in result_df.")
            progress_var.set((idx + 1) / total_folders * 100)
            root.update_idletasks()
        if master_df.empty:
            messagebox.showerror("Error", "No data to process.")
            status_var.set("Error: No data to process.")
            root.update_idletasks()
            return
        master_df.fillna(0, inplace=True)
        if sort_columns:
            if 'Mobility' in master_df.columns:
                master_df = master_df.sort_values('Mobility')
            else:
                column_order = ['ko'] + sorted(
                    [col for col in master_df.columns if col != 'ko'],
                    key=lambda x: float(re.search(r'^(\d+(\.\d+)?)', x).group(1))
                    if re.search(r'^(\d+(\.\d+)?)', x) else float('inf')
                )
                master_df = master_df[column_order]
        if 'Mobility' not in master_df.columns:
            master_df.rename(columns={'ko': 'Mobility'}, inplace=True)
        if ccs_conversion:
            try:
                master_df['Mobility'] = master_df['Mobility'].apply(lambda x: oneOverK0ToCCSforMz(x, int(charge), float(mz_value)))
            except Exception as e:
                messagebox.showerror("Error", f"CCS conversion failed: {e}")
                return
        if do_binning:
            master_df = bin_mobility_axis(master_df, num_bins)
        mz_range_str = f"{int(mzmin)}-{int(mzmax)}"
        if len(master_df.columns) > 1:
            raw_name = os.path.basename(input_folder)
            header1 = ['#mz range'] + [mz_range_str] * (len(master_df.columns) - 1)
            header2 = ['#Raw file name'] + [raw_name] * (len(master_df.columns) - 1)
        else:
            header1 = ['#mz range']
            header2 = ['#Raw file name']
        header3 = list(master_df.columns)
        header_df = pd.DataFrame([header1, header2, header3], columns=master_df.columns)
        output_file_name = f"{os.path.basename(input_folder)}_mz{mz_range_str}_raw.csv"
        output_file_path = os.path.join(save_folder, output_file_name)
        final_df = pd.concat([header_df, master_df], ignore_index=True)
        final_df.to_csv(output_file_path, index=False, header=False)
        print(f"Data saved to {output_file_path}")
        status_var.set("Processing complete")
        root.update_idletasks()
        if not batch_mode:
            process_button.config(text="Select folder containing .d files", state="normal")

def process_batch_data(batch_data, progress_var, status_var, batch_button, root, output_dir=None):
    import os
    import pandas as pd
    total_files = 0
    # Compute total number of files to process.
    for idx, row in batch_data.iterrows():
        parent_folder = row['Parent Folder']
        if ('min_mobility' in row and 'max_mobility' in row and 
            pd.notna(row['min_mobility']) and pd.notna(row['max_mobility']) and 
            row['min_mobility'] != "" and row['max_mobility'] != ""):
            if os.path.basename(parent_folder).endswith(".d"):
                total_files += 1
            else:
                subfolders = [os.path.join(parent_folder, f) for f in os.listdir(parent_folder)
                              if os.path.isdir(os.path.join(parent_folder, f)) and f.endswith(".d")]
                total_files += len(subfolders)
        else:
            subfolders = [os.path.join(parent_folder, f) for f in os.listdir(parent_folder)
                          if os.path.isdir(os.path.join(parent_folder, f))]
            total_files += len(subfolders)
    if total_files == 0:
        total_files = 1

    processed_files = 0
    total_rows = len(batch_data)
    for idx, row in batch_data.iterrows():
        try:
            parent_folder = row['Parent Folder']
            mzmin = float(row['mzmin'])
            mzmax = float(row['mzmax'])
            extraction_method = row['Extraction Method']
            sort_columns = bool(row['Sort Columns'])
            use_recalibrated_state = bool(row.get('Use Recalibrated State', True))
            pressure_compensation_strategy = row.get('Pressure Compensation Strategy', 'AnalysisGlobalPressureCompensation')
            
            ccs_conversion = bool(str(row.get('Convert to CCS', "FALSE")).upper() == "TRUE")
            charge = int(row['Charge']) if ('Charge' in row and pd.notna(row['Charge']) and row['Charge'] != "") else None
            mz_value = float(row['mz']) if ('mz' in row and pd.notna(row['mz']) and row['mz'] != "") else None

            if ('min_mobility' in row and 'max_mobility' in row and 
                pd.notna(row['min_mobility']) and pd.notna(row['max_mobility']) and 
                row['min_mobility'] != "" and row['max_mobility'] != ""):
                sum_mode = True
                mobmin = float(row['min_mobility'])
                mobmax = float(row['max_mobility'])
                if os.path.basename(parent_folder).endswith(".d"):
                    subfolders = [parent_folder]
                else:
                    subfolders = [os.path.join(parent_folder, f) for f in os.listdir(parent_folder)
                                  if os.path.isdir(os.path.join(parent_folder, f)) and f.endswith(".d")]
                    if not subfolders:
                        print(f"Warning: No .d folders found in {parent_folder}. Skipping this batch row.")
                        continue
                data_rows = []
                for subfolder in subfolders:
                    result_df = process_data(
                        subfolder, mzmin, mzmax, progress_var, status_var, batch_button, root,
                        extraction_method, sort_columns, use_recalibrated_state, pressure_compensation_strategy,
                        False, 0, False, None, None, sum_mode, mobmin, mobmax, batch_mode=True, output_dir=output_dir
                    )
                    if result_df is not None:
                        summed_values = result_df.iloc[0, 1:]
                        raw_file = os.path.basename(subfolder)
                        data_row = [raw_file] + list(summed_values)
                        data_rows.append(data_row)
                    processed_files += 1
                    progress_var.set((processed_files / total_files) * 100)
                    root.update_idletasks()
                if data_rows:
                    header_segments = list(result_df.columns[1:])
                    header = ["Raw File"] + header_segments
                    final_df = pd.DataFrame(data_rows, columns=header)
                    mz_range_str = f"{mzmin:.2f}-{mzmax:.2f}"
                    mob_range_str = f"{mobmin:.2f}-{mobmax:.2f}"
                    output_file_name = f"{os.path.basename(parent_folder)}_mz{mz_range_str}_mob{mob_range_str}_summed_intensity.csv"
                    output_file_path = os.path.join(parent_folder, output_file_name) if not output_dir else os.path.join(output_dir, output_file_name)
                    final_df.to_csv(output_file_path, index=False)
                    print(f"Data saved to {output_file_path}")
                else:
                    print(f"")
            else:
                sum_mode = False
                do_binning = False
                num_bins = 0
                if 'bin_number' in row and pd.notna(row['bin_number']) and row['bin_number'] != "":
                    do_binning = True
                    num_bins = int(row['bin_number'])
                subfolders = [os.path.join(parent_folder, f) for f in os.listdir(parent_folder)
                              if os.path.isdir(os.path.join(parent_folder, f))]
                for subfolder in subfolders:
                    process_data(
                        subfolder, mzmin, mzmax, progress_var, status_var, batch_button, root,
                        extraction_method, sort_columns, use_recalibrated_state, pressure_compensation_strategy,
                        do_binning, num_bins, ccs_conversion, charge, mz_value, sum_mode, None, None, batch_mode=True, output_dir=output_dir
                    )
                    processed_files += 1
                    progress_var.set((processed_files / total_files) * 100)
                    root.update_idletasks()
        except Exception as e:
            status_var.set(f"Error processing folder {parent_folder}: {e}")
            root.update_idletasks()
    status_var.set("Batch processing complete")
    batch_button.config(text="Batch Extraction", state="normal")
    root.update_idletasks()
