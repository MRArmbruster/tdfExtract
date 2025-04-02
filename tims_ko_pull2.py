import sys
import os
import argparse
import numpy as np
import pandas as pd
from timsdata import *
import sqlite3

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    dll_path = os.path.join(bundle_dir, 'timsdata.dll')
    os.add_dll_directory(os.path.dirname(dll_path))
else:
    os.add_dll_directory(os.getcwd())
    dll_path = os.path.join(os.getcwd(), 'timsdata.dll')

def main():
    parser = argparse.ArgumentParser(description='Process tims data.')
    parser.add_argument('input_folder', type=str, help='Path to the input .d folder')
    parser.add_argument('--mzmin', type=float, required=True, help='Minimum mz value')
    parser.add_argument('--mzmax', type=float, required=True, help='Maximum mz value')
    parser.add_argument('--use_recalibrated_state', type=bool, default=True, help='Whether to use recalibrated state')
    parser.add_argument('--pressure_compensation_strategy', type=str, default='AnalysisGlobalPressureCompensation', help='Pressure compensation strategy to use')
    
    # New arguments for summed intensity mode
    parser.add_argument('--sum_mode', action='store_true', help='Enable summed intensity mode within a mobility box')
    parser.add_argument('--mobmin', type=float, default=None, help='Minimum mobility value for summed intensity mode')
    parser.add_argument('--mobmax', type=float, default=None, help='Maximum mobility value for summed intensity mode')
    
    args = parser.parse_args()

    if args.sum_mode:
        if args.mobmin is None or args.mobmax is None:
            print("Error: In summed intensity mode, please provide both --mobmin and --mobmax values.")
            sys.exit(1)
    
    input_folder = os.path.normpath(args.input_folder)
    mzmin = args.mzmin
    mzmax = args.mzmax
    use_recalibrated_state = args.use_recalibrated_state
    pressure_compensation_strategy = args.pressure_compensation_strategy

    if not os.path.isdir(input_folder):
        print(f"Error: The folder {input_folder} does not exist.")
        sys.exit(1)
    
    # Map the UI string to the actual strategy.
    strategy_mapping = {
        "No compensation": PressureCompensationStrategy.NoPressureCompensation,
        "Per-frame": PressureCompensationStrategy.PerFramePressureCompensation,
        "Global": PressureCompensationStrategy.AnalyisGlobalPressureCompensation
    }

    td = TimsData(input_folder, use_recalibrated_state=use_recalibrated_state,
                  pressure_compensation_strategy=strategy_mapping.get(pressure_compensation_strategy,
                                                                      PressureCompensationStrategy.AnalyisGlobalPressureCompensation))
    conn = td.conn

    # Check if the "Segments" table exists in analysis.tdf.
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Segments'")
    segments_table = cur.fetchone()

    if args.sum_mode:
        # Summed intensity mode: sum intensities for each segment separately.
        if segments_table:
            segments = conn.execute("SELECT FirstFrame, LastFrame FROM Segments ORDER BY FirstFrame").fetchall()
            segment_sums = []
            for seg in segments:
                first_frame, last_frame = seg
                sum_seg = 0.0
                for frame_id in range(first_frame, last_frame + 1):
                    cur_scans = conn.execute("SELECT NumScans FROM Frames WHERE Id=?", (frame_id,))
                    row = cur_scans.fetchone()
                    if not row:
                        continue
                    num_scans = row[0]
                    scans = td.readScans(frame_id, 0, num_scans)
                    for scan_idx, (index_array, intensity_array) in enumerate(scans):
                        mz_array = td.indexToMz(frame_id, index_array)
                        filter_mask = (mz_array >= mzmin) & (mz_array <= mzmax)
                        if not filter_mask.any():
                            continue
                        intensities_filtered = intensity_array[filter_mask]
                        ko_val = td.scanNumToOneOverK0(frame_id, np.array([scan_idx]))[0]
                        if args.mobmin <= ko_val <= args.mobmax:
                            sum_seg += intensities_filtered.sum()
                segment_sums.append(sum_seg)
            try:
                from file_utils import extract_voltage_from_method_file
                voltage = extract_voltage_from_method_file(input_folder)
            except Exception as e:
                voltage = "unknown"
            # Use the voltage values as column headers if available and matching the number of segments.
            if isinstance(voltage, list) and len(voltage) == len(segment_sums):
                col_headers = [str(v) for v in voltage]
            else:
                col_headers = [f"Segment_{i+1}" for i in range(len(segment_sums))]
            # Build a single-row DataFrame for summed intensities.
            df_out = pd.DataFrame([segment_sums], columns=col_headers)
            print(df_out.to_csv(index=False))
        else:
            # Old format: if no segments table, sum over all frames (single value)
            total_intensity = 0.0
            cur = conn.execute("SELECT COUNT(*) FROM Frames")
            row = cur.fetchone()
            total_frames = row[0]
            for frame_id in range(1, total_frames + 1):
                cur_scans = conn.execute("SELECT NumScans FROM Frames WHERE Id=?", (frame_id,))
                num_scans = cur_scans.fetchone()[0]
                scans = td.readScans(frame_id, 0, num_scans)
                for scan_idx, (index_array, intensity_array) in enumerate(scans):
                    mz_array = td.indexToMz(frame_id, index_array)
                    filter_mask = (mz_array >= mzmin) & (mz_array <= mzmax)
                    if not filter_mask.any():
                        continue
                    intensities_filtered = intensity_array[filter_mask]
                    ko_val = td.scanNumToOneOverK0(frame_id, np.array([scan_idx]))[0]
                    if args.mobmin <= ko_val <= args.mobmax:
                        total_intensity += intensities_filtered.sum()
            try:
                from file_utils import extract_voltage_from_method_file
                voltage = extract_voltage_from_method_file(input_folder)
            except Exception as e:
                voltage = "unknown"
            df_out = pd.DataFrame({'Voltage': [voltage], 'SummedIntensity': [total_intensity]})
            print(df_out.to_csv(index=False))
    else:
        # Original processing mode: output intensity vs. mobility profiles.
        if segments_table:
            segment_dfs = []
            segments = conn.execute("SELECT FirstFrame, LastFrame FROM Segments ORDER BY FirstFrame").fetchall()
            for seg in segments:
                first_frame, last_frame = seg
                seg_data = []
                for frame_id in range(first_frame, last_frame + 1):
                    cur_scans = conn.execute("SELECT NumScans FROM Frames WHERE Id=?", (frame_id,))
                    row = cur_scans.fetchone()
                    if not row:
                        continue
                    num_scans = row[0]
                    scans = td.readScans(frame_id, 0, num_scans)
                    for scan_idx, (index_array, intensity_array) in enumerate(scans):
                        mz_array = td.indexToMz(frame_id, index_array)
                        filter_mask = (mz_array >= mzmin) & (mz_array <= mzmax)
                        mz_filtered = mz_array[filter_mask]
                        intensities_filtered = intensity_array[filter_mask]
                        if len(mz_filtered) > 0:
                            ko_val = td.scanNumToOneOverK0(frame_id, np.array([scan_idx]))[0]
                            df_scan = pd.DataFrame({'ko': np.full(len(mz_filtered), ko_val),
                                                     'intensity': intensities_filtered})
                            seg_data.append(df_scan)
                if seg_data:
                    seg_df = pd.concat(seg_data, ignore_index=True)
                    seg_sum = seg_df.groupby('ko', as_index=False)['intensity'].sum()
                    segment_dfs.append(seg_sum)
            if segment_dfs:
                combined_df = segment_dfs[0]
                for i in range(1, len(segment_dfs)):
                    combined_df = pd.merge(combined_df, segment_dfs[i], on='ko', how='outer', suffixes=('', f'_{i}'))
                combined_df.sort_values('ko', inplace=True)
                combined_df.fillna(0, inplace=True)
                final_df = combined_df[['ko'] + [col for col in combined_df.columns if col != 'ko']]
                print(final_df.to_csv(index=False))
            else:
                print("No segment data processed.")
        else:
            cur = conn.execute("SELECT COUNT(*) FROM Frames")
            row = cur.fetchone()
            total_frames = row[0]
            all_data = []
            for frame_id in range(1, total_frames + 1):
                cur_scans = conn.execute("SELECT NumScans FROM Frames WHERE Id=?", (frame_id,))
                num_scans = cur_scans.fetchone()[0]
                scans = td.readScans(frame_id, 0, num_scans)
                for scan_idx, (index_array, intensity_array) in enumerate(scans):
                    mz_array = td.indexToMz(frame_id, index_array)
                    filter_mask = (mz_array >= mzmin) & (mz_array <= mzmax)
                    if len(mz_array[filter_mask]) > 0:
                        ko_values = td.scanNumToOneOverK0(frame_id, np.array([scan_idx]))
                        intensities_filtered = intensity_array[filter_mask]
                        data = pd.DataFrame({'ko': np.full(len(mz_array[filter_mask]), ko_values[0]),
                                             'intensity': intensities_filtered})
                        all_data.append(data)
            if all_data:
                combined_data = pd.concat(all_data, ignore_index=True)
                grouped = combined_data.groupby(['ko'])['intensity'].sum().reset_index()
                print(grouped.to_csv(index=False))
            else:
                print("No data to process.")

if __name__ == '__main__':
    main()
