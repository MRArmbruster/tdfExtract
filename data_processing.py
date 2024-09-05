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
    if extraction_method == "method":
        try:
            voltage = extract_voltage_from_method_file(folder_path)
            return str(voltage)
        except Exception as e:
            print(f"Error extracting voltage from method file: {e}")
            return None
    else:
        match = re.search(r"(\d+V)", os.path.basename(folder_path))
        if match:
            return match.group(1)
        else:
            return os.path.basename(folder_path)

def process_folder(d_folder_path, mzmin, mzmax, use_recalibrated_state=True, pressure_compensation_strategy="AnalysisGlobalPressureCompensation"):
    try:
        # Set the command-line arguments for tims_ko_pull2's main function
        sys.argv = [
            'tims_ko_pull2.py',
            d_folder_path,
            '--mzmin', str(mzmin),
            '--mzmax', str(mzmax),
            '--use_recalibrated_state', str(use_recalibrated_state),
            '--pressure_compensation_strategy', pressure_compensation_strategy
        ]
        
        output = StringIO()
        with contextlib.redirect_stdout(output):
            tims_main()

        df = pd.read_csv(StringIO(output.getvalue()))
        return df

    except Exception as e:
        print(f"Error processing folder {d_folder_path}: {e}")
        return None
