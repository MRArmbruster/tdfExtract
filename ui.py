import tkinter as tk
from tkinter import messagebox, filedialog
from ttkbootstrap import Style, ttk
import threading
import pandas as pd
from processing import process_data, process_batch_data
from tkinter import PhotoImage
import sys
import os

# Global frame references for dynamic UI elements
binning_frame_ref = None
ccs_frame_ref = None
summed_frame_ref = None  # For summed intensity mode inputs

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    dll_path = os.path.join(bundle_dir, 'timsdata.dll')
    os.add_dll_directory(os.path.dirname(dll_path))
else:
    os.add_dll_directory(os.getcwd())
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

icon_path = os.path.join(bundle_dir, 'fingerprint.png')

# Global variable to hold the chosen output directory.
output_dir_var = ""

def create_ui():
    global binning_frame_ref, ccs_frame_ref, summed_frame_ref
    global mzmin_var, mzmax_var, recalibrated_var, pressure_compensation_var
    global sort_columns_var, progress_var, status_var, process_button, batch_button, root
    global bin_mobility_var, num_bins_var
    global ccs_conversion_var, charge_var, mz_value_var
    global sum_intensity_mode_var, mobmin_var, mobmax_var, output_dir_var

    root = tk.Tk()

    recalibrated_var = tk.BooleanVar(value=True)
    pressure_compensation_var = tk.StringVar(value="Global")

    bin_mobility_var = tk.BooleanVar(value=False)
    num_bins_var = tk.StringVar(value="200")

    ccs_conversion_var = tk.BooleanVar(value=False)
    charge_var = tk.StringVar(value="")
    mz_value_var = tk.StringVar(value="")

    sum_intensity_mode_var = tk.BooleanVar(value=False)
    mobmin_var = tk.StringVar(value="")
    mobmax_var = tk.StringVar(value="")

    def create_binning_frame(parent):
        frm = ttk.Frame(parent)
        ttk.Label(frm, text="Number of bins:", font=("Helvetica", 12)).grid(row=0, column=0, sticky=tk.W)
        nb_entry = ttk.Entry(frm, textvariable=num_bins_var, font=("Helvetica", 12), width=5)
        nb_entry.grid(row=0, column=1, sticky=tk.W)
        return frm

    def create_ccs_frame(parent):
        frm = ttk.Frame(parent)
        ttk.Label(frm, text="Charge:", font=("Helvetica", 12)).grid(row=0, column=0, sticky=tk.W)
        ch_entry = ttk.Entry(frm, textvariable=charge_var, font=("Helvetica", 12), width=5)
        ch_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        ttk.Label(frm, text="m/z:", font=("Helvetica", 12)).grid(row=0, column=2, sticky=tk.W)
        mz_entry = ttk.Entry(frm, textvariable=mz_value_var, font=("Helvetica", 12), width=7)
        mz_entry.grid(row=0, column=3, sticky=tk.W)
        return frm

    def create_summed_frame(parent):
        frm = ttk.Frame(parent)
        ttk.Label(frm, text="Min Mobility:", font=("Helvetica", 12)).grid(row=0, column=0, sticky=tk.W)
        mobmin_entry = ttk.Entry(frm, textvariable=mobmin_var, font=("Helvetica", 12), width=7)
        mobmin_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        ttk.Label(frm, text="Max Mobility:", font=("Helvetica", 12)).grid(row=0, column=2, sticky=tk.W)
        mobmax_entry = ttk.Entry(frm, textvariable=mobmax_var, font=("Helvetica", 12), width=7)
        mobmax_entry.grid(row=0, column=3, sticky=tk.W)
        return frm

    # New: Create a button to select an output directory.
    def select_output_directory():
        global output_dir_var
        selected = filedialog.askdirectory(title="Select Output Directory")
        if selected:
            output_dir_var = selected
            # Optionally update the button text to show the chosen directory.
            output_btn.config(text=f"Output: {os.path.basename(selected)}")
    output_btn = ttk.Button(root, text="Select Output Directory", command=select_output_directory)

    def toggle_binning():
        global binning_frame_ref
        if bin_mobility_var.get():
            if binning_frame_ref is None:
                binning_frame_ref = create_binning_frame(frame)
                binning_frame_ref.grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=10)
        else:
            if binning_frame_ref is not None:
                binning_frame_ref.destroy()
                binning_frame_ref = None

    def toggle_ccs():
        global ccs_frame_ref
        if ccs_conversion_var.get():
            if ccs_frame_ref is None:
                ccs_frame_ref = create_ccs_frame(frame)
                ccs_frame_ref.grid(row=9, column=0, columnspan=2, sticky=tk.W, padx=10)
        else:
            if ccs_frame_ref is not None:
                ccs_frame_ref.destroy()
                ccs_frame_ref = None

    def toggle_sum_mode():
        global summed_frame_ref
        if sum_intensity_mode_var.get():
            if summed_frame_ref is None:
                summed_frame_ref = create_summed_frame(frame)
                summed_frame_ref.grid(row=15, column=0, columnspan=2, sticky=tk.W, padx=10)
        else:
            if summed_frame_ref is not None:
                summed_frame_ref.destroy()
                summed_frame_ref = None

    def on_process():
        input_folder = filedialog.askdirectory(title="Select .d file")
        if not input_folder:
            messagebox.showerror("Error", "No folder selected.")
            return

        try:
            mzmin = float(mzmin_var.get())
            mzmax = float(mzmax_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid input value for m/z.")
            return

        extraction_method = "method"
        sort_columns = sort_columns_var.get()
        use_recalibrated_state = recalibrated_var.get()
        pressure_compensation_strategy = pressure_compensation_var.get()

        do_binning = bin_mobility_var.get()
        try:
            nbins = int(num_bins_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid number of bins.")
            return

        do_ccs = ccs_conversion_var.get()
        if do_ccs:
            if not charge_var.get() or not mz_value_var.get():
                messagebox.showerror("Error", "Please enter both Charge and m/z for CCS conversion.")
                return

        sum_mode = sum_intensity_mode_var.get()
        if sum_mode:
            try:
                mobmin = float(mobmin_var.get())
                mobmax = float(mobmax_var.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid input value for mobility.")
                return
        else:
            mobmin = None
            mobmax = None

        # Use output_dir from global variable.
        out_dir = output_dir_var if output_dir_var and os.path.isdir(output_dir_var) else ""

        progress_var.set(0)
        status_var.set("Starting processing...")
        root.update_idletasks()

        process_button.config(text="Processing...", state="disabled")

        thread = threading.Thread(target=process_data, args=(
            input_folder,
            mzmin,
            mzmax,
            progress_var,
            status_var,
            process_button,
            root,
            extraction_method,
            sort_columns,
            use_recalibrated_state,
            pressure_compensation_strategy,
            do_binning,
            nbins,
            do_ccs,
            charge_var.get(),
            mz_value_var.get(),
            sum_mode,
            mobmin,
            mobmax,
            False,  # batch_mode is False for single-run mode
            out_dir
        ))
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

        # Use output_dir from global variable.
        out_dir = output_dir_var if output_dir_var and os.path.isdir(output_dir_var) else ""
        
        progress_var.set(0)
        status_var.set("Starting batch processing...")
        root.update_idletasks()

        batch_button.config(text="Batch Processing...", state="disabled")

        thread = threading.Thread(target=process_batch_data, args=(batch_data, progress_var, status_var, batch_button, root, out_dir))
        thread.start()
        root.update_idletasks()

    def open_advanced_settings():
        def save_advanced_settings():
            recalibrated_var.set(recalibrated_check_var.get())
            pressure_compensation_var.set(pressure_compensation_var_popup.get())
            advanced_window.destroy()

        advanced_window = tk.Toplevel(root)
        advanced_window.title("Advanced Settings")
        advanced_window.geometry("400x150")

        recalibrated_check_var = tk.BooleanVar(value=recalibrated_var.get())
        ttk.Checkbutton(advanced_window, text="Use Recalibrated State", variable=recalibrated_check_var).grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=10)

        ttk.Label(advanced_window, text="Pressure Compensation Strategy:").grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=10)
        pressure_compensation_var_popup = tk.StringVar(value=pressure_compensation_var.get())
        pressure_compensation_menu = ttk.Combobox(
            advanced_window,
            textvariable=pressure_compensation_var_popup,
            values=["No compensation", "Per-frame", "Global"],
            state="readonly"
        )
        pressure_compensation_menu.grid(row=1, column=1, sticky=tk.W, padx=10, pady=10)

        save_button = ttk.Button(advanced_window, text="Save", command=save_advanced_settings)
        save_button.grid(row=2, column=0, columnspan=2, pady=10)

    style = Style(theme='flatly')
    root.title("tdfExtract")
    root.geometry('475x750')
    root.minsize(475, 750)
    root.iconphoto(False, PhotoImage(file=icon_path))

    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=0)

    ttk.Label(frame, text="tdfExtract", font=("Helvetica", 16)).grid(row=0, column=0, columnspan=2, pady=(0, 20))

    batch_button = ttk.Button(frame, text="Batch Extraction", command=on_batch_process, bootstyle="primary", padding=(12, 6))
    batch_button.grid(row=0, column=1, sticky=tk.E, padx=10)

    ttk.Label(frame, text="Enter the m/z range for the ion of interest.", font=("Helvetica", 14)).grid(
        row=1, column=0, columnspan=2, pady=(0, 30)
    )

    ttk.Label(frame, text="Minimum m/z:", font=("Helvetica", 12)).grid(row=2, column=0, sticky=tk.E)
    mzmin_var = tk.StringVar(value="")
    mzmin_entry = ttk.Entry(frame, textvariable=mzmin_var, font=("Helvetica", 12))
    mzmin_entry.grid(row=2, column=1, sticky=(tk.W, tk.E))

    ttk.Label(frame, text="Maximum m/z:", font=("Helvetica", 12)).grid(row=3, column=0, sticky=tk.E)
    mzmax_var = tk.StringVar(value="")
    mzmax_entry = ttk.Entry(frame, textvariable=mzmax_var, font=("Helvetica", 12))
    mzmax_entry.grid(row=3, column=1, sticky=(tk.W, tk.E))

    extraction_frame = ttk.LabelFrame(frame, text="Extraction method", padding=(10, 5))
    extraction_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 20))
    extraction_method_var = tk.StringVar(value="method")
    method_radio = ttk.Radiobutton(
        extraction_frame, text="Automatically extract D6 voltage",
        variable=extraction_method_var, value="method"
    )
    method_radio.grid(row=0, column=0, sticky=tk.W)

    sort_columns_var = tk.BooleanVar(value=True)
    sort_checkbox = ttk.Checkbutton(frame, text="Sort columns by voltage before saving", variable=sort_columns_var)
    sort_checkbox.grid(row=5, column=0, columnspan=2, sticky=tk.W)

    binning_check = ttk.Checkbutton(frame, text="Re-bin mobility axis", variable=bin_mobility_var, command=toggle_binning)
    binning_check.grid(row=6, column=0, columnspan=2, sticky=tk.W)

    ccs_checkbox = ttk.Checkbutton(frame, text="Convert mobility to CCS", variable=ccs_conversion_var, command=toggle_ccs)
    ccs_checkbox.grid(row=8, column=0, columnspan=2, sticky=tk.W)

    summed_checkbox = ttk.Checkbutton(frame, text="Mobility filtering/summing", variable=sum_intensity_mode_var, command=toggle_sum_mode)
    summed_checkbox.grid(row=14, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

    # Place the output directory button (without text entry) at row 12.
    output_dir_btn = ttk.Button(frame, text="Select Output Directory", command=select_output_directory)
    output_dir_btn.grid(row=12, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(10, 0))

    advanced_button = ttk.Button(frame, text="Advanced Settings", command=open_advanced_settings, bootstyle="primary", padding=(10, 5))
    advanced_button.grid(row=16, column=0, columnspan=2, pady=20)

    ttk.Label(frame, text="Extraction output is saved in the selected folder as \"*_raw.csv\"", font=("Helvetica", 10)).grid(row=17, column=0, columnspan=2, pady=(5, 10))

    # Place the process button in its own frame with fixed height.
    button_frame = ttk.Frame(frame, height=60)
    button_frame.grid(row=18, column=0, columnspan=2, pady=20, sticky="ew")
    button_frame.grid_propagate(False)
    process_button = ttk.Button(button_frame, text="Select .d file", command=on_process, bootstyle="primary", padding=(10, 5))
    process_button.pack(expand=True)

    progress_var = tk.DoubleVar(value=0)
    progress_frame = ttk.Frame(frame, bootstyle="dark")
    progress_frame.grid(row=19, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20)
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100, length=300, bootstyle="info")
    progress_bar.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    status_var = tk.StringVar(value="Status: Ready")
    status_label = ttk.Label(frame, textvariable=status_var, font=("Helvetica", 12))
    status_label.grid(row=20, column=0, columnspan=2, sticky=(tk.W, tk.E))

    for child in frame.winfo_children():
        child.grid_configure(padx=10, pady=10)

    def update_status(status_message):
        status_var.set(status_message)
        root.update_idletasks()

    process_data.update_status = update_status

    root.mainloop()

if __name__ == "__main__":
    create_ui()
