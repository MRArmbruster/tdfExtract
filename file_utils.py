import os
import re
import tkinter as tk
from tkinter import simpledialog, filedialog

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
    print(f"Checking folder: {folder_path}")
    method_folder = None
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
    
    print(f"Method file found: {method_file}")

    with open(method_file, 'r') as f:
        content = f.read()
    
    match = re.search(r'<para_double value="([\d.]+)" permname="IMS_TunnelVoltage_Delta_6"/>', content)
    if match:
        return round(float(match.group(1)), 1)
    else:
        print(f"IMS_TunnelVoltage_Delta_6 not found in the method file: {method_file}")
        return None
