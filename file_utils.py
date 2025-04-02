import os
import re
import tkinter as tk
from tkinter import simpledialog, filedialog
import sys

def select_folders():
    root = tk.Tk()
    root.withdraw()
    folder_paths = filedialog.askdirectory(title="Select one or more folders containing .d files", mustexist=True)
    return folder_paths.split()

def get_user_input(prompt, default_value):
    root = tk.Tk()
    root.withdraw()
    user_input = simpledialog.askfloat(title="Input", prompt=prompt, initialvalue=default_value)
    root.destroy()
    return user_input

def extract_voltage_from_method_file(folder_path):
    print(f"Checking folder: {folder_path}", file=sys.stderr)
    method_folder = None
    # If the provided folder already ends with ".m", assume it is the method folder.
    if folder_path.endswith(".m"):
        method_folder = folder_path
    else:
        for subdir in os.listdir(folder_path):
            if subdir.endswith(".m"):
                method_folder = os.path.join(folder_path, subdir)
                break

    if not method_folder:
        raise FileNotFoundError(f"No subfolder ending with '.m' found in the directory: {folder_path}")

    method_file = None
    for file in os.listdir(method_folder):
        if file.endswith(".method"):
            method_file = os.path.join(method_folder, file)
            break

    if not method_file:
        raise FileNotFoundError(f"No .method file found in the directory: {method_folder}")

    print(f"Method file found: {method_file}", file=sys.stderr)

    with open(method_file, 'r') as f:
        content = f.read()

    # Extract all voltage values from IMS_TunnelVoltage_Delta_6 entries.
    matches = re.findall(r'<para_double value="([\d.]+)" permname="IMS_TunnelVoltage_Delta_6"/>', content)
    if matches:
        voltages = [round(float(v), 1) for v in matches]
        if len(voltages) == 1:
            return voltages[0]
        else:
            return voltages
    else:
        print(f"IMS_TunnelVoltage_Delta_6 not found in the method file: {method_file}", file=sys.stderr)
        return None
