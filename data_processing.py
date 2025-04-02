import os
import sys
import pandas as pd
import re
from file_utils import extract_voltage_from_method_file
from tims_ko_pull2 import main as tims_main
from io import StringIO
import contextlib

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    dll_path = os.path.join(bundle_dir, 'timsdata.dll')
    os.add_dll_directory(os.path.dirname(dll_path))
else:
    os.add_dll_directory(os.getcwd())
    dll_path = os.path.join(os.getcwd(), 'timsdata.dll')

def extract_column_name(folder_path, extraction_method):
    try:
        voltage = extract_voltage_from_method_file(folder_path)
        return str(voltage)
    except Exception as e:
        print(f"Error extracting voltage from method file: {e}")
        return None

def process_folder(d_folder_path, mzmin, mzmax, use_recalibrated_state=True, pressure_compensation_strategy="AnalysisGlobalPressureCompensation", sum_mode=False, mobmin=None, mobmax=None):
    try:
        if d_folder_path.endswith(".m"):
            data_folder = os.path.dirname(d_folder_path)
        else:
            data_folder = d_folder_path

        sys.argv = [
            'tims_ko_pull2.py',
            data_folder,
            '--mzmin', str(mzmin),
            '--mzmax', str(mzmax),
            '--use_recalibrated_state', str(use_recalibrated_state),
            '--pressure_compensation_strategy', pressure_compensation_strategy
        ]
        if sum_mode:
            sys.argv.extend(['--sum_mode', '--mobmin', str(mobmin), '--mobmax', str(mobmax)])
        
        output = StringIO()
        with contextlib.redirect_stdout(output):
            tims_main()

        df = pd.read_csv(StringIO(output.getvalue()))
        
        if sum_mode:
            return df
        else:
            if len(df.columns) > 2:
                voltages = extract_voltage_from_method_file(d_folder_path)
                intensity_cols = [col for col in df.columns if col != 'ko']
                if isinstance(voltages, list) and len(voltages) == len(intensity_cols):
                    rename_dict = {}
                    for col, voltage in zip(intensity_cols, voltages):
                        rename_dict[col] = str(voltage)
                    df.rename(columns=rename_dict, inplace=True)
                else:
                    for idx, col in enumerate(intensity_cols):
                        df.rename(columns={col: f"Segment_{idx+1}"}, inplace=True)
                df.rename(columns={'ko': 'Mobility'}, inplace=True)
                other_cols = [col for col in df.columns if col != 'Mobility']
                try:
                    other_cols = sorted(other_cols, key=lambda x: float(x))
                except Exception:
                    pass
                df = df[['Mobility'] + other_cols]
                return df
            else:
                df.rename(columns={'ko': 'Mobility'}, inplace=True)
                return df

    except Exception as e:
        print(f"Error processing folder {d_folder_path}: {e}")
        return None
