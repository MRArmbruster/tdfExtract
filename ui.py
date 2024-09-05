import tkinter as tk
from tkinter import messagebox, filedialog
from ttkbootstrap import Style, ttk
import threading
import pandas as pd
from processing import process_data, process_batch_data
from tkinter import PhotoImage
import sys
import os

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    dll_path = os.path.join(bundle_dir, 'timsdata.dll')
    os.add_dll_directory(os.path.dirname(dll_path))
else:
    os.add_dll_directory(os.getcwd())
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

icon_path = os.path.join(bundle_dir, 'fingerprint.png')

def create_ui():
    global mzmin_var, mzmax_var, charge_var, mz_value_var
    global recalibrated_var, pressure_compensation_var, ccs_conversion_var
    global extraction_method_var, sort_columns_var, progress_var, status_var
    global process_button, batch_button, root
    
    root = tk.Tk()  # Initialize root window
    
    recalibrated_var = tk.BooleanVar(value=True)  
    pressure_compensation_var = tk.StringVar(value="Global")
    
    def on_process():
        input_folder = filedialog.askdirectory(title="Select a folder containing .d files")
        if not input_folder:
            messagebox.showerror("Error", "No folder selected.")
            return
        
        try:
            mzmin = float(mzmin_var.get())
            mzmax = float(mzmax_var.get())
            charge = int(charge_var.get()) if ccs_conversion_var.get() else None
            mz_value = float(mz_value_var.get()) if ccs_conversion_var.get() else None
        except ValueError:
            messagebox.showerror("Error", "Invalid input value.")
            return
        
        extraction_method = extraction_method_var.get()
        sort_columns = sort_columns_var.get()
        use_recalibrated_state = recalibrated_var.get()
        pressure_compensation_strategy = pressure_compensation_var.get()
        
        progress_var.set(0)
        status_var.set("Starting processing...")
        root.update_idletasks()

        process_button.config(text="Processing...", state="disabled")
        
        thread = threading.Thread(target=process_data, args=(input_folder, mzmin, mzmax, progress_var, status_var, process_button, root, extraction_method, sort_columns, ccs_conversion_var.get(), charge, mz_value, use_recalibrated_state, pressure_compensation_strategy))
        thread.start()

        root.update_idletasks()

    def on_batch_process():
        file_path = filedialog.askopenfilename(title="Select a CSV file", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            messagebox.showerror("Error", "No file selected.")
            return
        
        try:
            batch_data = pd.read_csv(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file: {e}")
            return
        
        progress_var.set(0)
        status_var.set("Starting batch processing...")
        root.update_idletasks()

        batch_button.config(text="Batch Processing...", state="disabled")
        
        thread = threading.Thread(target=process_batch_data, args=(batch_data, progress_var, status_var, batch_button, root))
        thread.start()

        root.update_idletasks()

    def toggle_ccs_conversion():
        if ccs_conversion_var.get():
            charge_label.grid()
            charge_entry.grid()
            mz_value_label.grid()
            mz_value_entry.grid()
        else:
            charge_label.grid_remove()
            charge_entry.grid_remove()
            mz_value_label.grid_remove()
            mz_value_entry.grid_remove()

    def open_advanced_settings():
        def save_advanced_settings():
            recalibrated_var.set(recalibrated_check_var.get())
            pressure_compensation_var.set(pressure_compensation_var_popup.get())
            advanced_window.destroy()

        advanced_window = tk.Toplevel(root)
        advanced_window.title("Advanced Settings")
        advanced_window.geometry("400x150")  

        recalibrated_check_var = tk.BooleanVar(value=recalibrated_var.get())
        ttk.Checkbutton(advanced_window, text="Use Recalibrated State", variable=recalibrated_check_var).grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)

        ttk.Label(advanced_window, text="Pressure Compensation Strategy:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        pressure_compensation_var_popup = tk.StringVar(value=pressure_compensation_var.get())
        pressure_compensation_menu = ttk.Combobox(advanced_window, textvariable=pressure_compensation_var_popup, values=[
            "No compensation",
            "Per-frame",
            "Global"
        ], state="readonly")
        pressure_compensation_menu.grid(row=1, column=1, sticky=tk.W, padx=10, pady=10)

        save_button = ttk.Button(advanced_window, text="Save", command=save_advanced_settings)
        save_button.grid(row=2, column=0, columnspan=2, pady=10)

    style = Style(theme='flatly')  
    root.title("tdfExtract")

    root.geometry('475x700')  
    root.minsize(475, 700)  

    root.iconphoto(False, PhotoImage(file=icon_path))

    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=0)

    ttk.Label(frame, text="tdfExtract", font=("Helvetica", 16)).grid(row=0, column=0, columnspan=2, pady=(0, 20))

    batch_button = ttk.Button(frame, text="Batch Extraction", command=on_batch_process, bootstyle="primary", padding=(12, 6))
    batch_button.grid(row=0, column=1, sticky=tk.E, padx=10)

    ttk.Label(frame, text="Enter the m/z range for the ion of interest.", font=("Helvetica", 14)).grid(row=1, column=0, columnspan=2, pady=(0, 30))

    ttk.Label(frame, text="Minimum m/z:", font=("Helvetica", 12)).grid(row=2, column=0, sticky=tk.E)
    mzmin_var = tk.StringVar(value="")
    mzmin_entry = ttk.Entry(frame, textvariable=mzmin_var, font=("Helvetica", 12))
    mzmin_entry.grid(row=2, column=1, sticky=(tk.W, tk.E))

    ttk.Label(frame, text="Maximum m/z:", font=("Helvetica", 12)).grid(row=3, column=0, sticky=tk.E)
    mzmax_var = tk.StringVar(value="")
    mzmax_entry = ttk.Entry(frame, textvariable=mzmax_var, font=("Helvetica", 12))
    mzmax_entry.grid(row=3, column=1, sticky=(tk.W, tk.E))

    # Grouping the extraction method options
    extraction_frame = ttk.LabelFrame(frame, text="Select extraction method", padding=(10, 5))
    extraction_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 20))

    extraction_method_var = tk.StringVar(value="method")
    method_radio = ttk.Radiobutton(extraction_frame, text="Automatically extract D6 voltage", variable=extraction_method_var, value="method")
    method_radio.grid(row=0, column=0, sticky=tk.W)

    filename_radio = ttk.Radiobutton(extraction_frame, text="Use file names as activation indicator", variable=extraction_method_var, value="filename")
    filename_radio.grid(row=1, column=0, sticky=tk.W)

    sort_columns_var = tk.BooleanVar(value=True)
    sort_checkbox = ttk.Checkbutton(frame, text="Sort columns by voltage before saving", variable=sort_columns_var)
    sort_checkbox.grid(row=5, column=0, columnspan=2, sticky=tk.W)

    ccs_conversion_var = tk.BooleanVar(value=False)
    ccs_checkbox = ttk.Checkbutton(frame, text="Convert mobility to CCS", variable=ccs_conversion_var, command=toggle_ccs_conversion)
    ccs_checkbox.grid(row=6, column=0, columnspan=2, sticky=tk.W)

    charge_label = ttk.Label(frame, text="Charge:", font=("Helvetica", 12))
    charge_label.grid(row=7, column=0, sticky=tk.E)

    charge_var = tk.StringVar(value="")
    charge_entry = ttk.Entry(frame, textvariable=charge_var, font=("Helvetica", 12))
    charge_entry.grid(row=7, column=1, sticky=(tk.W, tk.E))

    mz_value_label = ttk.Label(frame, text="m/z:", font=("Helvetica", 12))
    mz_value_label.grid(row=8, column=0, sticky=tk.E)

    mz_value_var = tk.StringVar(value="")
    mz_value_entry = ttk.Entry(frame, textvariable=mz_value_var, font=("Helvetica", 12))
    mz_value_entry.grid(row=8, column=1, sticky=(tk.W, tk.E))

    # Advanced settings button
    advanced_button = ttk.Button(frame, text="Advanced Settings", command=open_advanced_settings, bootstyle="primary", padding=(10, 5))
    advanced_button.grid(row=9, column=0, columnspan=2, pady=20)

    ttk.Label(frame, text="Extraction output is saved in the selected folder as \"*_raw.csv\"", font=("Helvetica", 10)).grid(row=10, column=0, columnspan=2, pady=(5, 10))

    process_button = ttk.Button(frame, text="Select folder containing .d files", command=on_process, bootstyle="primary", padding=(10, 5))
    process_button.grid(row=11, column=0, columnspan=2, pady=20)

    progress_var = tk.DoubleVar(value=0)

    progress_frame = ttk.Frame(frame, bootstyle="dark")
    progress_frame.grid(row=12, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100, length=300, bootstyle="info")
    progress_bar.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    status_var = tk.StringVar(value="Status: Ready")
    status_label = ttk.Label(frame, textvariable=status_var, font=("Helvetica", 12))
    status_label.grid(row=13, column=0, columnspan=2, sticky=(tk.W, tk.E))

    for child in frame.winfo_children():
        child.grid_configure(padx=10, pady=10)

    def update_status(status_message):
        status_var.set(status_message)
        root.update_idletasks()

    process_data.update_status = update_status

    toggle_ccs_conversion()

    root.mainloop()

if __name__ == "__main__":
    create_ui()
