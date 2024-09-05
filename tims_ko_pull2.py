import sys
import os
import argparse
import numpy as np
import pandas as pd
from timsdata import *

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    dll_path = os.path.join(bundle_dir, 'timsdata.dll')
    os.add_dll_directory(os.path.dirname(dll_path))
else:
    os.add_dll_directory(os.getcwd())
    dll_path = os.path.join(os.getcwd(), 'timsdata.dll')

def main():
    parser = argparse.ArgumentParser(description='Process some data.')
    parser.add_argument('input_folder', type=str, help='Path to the input .d folder')
    parser.add_argument('--mzmin', type=float, required=True, help='Minimum mz value')
    parser.add_argument('--mzmax', type=float, required=True, help='Maximum mz value')
    parser.add_argument('--use_recalibrated_state', type=bool, default=True, help='Whether to use recalibrated state')
    parser.add_argument('--pressure_compensation_strategy', type=str, default='AnalysisGlobalPressureCompensation', help='Pressure compensation strategy to use')
    
    args = parser.parse_args()

    input_folder = os.path.normpath(args.input_folder)
    mzmin = args.mzmin
    mzmax = args.mzmax
    use_recalibrated_state = args.use_recalibrated_state
    pressure_compensation_strategy = args.pressure_compensation_strategy

    if not os.path.isdir(input_folder):
        print(f"Error: The folder {input_folder} does not exist.")
        sys.exit(1)

    # Map the UI string to the actual strategy
    strategy_mapping = {
        "No compensation": PressureCompensationStrategy.NoPressureCompensation,
        "Per-frame": PressureCompensationStrategy.PerFramePressureCompensation,
        "Global": PressureCompensationStrategy.AnalyisGlobalPressureCompensation
    }

    td = TimsData(input_folder, use_recalibrated_state=use_recalibrated_state, pressure_compensation_strategy=strategy_mapping[pressure_compensation_strategy])
    conn = td.conn
    
    # Get total frame count
    q = conn.execute("SELECT COUNT(*) FROM Frames")
    row = q.fetchone()
    total_frames = row[0]

    all_data = []

    for frame_id in range(1, total_frames + 1):
        q = conn.execute(f"SELECT NumScans FROM Frames WHERE Id={frame_id}")
        num_scans = q.fetchone()[0]

        scans = td.readScans(frame_id, 0, num_scans)
        
        for scan_idx, (index_array, intensity_array) in enumerate(scans):
            mz_array = td.indexToMz(frame_id, index_array)
            
            filter_mask = (mz_array >= mzmin) & (mz_array <= mzmax)
            mz_filtered = mz_array[filter_mask]
            intensities_filtered = intensity_array[filter_mask]
            
            if len(mz_filtered) > 0:
                ko_values = td.scanNumToOneOverK0(frame_id, np.array([scan_idx]))
                ko_values_filtered = np.full(len(mz_filtered), ko_values[0])

                data = pd.DataFrame({'ko': ko_values_filtered, 'intensity': intensities_filtered})
                all_data.append(data)

    if all_data:
        combined_data = pd.concat(all_data, ignore_index=True)
        grouped = combined_data.groupby(['ko'])['intensity'].sum().reset_index()
        print(grouped.to_csv(index=False))
    else:
        print("No data to process.")

if __name__ == '__main__':
    main()
