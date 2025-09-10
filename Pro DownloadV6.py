import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse
import json
import concurrent.futures
from queue import Queue
import uuid
import hashlib
from datetime import datetime, timedelta
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import webbrowser

# --- Package Installation ---
def install_package(package):
    """Installs a package using pip, handling potential errors."""
    try:
        print(f"Attempting to install {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--upgrade"])
        print(f"{package} installed successfully.")
    except Exception as e:
        print(f"Error: Failed to install {package}. Please install it manually using 'pip install {package}'.\nDetails: {e}")
        if package in ["yt-dlp", "ttkbootstrap", "opencv-python", "pillow", "cryptography"]:
            sys.exit(1)

# Check and import necessary packages
try:
    import yt_dlp
except ImportError:
    install_package("yt-dlp")
    import yt_dlp

try:
    import ttkbootstrap as bootstrap
    from ttkbootstrap.constants import *
except ImportError:
    install_package("ttkbootstrap")
    import ttkbootstrap as bootstrap
    from ttkbootstrap.constants import *

try:
    import cv2
except ImportError:
    install_package("opencv-python")
    import cv2

try:
    from PIL import Image, ImageTk
except ImportError:
    install_package("pillow")
    from PIL import Image, ImageTk
    
try:
    from cryptography.fernet import Fernet
except ImportError:
    install_package("cryptography")
    from cryptography.fernet import Fernet

import numpy as np


# --- License Management System (Integrated from LicenseGenerator.py) ---
class LicenseManager:
    """Handles license generation, validation, and management"""
    
    def __init__(self, app_secret="PBKDF2HMAC"):
        self.app_secret = app_secret.encode()
        self.license_file = Path.home() / ".pro_downloader" / "license.dat"
        self.license_file.parent.mkdir(exist_ok=True)
        
        # Generate encryption key from app secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'pro_downloader_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.app_secret))
        self.cipher_suite = Fernet(key)
    
    def generate_license_key(self, duration_days, user_id=None, extra_data=None):
        """Generate a license key for specified duration"""
        if user_id is None:
            user_id = str(uuid.uuid4())
        issue_date = datetime.now()
        expiry_date = issue_date + timedelta(days=duration_days)
        license_data = {
            'user_id': user_id,
            'issue_date': issue_date.isoformat(),
            'expiry_date': expiry_date.isoformat(),
            'duration_days': duration_days,
            'version': '4.0',
            'features': ['download', 'processing', 'parallel'],
            'extra_data': extra_data or {}
        }
        # Create signature for tamper protection
        data_string = json.dumps(license_data, sort_keys=True)
        signature = hashlib.sha256((data_string + self.app_secret.decode()).encode()).hexdigest()
        license_data['signature'] = signature
        # Encrypt the license data
        encrypted_data = self.cipher_suite.encrypt(json.dumps(license_data).encode())
        # Create final license key (base64 encoded)
        license_key = base64.b64encode(encrypted_data).decode()
        return license_key, license_data
    
    def validate_license_key(self, license_key):
        """Validate a license key and return license info"""
        try:
            encrypted_data = base64.b64decode(license_key.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            license_data = json.loads(decrypted_data.decode())
            # Verify signature
            signature = license_data.pop('signature')
            data_string = json.dumps(license_data, sort_keys=True)
            expected_signature = hashlib.sha256((data_string + self.app_secret.decode()).encode()).hexdigest()
            if signature != expected_signature:
                return False, "Invalid license signature"
            # Check expiry
            expiry_date = datetime.fromisoformat(license_data['expiry_date'])
            if datetime.now() > expiry_date:
                return False, "License expired"
            return True, license_data
        except Exception as e:
            return False, f"License validation error: {str(e)}"
    
    def save_license(self, license_key):
        """Save license key to local file"""
        try:
            with open(self.license_file, 'w') as f:
                f.write(license_key)
            return True
        except Exception:
            return False
    
    def load_license(self):
        """Load license key from local file"""
        try:
            if self.license_file.exists():
                with open(self.license_file, 'r') as f:
                    return f.read().strip()
            return None
        except Exception:
            return None
    
    def get_license_info(self):
        """Get current license information"""
        license_key = self.load_license()
        if not license_key:
            return False, "No license found"
        return self.validate_license_key(license_key)
    
    def remove_license(self):
        """Remove current license"""
        try:
            if self.license_file.exists():
                self.license_file.unlink()
            return True
        except Exception:
            return False


class LicenseDialog:
    """License activation dialog"""
    
    def __init__(self, parent, license_manager):
        self.parent = parent
        self.license_manager = license_manager
        self.dialog = None
        self.result = False
    
    def show_activation_dialog(self):
        """Show license activation dialog"""
        self.dialog = bootstrap.Toplevel(title="License Activation Required")
        self.dialog.geometry("600x500")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame, style='secondary.TFrame', padding=15)
        header_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(
            header_frame,
            text="Pro Video Downloader & Processor Suite",
            font=('Segoe UI', 18, 'bold'),
            style='secondary.Inverse.TLabel'
        ).pack()
        
        ttk.Label(
            header_frame,
            text="License Activation Required",
            font=('Segoe UI', 14),
            style='secondary.Inverse.TLabel'
        ).pack()
        
        # License input section
        input_frame = ttk.Labelframe(main_frame, text=" Enter License Key ", padding=15)
        input_frame.pack(fill='x', pady=(0, 15))
        
        self.license_var = tk.StringVar()
        
        ttk.Label(input_frame, text="License Key:", font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 5))
        
        key_frame = ttk.Frame(input_frame)
        key_frame.pack(fill='x', pady=(0, 10))
        
        self.license_entry = ttk.Entry(
            key_frame, 
            textvariable=self.license_var,
            font=('Consolas', 10),
            show='*'  # Hide the key by default
        )
        self.license_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        # Show/hide key button
        self.show_key = tk.BooleanVar()
        show_btn = ttk.Checkbutton(
            key_frame, 
            text="Show", 
            variable=self.show_key,
            command=self.toggle_key_visibility,
            style='primary.Roundtoggle.Toolbutton'
        )
        show_btn.pack(side='right')
        
        # Paste button
        ttk.Button(
            input_frame,
            text="Paste from Clipboard",
            command=self.paste_license,
            style='info-outline.TButton'
        ).pack(pady=(0, 10))
        
        # Status area
        self.status_frame = ttk.Labelframe(main_frame, text=" License Status ", padding=15)
        self.status_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        self.status_text = tk.Text(
            self.status_frame, 
            height=8, 
            font=('Segoe UI', 10),
            wrap='word',
            state='disabled'
        )
        self.status_text.pack(fill='both', expand=True)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x')
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        ttk.Button(
            button_frame,
            text="Activate License",
            command=self.activate_license,
            style='success.TButton'
        ).grid(row=0, column=0, sticky='ew', padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="Trial Mode",
            command=self.start_trial,
            style='warning.TButton'
        ).grid(row=0, column=1, sticky='ew', padx=5)
        
        ttk.Button(
            button_frame,
            text="Exit",
            command=self.close_dialog,
            style='danger.TButton'
        ).grid(row=0, column=2, sticky='ew', padx=(5, 0))
        
        self.update_status("Please enter your license key to continue.")
        
        # Check for existing license
        is_valid, info = self.license_manager.get_license_info()
        if is_valid:
            self.show_license_info(info)
        
        self.dialog.focus_set()
        self.license_entry.focus_set()
        
        # Bind Enter key
        self.license_entry.bind('<Return>', lambda e: self.activate_license())
        # Bind Ctrl+V / Command+V to paste license (works when focus on entry)
        try:
            self.license_entry.bind('<Control-v>', lambda e: self.paste_license())
            self.license_entry.bind('<Control-V>', lambda e: self.paste_license())
        except Exception:
            pass
        
        self.dialog.wait_window()
        return self.result
    
    def toggle_key_visibility(self):
        """Toggle license key visibility"""
        if self.show_key.get():
            self.license_entry.config(show='')
        else:
            self.license_entry.config(show='*')
    
    def paste_license(self):
        """Paste license from clipboard"""
        # Try multiple clipboard sources to be more reliable across platforms and contexts
        clipboard_text = None
        try:
            # Prefer the root window clipboard if available
            clipboard_text = self.parent.clipboard_get()
        except Exception:
            try:
                clipboard_text = self.dialog.clipboard_get()
            except Exception:
                try:
                    clipboard_text = self.parent.tk.call('tk', 'clipboard', 'get')
                except Exception:
                    clipboard_text = None

        if clipboard_text:
            # Clean up whitespace/newlines that sometimes get added
            cleaned = clipboard_text.strip()
            self.license_var.set(cleaned)
            self.update_status("License pasted from clipboard. Click Activate to validate.")
        else:
            self.update_status("Error: Could not paste from clipboard.")
    
    def activate_license(self):
        """Activate the entered license"""
        license_key = self.license_var.get().strip()
        if not license_key:
            self.update_status("Error: Please enter a license key.")
            return
        
        self.update_status("Validating license...")
        
        # Validate license
        is_valid, result = self.license_manager.validate_license_key(license_key)
        
        if is_valid:
            # Save license
            if self.license_manager.save_license(license_key):
                self.show_license_info(result)
                self.result = True
                
                # Auto-close after successful activation
                self.dialog.after(2000, self.close_dialog)
            else:
                self.update_status("Error: Could not save license file.")
        else:
            self.update_status(f"License Validation Failed: {result}")
    
    def start_trial(self):
        """Start trial mode (if implemented)"""
        if self.license_manager.load_license():
            messagebox.showinfo("Trial Mode", "A license is already present. Please remove it to start a trial.")
            return
            
        trial_key, _ = self.license_manager.generate_license_key(
            duration_days=7,
            user_id="trial_user",
            extra_data={"type": "trial"}
        )
        
        if self.license_manager.save_license(trial_key):
            self.update_status("Trial mode activated (7 days)")
            self.result = True
            self.dialog.after(1500, self.close_dialog)
        else:
            self.update_status("Error: Could not start trial mode.")
    
    def show_license_info(self, license_data):
        """Display license information"""
        issue_date = datetime.fromisoformat(license_data['issue_date'])
        expiry_date = datetime.fromisoformat(license_data['expiry_date'])
        days_remaining = (expiry_date - datetime.now()).days
        
        info_text = f"""✓ LICENSE ACTIVATED SUCCESSFULLY

User ID: {license_data['user_id'][:16]}...
Issue Date: {issue_date.strftime('%Y-%m-%d %H:%M')}
Expiry Date: {expiry_date.strftime('%Y-%m-%d %H:%M')}
Days Remaining: {days_remaining} day(s)
Duration: {license_data['duration_days']} days
Version: {license_data['version']}

Features Enabled:
• Video Downloads from 1000+ platforms
• Parallel downloading (up to 5 concurrent)
• Advanced video processing & enhancement
• Batch processing capabilities
• Multiple processing tabs

Status: ACTIVE"""
        
        self.update_status(info_text)
    
    def update_status(self, message):
        """Update status text"""
        self.status_text.config(state='normal')
        self.status_text.delete(1.0, 'end')
        self.status_text.insert(1.0, message)
        self.status_text.config(state='disabled')
    
    def close_dialog(self):
        """Close the dialog"""
        if self.dialog:
            self.dialog.destroy()


# --- Enhanced Video Processing Class ---
class VideoProcessor:
    """Handles video processing operations with parallel processing support."""
    
    def __init__(self, progress_callback=None, status_callback=None, task_id=None):
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.task_id = task_id
        
    def process_video(self, input_path, output_path, method="sharpen", intensity=1.0):
        """Process video to remove blur and enhance smoothness."""
        try:
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                raise Exception("Could not open input video")
            
            # Get video properties
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Setup video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            frame_count = 0
            
            if self.status_callback:
                self.status_callback(f"Processing {os.path.basename(input_path)}: {method} (Intensity: {intensity})", self.task_id)
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Apply the selected processing method
                processed_frame = self._apply_processing(frame, method, intensity)
                out.write(processed_frame)
                
                frame_count += 1
                if self.progress_callback and total_frames > 0:
                    progress = (frame_count / total_frames) * 100
                    self.progress_callback(progress, self.task_id)
            
            cap.release()
            out.release()
            
            if self.status_callback:
                self.status_callback(f"Video processing completed: {os.path.basename(output_path)}", self.task_id)
            
            return True
            
        except Exception as e:
            if self.status_callback:
                self.status_callback(f"Error processing {os.path.basename(input_path)}: {str(e)}", self.task_id)
            return False
    
    def _apply_processing(self, frame, method, intensity):
        """Apply the specified processing method to a frame."""
        if method == "sharpen":
            return self._sharpen_frame(frame, intensity)
        elif method == "deblur":
            return self._deblur_frame(frame, intensity)
        elif method == "enhance":
            return self._enhance_frame(frame, intensity)
        elif method == "stabilize":
            return self._stabilize_frame(frame, intensity)
        else:
            return frame
    
    def _sharpen_frame(self, frame, intensity):
        """Apply unsharp masking to sharpen the frame."""
        gaussian = cv2.GaussianBlur(frame, (0, 0), 2.0)
        unsharp_mask = cv2.addWeighted(frame, 1.0 + intensity, gaussian, -intensity, 0)
        return unsharp_mask
    
    def _deblur_frame(self, frame, intensity):
        """Apply advanced deblurring techniques."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        clahe = cv2.createCLAHE(clipLimit=2.0 * intensity, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        result = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        return cv2.addWeighted(frame, 1.0 - intensity * 0.5, result, intensity * 0.5, 0)
    
    def _enhance_frame(self, frame, intensity):
        """Enhance frame details and reduce noise."""
        smooth = cv2.bilateralFilter(frame, 9, 80, 80)
        detail_mask = cv2.subtract(frame, smooth)
        detail_enhanced = cv2.add(frame, cv2.multiply(detail_mask, intensity))
        return np.clip(detail_enhanced, 0, 255).astype(np.uint8)
    
    def _stabilize_frame(self, frame, intensity):
        """Basic frame stabilization (simplified)."""
        stabilized = cv2.GaussianBlur(frame, (5, 5), intensity)
        return cv2.addWeighted(frame, 0.7, stabilized, 0.3, 0)


# --- Parallel Task Manager ---
class ParallelTaskManager:
    """Manages parallel execution of downloads and video processing tasks."""
    
    def __init__(self, max_workers=10):
        # Increase default worker pool to better support large parallel operations
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = {}
        self.task_queue = Queue()
        self.callbacks = {}
        
    def submit_download_task(self, task_id, download_func, url, **kwargs):
        """Submit a download task for parallel execution."""
        future = self.executor.submit(download_func, url, **kwargs)
        self.active_tasks[task_id] = {
            'future': future,
            'type': 'download',
            'url': url,
            'status': 'Running'
        }
        return future
    
    def submit_processing_task(self, task_id, process_func, input_path, output_path, **kwargs):
        """Submit a video processing task for parallel execution."""
        future = self.executor.submit(process_func, input_path, output_path, **kwargs)
        self.active_tasks[task_id] = {
            'future': future,
            'type': 'processing',
            'input_path': input_path,
            'output_path': output_path,
            'status': 'Running'
        }
        return future
    
    def get_active_task_count(self):
        """Get the number of currently active tasks."""
        return len([task for task in self.active_tasks.values() if task['status'] == 'Running'])
    
    def cancel_task(self, task_id):
        """Cancel a specific task."""
        if task_id in self.active_tasks:
            future = self.active_tasks[task_id]['future']
            cancelled = future.cancel()
            if cancelled:
                self.active_tasks[task_id]['status'] = 'Cancelled'
            return cancelled
        return False
    
    def shutdown(self):
        """Shutdown the task manager."""
        self.executor.shutdown(wait=True)


# --- Multiple Processing Tabs Manager ---
class ProcessingTabManager:
    """Manages multiple processing tabs for different video tasks."""
    
    def __init__(self, parent):
        self.parent = parent
        self.tabs = {}
        self.tab_counter = 0
        
    def create_new_tab(self, tab_name=None):
        """Create a new processing tab."""
        self.tab_counter += 1
        if not tab_name:
            tab_name = f"Process {self.tab_counter}"
        
        tab_id = str(uuid.uuid4())
        
        # Create new tab frame
        tab_frame = ttk.Frame(self.parent.processing_notebook, padding=15)
        self.parent.processing_notebook.add(tab_frame, text=tab_name)
        
        # Create processing interface for this tab
        tab_data = {
            'frame': tab_frame,
            'name': tab_name,
            'input_var': tk.StringVar(),
            'output_var': tk.StringVar(),
            'method_var': tk.StringVar(value="sharpen"),
            'intensity_var': tk.DoubleVar(value=1.0),
            'task_id': None
        }
        
        self._setup_tab_interface(tab_data)
        self.tabs[tab_id] = tab_data
        
        return tab_id
    
    def _setup_tab_interface(self, tab_data):
        """Setup the interface for a processing tab."""
        frame = tab_data['frame']
        
        # Input Video Section
        input_frame = self.parent._create_styled_frame(frame, "Input Video")
        input_content = ttk.Frame(input_frame, padding=10)
        input_content.pack(fill=X)
        
        input_entry = ttk.Entry(input_content, textvariable=tab_data['input_var'], font=('Consolas', 11))
        input_entry.pack(side=LEFT, fill=X, expand=True, ipady=3)
        
        browse_input_btn = ttk.Button(
            input_content, text="Browse", 
            command=lambda: self._browse_input_for_tab(tab_data),
            style='primary-outline.TButton'
        )
        browse_input_btn.pack(side=RIGHT, padx=(10, 0))
        
        # Output Video Section
        output_frame = self.parent._create_styled_frame(frame, "Output Video")
        output_content = ttk.Frame(output_frame, padding=10)
        output_content.pack(fill=X)
        
        output_entry = ttk.Entry(output_content, textvariable=tab_data['output_var'], font=('Consolas', 11))
        output_entry.pack(side=LEFT, fill=X, expand=True, ipady=3)
        
        browse_output_btn = ttk.Button(
            output_content, text="Save As",
            command=lambda: self._browse_output_for_tab(tab_data),
            style='success-outline.TButton'
        )
        browse_output_btn.pack(side=RIGHT, padx=(10, 0))
        
        # Processing Settings
        settings_frame = self.parent._create_styled_frame(frame, "Enhancement Settings")
        settings_content = ttk.Frame(settings_frame, padding=10)
        settings_content.pack(fill=BOTH, expand=True)
        settings_content.grid_columnconfigure(1, weight=1)
        
        # Processing Method
        ttk.Label(settings_content, text="Method:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky=W, pady=5, padx=(0, 15))
        method_options = [
            ("sharpen", "Sharpen (Remove Blur)"),
            ("deblur", "Advanced Deblur"),
            ("enhance", "Detail Enhancement"),
            ("stabilize", "Video Stabilization")
        ]
        method_combo = ttk.Combobox(
            settings_content, 
            values=[desc for _, desc in method_options],
            state="readonly",
            style='warning.TCombobox'
        )
        method_combo.grid(row=0, column=1, sticky=EW, pady=5)
        method_combo.set("Sharpen (Remove Blur)")
        
        def on_method_change(event):
            selected_desc = method_combo.get()
            for method, desc in method_options:
                if desc == selected_desc:
                    tab_data['method_var'].set(method)
                    break
        
        method_combo.bind('<<ComboboxSelected>>', on_method_change)
        
        # Intensity Slider
        ttk.Label(settings_content, text="Intensity:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky=W, pady=5, padx=(0, 15))
        intensity_frame = ttk.Frame(settings_content)
        intensity_frame.grid(row=1, column=1, sticky=EW, pady=5)
        intensity_frame.grid_columnconfigure(0, weight=1)
        
        intensity_scale = ttk.Scale(
            intensity_frame, from_=0.1, to=3.0, variable=tab_data['intensity_var'],
            orient=HORIZONTAL, style='success.TScale'
        )
        intensity_scale.grid(row=0, column=0, sticky=EW, padx=(0, 10))
        
        intensity_label = ttk.Label(intensity_frame, text="1.0", font=('Segoe UI', 10, 'bold'))
        intensity_label.grid(row=0, column=1)
        
        def update_intensity_label(val):
            intensity_label.config(text=f"{float(val):.1f}")
        
        intensity_scale.configure(command=update_intensity_label)
        
        # Process Button
        process_frame = ttk.Frame(frame, padding=(0, 15))
        process_frame.pack(fill=X, side=BOTTOM)
        process_frame.grid_columnconfigure((0, 1), weight=1)
        
        process_btn = ttk.Button(
            process_frame, text="Process Video",
            command=lambda: self.parent.start_video_processing_for_tab(tab_data),
            style='success.TButton'
        )
        process_btn.grid(row=0, column=0, sticky=EW, ipady=10, padx=(0, 5))
        
        close_tab_btn = ttk.Button(
            process_frame, text="Close Tab",
            command=lambda: self._close_tab(tab_data),
            style='danger-outline.TButton'
        )
        close_tab_btn.grid(row=0, column=1, sticky=EW, ipady=10, padx=(5, 0))
        
        tab_data['process_btn'] = process_btn
    
    def _browse_input_for_tab(self, tab_data):
        """Browse for input video file for specific tab."""
        filetypes = [
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm"),
            ("All files", "*.*")
        ]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            tab_data['input_var'].set(filepath)
            # Auto-suggest output path
            input_path = Path(filepath)
            output_path = input_path.parent / f"{input_path.stem}_enhanced{input_path.suffix}"
            tab_data['output_var'].set(str(output_path))
    
    def _browse_output_for_tab(self, tab_data):
        """Browse for output video file location for specific tab."""
        filetypes = [
            ("MP4 files", "*.mp4"),
            ("AVI files", "*.avi"),
            ("MKV files", "*.mkv"),
            ("All files", "*.*")
        ]
        filepath = filedialog.asksaveasfilename(filetypes=filetypes, defaultextension=".mp4")
        if filepath:
            tab_data['output_var'].set(filepath)
    
    def _close_tab(self, tab_data):
        """Close a specific processing tab."""
        # Cancel any running task for this tab
        if tab_data['task_id'] and tab_data['task_id'] in self.parent.task_manager.active_tasks:
            self.parent.task_manager.cancel_task(tab_data['task_id'])
        
        # Remove tab from notebook
        for tab_id, data in list(self.tabs.items()):
            if data == tab_data:
                self.parent.processing_notebook.forget(data['frame'])
                del self.tabs[tab_id]
                break


# --- Enhanced Main Application Class ---
class VideoDownloader:
    """Enhanced video downloader with parallel processing and multiple tabs."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Pro Video Downloader & Processor Suite v4.0 - Parallel Edition")
        self.root.geometry("1600x1100")
        self.root.minsize(1400, 1000)

        # Use a modern, clean theme
        self.style = bootstrap.Style(theme='litera')
        self.root.configure(bg=self.style.colors.bg)

        # --- Enhanced State Variables ---
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value="Best Quality (1080p+, 30fps+)")
        self.format_var = tk.StringVar(value="mp4 (Best Compatibility)")
        self.output_path = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready - Enhanced with Parallel Processing")
        self.youtube_fix_var = tk.StringVar(value="Smart Fix (Auto)")
        self.fps_var = tk.StringVar(value="30+")
        self.audio_quality_var = tk.StringVar(value="Best Available")
        self.subtitle_var = tk.BooleanVar(value=True)
        self.thumbnail_var = tk.BooleanVar(value=False)

        # Parallel processing settings
        # increase sensible defaults for a faster, high-parallel environment
        self.max_concurrent_downloads = tk.IntVar(value=8)
        self.max_concurrent_processing = tk.IntVar(value=4)

        # Data stores
        self.url_list = []
        self.processing_tasks = {}
        
        # Initialize parallel task manager
        self.task_manager = ParallelTaskManager(max_workers=5)
        
        # Initialize processing tab manager
        self.processing_tab_manager = None

        # --- UI Setup ---
        self.setup_ui()
    
    def setup_ui(self):
        """Builds the main user interface."""
        self._create_header()
        self._create_main_content_area()
        # Placeholder for locked overlay (created when needed)
        self._locked_overlay = None
        self.locked = False
        self.controls_locked = False

    def update_controls_locked(self, locked: bool):
        """Enable/disable main action controls based on license state."""
        self.controls_locked = locked
        state = 'disabled' if locked else 'normal'
        # Download buttons
        try:
            if hasattr(self, 'download_single_btn'):
                self.download_single_btn.configure(state=state)
            if hasattr(self, 'download_batch_btn'):
                self.download_batch_btn.configure(state=state)
            if hasattr(self, 'info_btn'):
                self.info_btn.configure(state=state)
        except Exception:
            pass

        # Processing buttons in each tab
        try:
            if self.processing_tab_manager:
                for tab_data in self.processing_tab_manager.tabs.values():
                    btn = tab_data.get('process_btn')
                    if btn:
                        try:
                            btn.configure(state=state)
                        except Exception:
                            pass
        except Exception:
            pass

    def require_license(self, show_message=True):
        """Return True if a valid license exists. If not, optionally show a message and return False.

        This central check ensures downloads and processing are blocked until the user activates a license.
        """
        try:
            if not hasattr(self, 'license_manager'):
                # Fallback: create a manager to check for license file
                lm = LicenseManager()
            else:
                lm = self.license_manager

            is_valid, info = lm.get_license_info()
            if is_valid:
                return True
        except Exception:
            # If anything goes wrong, treat as not licensed
            is_valid = False

        if show_message:
            try:
                messagebox.showwarning(
                    "License Required",
                    "Download and processing functions are disabled until you activate a valid license.\n\n"
                    "Press Ctrl+Shift+L to open the activation dialog or Ctrl+Shift+V to paste a license from clipboard."
                )
            except Exception:
                print("License required: cannot show messagebox")
        return False

    def _create_header(self):
        """Creates the top header section."""
        header_frame = ttk.Frame(self.root, style='secondary.TFrame', padding=(20, 15))
        header_frame.pack(fill=X, side=TOP)

        ttk.Label(
            header_frame,
            text="Pro Video Downloader & Processor Suite v4.0",
            font=('Segoe UI', 24, 'bold'),
            style='secondary.Inverse.TLabel'
        ).pack(side=LEFT)

        # Status indicators
        status_frame = ttk.Frame(header_frame)
        status_frame.pack(side=RIGHT)
        
        self.active_downloads_label = ttk.Label(
            status_frame,
            text="Downloads: 0/3",
            font=('Segoe UI', 10, 'bold'),
            style='secondary.Inverse.TLabel'
        )
        self.active_downloads_label.pack(side=RIGHT, padx=(0, 15))
        
        self.active_processing_label = ttk.Label(
            status_frame,
            text="Processing: 0/2",
            font=('Segoe UI', 10, 'bold'),
            style='secondary.Inverse.TLabel'
        )
        self.active_processing_label.pack(side=RIGHT, padx=(0, 15))

    def _create_main_content_area(self):
        """Creates the main layout with enhanced parallel processing."""
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=True)
        main_frame.grid_columnconfigure(1, weight=3)
        main_frame.grid_rowconfigure(0, weight=1)

        # --- Left Panel (Enhanced Controls) ---
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self._create_control_tabs(left_panel)

        # --- Right Panel (Queue & Progress with Task Monitor) ---
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_rowconfigure(2, weight=1)
        self._create_progress_section(right_panel)
        self._create_task_monitor_section(right_panel)
        self._create_queue_section(right_panel)

    def _create_control_tabs(self, parent):
        """Creates the tabbed interface with enhanced processing tabs."""
        notebook = ttk.Notebook(parent, style='primary.TNotebook')
        notebook.pack(fill=BOTH, expand=True)

        # Create tabs
        download_tab = ttk.Frame(notebook, padding=15)
        bulk_import_tab = ttk.Frame(notebook, padding=15)
        processing_tab = ttk.Frame(notebook, padding=15)
        parallel_tab = ttk.Frame(notebook, padding=15)
        advanced_tab = ttk.Frame(notebook, padding=15)

        notebook.add(download_tab, text="  Download  ")
        notebook.add(bulk_import_tab, text="  Bulk Import  ")
        notebook.add(processing_tab, text="  Processing  ")
        notebook.add(parallel_tab, text="  Parallel Settings  ")
        notebook.add(advanced_tab, text="  Advanced  ")

        # Populate tabs
        self._populate_download_tab(download_tab)
        self._populate_bulk_import_tab(bulk_import_tab)
        self._populate_enhanced_processing_tab(processing_tab)
        self._populate_parallel_settings_tab(parallel_tab)
        self._populate_advanced_tab(advanced_tab)

    def _populate_enhanced_processing_tab(self, parent):
        """Enhanced processing tab with multiple processing windows."""
        # Create notebook for processing tabs
        self.processing_notebook = ttk.Notebook(parent, style='warning.TNotebook')
        self.processing_notebook.pack(fill=BOTH, expand=True, pady=(0, 15))
        
        # Initialize tab manager
        self.processing_tab_manager = ProcessingTabManager(self)
        
        # Create initial processing tab
        self.processing_tab_manager.create_new_tab("Main Process")
        
        # Control buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=X)
        control_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        ttk.Button(
            control_frame, text="New Processing Tab",
            command=lambda: self.processing_tab_manager.create_new_tab(),
            style='primary.TButton'
        ).grid(row=0, column=0, sticky=EW, padx=(0, 5))
        
        ttk.Button(
            control_frame, text="Batch Processor",
            command=self.create_enhanced_batch_window,
            style='success.TButton'
        ).grid(row=0, column=1, sticky=EW, padx=5)
        
        ttk.Button(
            control_frame, text="Processing Presets",
            command=self.create_processing_presets_window,
            style='info.TButton'
        ).grid(row=0, column=2, sticky=EW, padx=(5, 0))

    def _populate_parallel_settings_tab(self, parent):
        """Populate the parallel processing settings tab."""
        settings_frame = self._create_styled_frame(parent, "Concurrent Processing Limits")
        settings_content = ttk.Frame(settings_frame, padding=15)
        settings_content.pack(fill=BOTH, expand=True)
        settings_content.grid_columnconfigure(1, weight=1)
        
        # Download concurrency
        ttk.Label(settings_content, text="Max Concurrent Downloads:", font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, sticky=W, pady=10, padx=(0, 15))
        # allow a wide range from 1 to 100 for aggressive parallel downloads if needed
        download_scale = ttk.Scale(
            settings_content, from_=1, to=100, variable=self.max_concurrent_downloads,
            orient=HORIZONTAL, style='primary.TScale'
        )
        download_scale.grid(row=0, column=1, sticky=EW, padx=(0, 10))
        
        self.download_count_label = ttk.Label(settings_content, text=str(self.max_concurrent_downloads.get()), font=('Segoe UI', 11, 'bold'))
        self.download_count_label.grid(row=0, column=2)
        
        def update_download_label(val):
            count = int(float(val))
            self.download_count_label.config(text=str(count))
            self.update_header_status()
        
        download_scale.configure(command=update_download_label)
        
        # Processing concurrency
        ttk.Label(settings_content, text="Max Concurrent Video Processing:", font=('Segoe UI', 11, 'bold')).grid(row=1, column=0, sticky=W, pady=10, padx=(0, 15))
        # allow a larger processing pool for powerful CPUs (range up to 50)
        processing_scale = ttk.Scale(
            settings_content, from_=1, to=50, variable=self.max_concurrent_processing,
            orient=HORIZONTAL, style='success.TScale'
        )
        processing_scale.grid(row=1, column=1, sticky=EW, padx=(0, 10))
        
        self.processing_count_label = ttk.Label(settings_content, text=str(self.max_concurrent_processing.get()), font=('Segoe UI', 11, 'bold'))
        self.processing_count_label.grid(row=1, column=2)
        
        def update_processing_label(val):
            count = int(float(val))
            self.processing_count_label.config(text=str(count))
            self.update_header_status()
        
        processing_scale.configure(command=update_processing_label)
        
        # Performance info
        info_frame = self._create_styled_frame(parent, "Performance Information")
        info_content = ttk.Frame(info_frame, padding=15)
        info_content.pack(fill=BOTH, expand=True)
        
        info_text = scrolledtext.ScrolledText(
            info_content, height=8, font=('Segoe UI', 10), wrap='word',
            bg=self.style.colors.inputbg, fg=self.style.colors.fg
        )
        info_text.pack(fill=BOTH, expand=True)
        
        info_content_text = """
PARALLEL PROCESSING BENEFITS:

✓ Download 2-3 videos simultaneously for faster batch processing
✓ Process multiple videos concurrently while downloading others
✓ Better CPU and network utilization
✓ Reduced total processing time for large batches

RECOMMENDATIONS:
• For fast internet: Use 3-5 concurrent downloads
• For video processing: Use 2-3 concurrent processes (depends on CPU cores)
• Monitor system resources to avoid overload
• Close other heavy applications for optimal performance

SYSTEM MONITORING:
The task monitor shows real-time status of all running operations.
"""
        info_text.insert('1.0', info_content_text)
        info_text.config(state='disabled')

    def _create_task_monitor_section(self, parent):
        """Create the task monitoring section."""
        monitor_frame = ttk.Labelframe(parent, text=" Active Tasks Monitor ", style='warning.TLabelframe')
        monitor_frame.grid(row=1, column=0, sticky="ew", pady=15)
        monitor_frame.grid_columnconfigure(0, weight=1)
        
        # Task list with scrollbar
        monitor_content = ttk.Frame(monitor_frame, padding=10)
        monitor_content.grid(row=0, column=0, sticky=EW)
        monitor_content.grid_rowconfigure(0, weight=1)
        monitor_content.grid_columnconfigure(0, weight=1)
        
        # Task treeview
        task_columns = ('Type', 'Item', 'Progress', 'Status')
        self.task_tree = ttk.Treeview(
            monitor_content, columns=task_columns, show='headings',
            height=6, style='warning.Treeview'
        )
        
        # Configure columns
        self.task_tree.heading('Type', text='Type')
        self.task_tree.column('Type', width=80, minwidth=60, anchor=CENTER)
        self.task_tree.heading('Item', text='Item')
        self.task_tree.column('Item', width=200, minwidth=150)
        self.task_tree.heading('Progress', text='Progress')
        self.task_tree.column('Progress', width=80, minwidth=60, anchor=CENTER)
        self.task_tree.heading('Status', text='Status')
        self.task_tree.column('Status', width=120, minwidth=100)
        
        self.task_tree.grid(row=0, column=0, sticky='ew')
        
        task_scrollbar = ttk.Scrollbar(monitor_content, orient=VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=task_scrollbar.set)
        task_scrollbar.grid(row=0, column=1, sticky='ns')

    def update_header_status(self):
        """Update header status indicators."""
        active_downloads = len([t for t in self.task_manager.active_tasks.values() if t['type'] == 'download' and t['status'] == 'Running'])
        active_processing = len([t for t in self.task_manager.active_tasks.values() if t['type'] == 'processing' and t['status'] == 'Running'])
        
        max_downloads = self.max_concurrent_downloads.get()
        max_processing = self.max_concurrent_processing.get()
        
        self.active_downloads_label.config(text=f"Downloads: {active_downloads}/{max_downloads}")
        self.active_processing_label.config(text=f"Processing: {active_processing}/{max_processing}")

    def update_task_monitor(self):
        """Update the task monitor display."""
        # Clear existing items
        self.task_tree.delete(*self.task_tree.get_children())
        
        # Add current tasks
        for task_id, task_info in self.task_manager.active_tasks.items():
            task_type = task_info['type'].title()
            
            if task_info['type'] == 'download':
                item_name = os.path.basename(task_info.get('url', 'Unknown'))[:30]
            else:
                item_name = os.path.basename(task_info.get('input_path', 'Unknown'))[:30]
            
            progress = task_info.get('progress', 0)
            progress_text = f"{progress:.1f}%" if progress > 0 else "..."
            
            status = task_info['status']
            
            # Insert with color coding
            tag = 'running' if status == 'Running' else 'completed' if status == 'Completed' else 'error'
            self.task_tree.insert('', 'end', values=(task_type, item_name, progress_text, status), tags=(tag,))
        
        # Configure tag colors
        self.task_tree.tag_configure('running', foreground='#00ff00')
        self.task_tree.tag_configure('completed', foreground='#0066ff')
        self.task_tree.tag_configure('error', foreground='#ff6666')

    def start_video_processing_for_tab(self, tab_data):
        """Start video processing for a specific tab."""
        # License guard: block processing until licensed
        if not self.require_license(show_message=True):
            return
        input_path = tab_data['input_var'].get()
        output_path = tab_data['output_var'].get()
        
        if not input_path or not output_path:
            messagebox.showerror("Error", "Please specify both input and output paths.")
            return
        
        if not os.path.exists(input_path):
            messagebox.showerror("Error", "Input video file does not exist.")
            return
        
        # Check if we can start a new processing task
        active_processing = len([t for t in self.task_manager.active_tasks.values() 
                               if t['type'] == 'processing' and t['status'] == 'Running'])
        
        if active_processing >= self.max_concurrent_processing.get():
            messagebox.showwarning("Warning", 
                f"Maximum concurrent processing tasks ({self.max_concurrent_processing.get()}) reached. "
                "Please wait for a task to complete or adjust settings.")
            return
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        tab_data['task_id'] = task_id
        
        # Disable the process button for this tab
        tab_data['process_btn'].configure(state='disabled', text="Processing...")
        
        # Create processor with callbacks
        processor = VideoProcessor(
            progress_callback=self.update_processing_progress,
            status_callback=self.update_processing_status,
            task_id=task_id
        )
        
        # Submit processing task
        method = tab_data['method_var'].get()
        intensity = tab_data['intensity_var'].get()
        
        future = self.task_manager.submit_processing_task(
            task_id, 
            processor.process_video,
            input_path, 
            output_path,
            method=method, 
            intensity=intensity
        )
        
        # Set up completion callback
        def on_processing_complete():
            try:
                success = future.result()
                self.root.after(0, lambda: self._handle_processing_completion(tab_data, task_id, success))
            except Exception as e:
                self.root.after(0, lambda: self._handle_processing_error(tab_data, task_id, str(e)))
        
        # Start completion monitor thread
        threading.Thread(target=on_processing_complete, daemon=True).start()
        
        self.update_header_status()
        self.update_task_monitor()

    def _handle_processing_completion(self, tab_data, task_id, success):
        """Handle processing completion for a tab."""
        # Re-enable the process button
        tab_data['process_btn'].configure(state='normal', text="Process Video")
        
        # Update task status
        if task_id in self.task_manager.active_tasks:
            self.task_manager.active_tasks[task_id]['status'] = 'Completed' if success else 'Failed'
        
        if success:
            output_path = tab_data['output_var'].get()
            messagebox.showinfo("Success", f"Video processing completed!\n\nOutput saved to:\n{output_path}")
        else:
            messagebox.showerror("Error", "Video processing failed. Check the task monitor for details.")
        
        self.update_header_status()
        self.update_task_monitor()

    def _handle_processing_error(self, tab_data, task_id, error_msg):
        """Handle processing error for a tab."""
        tab_data['process_btn'].configure(state='normal', text="Process Video")
        
        if task_id in self.task_manager.active_tasks:
            self.task_manager.active_tasks[task_id]['status'] = f'Error: {error_msg[:20]}'
        
        messagebox.showerror("Error", f"Processing failed:\n\n{error_msg}")
        
        self.update_header_status()
        self.update_task_monitor()

    def update_processing_progress(self, progress, task_id):
        """Update processing progress for specific task."""
        if task_id in self.task_manager.active_tasks:
            self.task_manager.active_tasks[task_id]['progress'] = progress
        self.root.after(0, self.update_task_monitor)

    def update_processing_status(self, status_text, task_id):
        """Update processing status for specific task."""
        if task_id in self.task_manager.active_tasks:
            # Don't override Running status with intermediate messages
            if self.task_manager.active_tasks[task_id]['status'] == 'Running':
                pass  # Keep as Running
        self.root.after(0, lambda: self.status_var.set(status_text))

    def create_enhanced_batch_window(self):
        """Create enhanced batch processing window with parallel support."""
        batch_window = bootstrap.Toplevel(title="Enhanced Batch Video Processor")
        batch_window.geometry("1200x800")
        
        main_frame = ttk.Frame(batch_window, padding=15)
        main_frame.pack(fill=BOTH, expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Enhanced controls frame
        controls_frame = ttk.Labelframe(main_frame, text=" Batch Controls ", style='primary.TLabelframe')
        controls_frame.grid(row=0, column=0, sticky=EW, pady=(0, 15))
        
        controls_content = ttk.Frame(controls_frame, padding=10)
        controls_content.pack(fill=X)
        controls_content.grid_columnconfigure((1, 3, 5), weight=1)
        
        # Add videos button
        ttk.Button(
            controls_content, text="Add Videos", 
            command=lambda: self.add_videos_to_enhanced_batch(batch_window),
            style='primary.TButton'
        ).grid(row=0, column=0, sticky=EW, padx=(0, 10))
        
        # Method selection
        ttk.Label(controls_content, text="Method:").grid(row=0, column=1, sticky=W, padx=(0, 5))
        batch_method_var = tk.StringVar(value="sharpen")
        method_combo = ttk.Combobox(
            controls_content, textvariable=batch_method_var,
            values=["sharpen", "deblur", "enhance", "stabilize"],
            state="readonly", width=12
        )
        method_combo.grid(row=0, column=2, padx=(0, 10))
        
        # Intensity
        ttk.Label(controls_content, text="Intensity:").grid(row=0, column=3, sticky=W, padx=(0, 5))
        batch_intensity_var = tk.DoubleVar(value=1.0)
        intensity_spin = ttk.Spinbox(
            controls_content, from_=0.1, to=3.0, increment=0.1,
            textvariable=batch_intensity_var, width=6
        )
        intensity_spin.grid(row=0, column=4, padx=(0, 10))
        
        # Concurrent processing setting
        ttk.Label(controls_content, text="Parallel:").grid(row=0, column=5, sticky=W, padx=(0, 5))
        parallel_var = tk.IntVar(value=2)
        # increase batch parallelism upper bound for power users
        parallel_spin = ttk.Spinbox(
            controls_content, from_=1, to=50, textvariable=parallel_var, width=4
        )
        parallel_spin.grid(row=0, column=6, padx=(0, 10))
        
        # Process batch button
        ttk.Button(
            controls_content, text="Process Batch", 
            command=lambda: self.start_enhanced_batch_processing(
                batch_window, batch_method_var.get(), batch_intensity_var.get(), parallel_var.get()
            ),
            style='success.TButton'
        ).grid(row=0, column=7, sticky=EW)
        
        # Enhanced queue display
        queue_frame = ttk.Labelframe(main_frame, text=" Processing Queue ", style='primary.TLabelframe')
        queue_frame.grid(row=1, column=0, sticky="nsew")
        queue_frame.grid_rowconfigure(0, weight=1)
        queue_frame.grid_columnconfigure(0, weight=1)
        
        # Batch queue treeview with enhanced columns
        batch_tree_frame = ttk.Frame(queue_frame, padding=10)
        batch_tree_frame.grid(row=0, column=0, sticky='nsew')
        batch_tree_frame.grid_rowconfigure(0, weight=1)
        batch_tree_frame.grid_columnconfigure(0, weight=1)
        
        batch_columns = ('Input', 'Output', 'Method', 'Intensity', 'Progress', 'Status', 'ETA')
        batch_tree = ttk.Treeview(
            batch_tree_frame, columns=batch_columns, show='headings'
        )
        
        # Configure enhanced columns
        column_widths = {'Input': 150, 'Output': 150, 'Method': 80, 'Intensity': 70, 
                        'Progress': 80, 'Status': 100, 'ETA': 70}
        
        for col in batch_columns:
            batch_tree.heading(col, text=col)
            batch_tree.column(col, width=column_widths.get(col, 100), minwidth=60)
        
        batch_tree.grid(row=0, column=0, sticky='nsew')
        
        batch_scrollbar = ttk.Scrollbar(batch_tree_frame, orient=VERTICAL, command=batch_tree.yview)
        batch_tree.configure(yscrollcommand=batch_scrollbar.set)
        batch_scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Store references for this batch window
        batch_window.batch_tree = batch_tree
        batch_window.batch_queue = []

    def add_videos_to_enhanced_batch(self, batch_window):
        """Add multiple videos to enhanced batch processing queue."""
        filetypes = [
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm"),
            ("All files", "*.*")
        ]
        filepaths = filedialog.askopenfilenames(filetypes=filetypes)
        
        if filepaths:
            output_dir = filedialog.askdirectory(title="Select output directory for processed videos")
            if not output_dir:
                return
            
            for filepath in filepaths:
                input_path = Path(filepath)
                output_path = Path(output_dir) / f"{input_path.stem}_enhanced{input_path.suffix}"
                
                job = {
                    'input': str(input_path),
                    'output': str(output_path),
                    'method': 'sharpen',
                    'intensity': 1.0,
                    'progress': 0,
                    'status': 'Queued',
                    'eta': '--',
                    'task_id': None
                }
                
                batch_window.batch_queue.append(job)
            
            self.update_enhanced_batch_tree(batch_window)
            messagebox.showinfo("Success", f"Added {len(filepaths)} videos to batch queue.")

    def update_enhanced_batch_tree(self, batch_window):
        """Update the enhanced batch processing tree view."""
        batch_window.batch_tree.delete(*batch_window.batch_tree.get_children())
        
        for job in batch_window.batch_queue:
            input_name = os.path.basename(job['input'])
            output_name = os.path.basename(job['output'])
            progress_text = f"{job['progress']:.1f}%" if job['progress'] > 0 else "0%"
            
            batch_window.batch_tree.insert('', 'end', values=(
                input_name, output_name, job['method'], 
                f"{job['intensity']:.1f}", progress_text, job['status'], job['eta']
            ))

    def start_enhanced_batch_processing(self, batch_window, method, intensity, max_parallel):
        """Start enhanced batch processing with parallel support."""
        # License guard: block batch processing until licensed
        if not self.require_license(show_message=True):
            return
        if not batch_window.batch_queue:
            messagebox.showwarning("Warning", "No videos in batch queue.")
            return
        
        # Update all jobs with current settings
        for job in batch_window.batch_queue:
            job['method'] = method
            job['intensity'] = intensity
            if job['status'] == 'Queued':
                job['status'] = 'Waiting'
        
        self.update_enhanced_batch_tree(batch_window)
        
        # Start parallel batch processing
        threading.Thread(
            target=self._enhanced_batch_worker, 
            args=(batch_window, max_parallel),
            daemon=True
        ).start()

    def _enhanced_batch_worker(self, batch_window, max_parallel):
        """Enhanced batch processing worker with parallel execution."""
        pending_jobs = [job for job in batch_window.batch_queue if job['status'] in ['Waiting', 'Queued']]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
            # Submit all jobs
            future_to_job = {}
            
            for job in pending_jobs:
                task_id = str(uuid.uuid4())
                job['task_id'] = task_id
                job['status'] = 'Processing'
                job['start_time'] = time.time()
                
                # Create processor for this job
                processor = VideoProcessor(
                    progress_callback=lambda p, tid=task_id: self._update_batch_progress(batch_window, tid, p),
                    status_callback=lambda s, tid=task_id: self._update_batch_status(batch_window, tid, s),
                    task_id=task_id
                )
                
                future = executor.submit(
                    processor.process_video,
                    job['input'], job['output'], job['method'], job['intensity']
                )
                future_to_job[future] = job
            
            self.root.after(0, lambda: self.update_enhanced_batch_tree(batch_window))
            
            # Process completed jobs
            completed = 0
            failed = 0
            
            for future in concurrent.futures.as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    success = future.result()
                    if success:
                        job['status'] = 'Completed'
                        job['progress'] = 100
                        completed += 1
                    else:
                        job['status'] = 'Failed'
                        failed += 1
                        
                except Exception as e:
                    job['status'] = f'Error: {str(e)[:20]}'
                    failed += 1
                
                job['eta'] = '--'
                self.root.after(0, lambda: self.update_enhanced_batch_tree(batch_window))
        
        # Final status update
        final_msg = f"Enhanced batch processing complete! {completed} successful, {failed} failed"
        self.root.after(0, lambda: messagebox.showinfo("Batch Complete", final_msg))

    def _update_batch_progress(self, batch_window, task_id, progress):
        """Update progress for a specific batch job."""
        for job in batch_window.batch_queue:
            if job.get('task_id') == task_id:
                job['progress'] = progress
                # Calculate ETA
                if progress > 0 and job.get('start_time'):
                    elapsed = time.time() - job['start_time']
                    total_time = elapsed * (100 / progress)
                    remaining = total_time - elapsed
                    job['eta'] = f"{int(remaining/60)}:{int(remaining%60):02d}"
                break
        
        self.root.after(0, lambda: self.update_enhanced_batch_tree(batch_window))

    def _update_batch_status(self, batch_window, task_id, status):
        """Update status for a specific batch job."""
        # Status updates are handled in the main worker
        pass

    # --- Enhanced Download Methods ---
    def start_parallel_batch_download(self):
        """Start downloading multiple items in parallel."""
        # License guard: block parallel downloads until licensed
        if not self.require_license(show_message=True):
            return
        if not self.url_list:
            messagebox.showwarning("Warning", "The download queue is empty.")
            return
        
        ready_urls = [item for item in self.url_list if 'Ready' in item['status']]
        if not ready_urls:
            messagebox.showinfo("Info", "No URLs are ready for download.")
            return
        
        max_concurrent = self.max_concurrent_downloads.get()
        
        if messagebox.askyesno("Confirm Parallel Download", 
                              f"Start parallel download of {len(ready_urls)} videos?\n"
                              f"Concurrent downloads: {max_concurrent}"):
            self.status_var.set("Starting parallel batch download...")
            threading.Thread(target=self._parallel_download_worker, args=(ready_urls,), daemon=True).start()

    def _parallel_download_worker(self, ready_items):
        """Worker for parallel downloads."""
        max_workers = self.max_concurrent_downloads.get()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit download tasks
            future_to_item = {}
            
            for item in ready_items:
                task_id = str(uuid.uuid4())
                item['task_id'] = task_id
                item['status'] = 'Downloading...'
                
                future = self.task_manager.submit_download_task(
                    task_id, self._download_single_item, item['url'], item=item
                )
                future_to_item[future] = item
            
            self.root.after(0, self.update_url_tree)
            self.root.after(0, self.update_header_status)
            self.root.after(0, self.update_task_monitor)
            
            # Process results
            successful = 0
            failed = 0
            
            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    success = future.result()
                    if success:
                        item['status'] = 'Downloaded'
                        successful += 1
                    else:
                        item['status'] = 'Failed'
                        failed += 1
                except Exception:
                    item['status'] = 'Error'
                    failed += 1
                
                self.root.after(0, self.update_url_tree)
        
        # Final update
        final_msg = f"Parallel download complete! {successful} successful, {failed} failed"
        self.root.after(0, lambda: self.status_var.set(final_msg))
        self.root.after(0, lambda: messagebox.showinfo("Download Complete", final_msg))
        self.root.after(0, self.update_header_status)
        self.root.after(0, self.update_task_monitor)

    def _download_single_item(self, url=None, item=None):
        """Download a single item (used by parallel downloader)."""
        try:
            return self.download_video(url, update_status=False)
        except Exception:
            return False

    # --- Standard UI Creation Methods (preserved from original) ---
    def _create_styled_frame(self, parent, title):
        """Helper to create a consistent styled frame with a title."""
        frame = ttk.Labelframe(parent, text=f" {title} ", style='primary.TLabelframe')
        frame.pack(fill=X, pady=(0, 15), expand=True)
        return frame

    def _populate_download_tab(self, parent):
        """Populates the main download control tab."""
        # URL Input
        url_frame = self._create_styled_frame(parent, "Video URL")
        url_input_frame = ttk.Frame(url_frame, padding=10)
        url_input_frame.pack(fill=X, expand=True)
        self.url_entry = ttk.Entry(
            url_input_frame,
            textvariable=self.url_var,
            font=('Consolas', 12)
        )
        self.url_entry.pack(side=LEFT, fill=X, expand=True, ipady=5)
        add_btn = ttk.Button(
            url_input_frame,
            text="Add",
            command=self.add_url_to_list,
            style='success-outline.TButton'
        )
        add_btn.pack(side=RIGHT, padx=(10, 0))

        # Settings
        settings_frame = self._create_styled_frame(parent, "Download Settings")
        settings_content = ttk.Frame(settings_frame, padding=10)
        settings_content.pack(fill=BOTH, expand=True)
        settings_content.grid_columnconfigure(0, weight=1)
        settings_content.grid_columnconfigure(1, weight=1)

        ttk.Label(settings_content, text="Quality Preset:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky=W, pady=(0, 5))
        quality_options = [
            "Ultra HD (4K+, 30fps+)", "Best Quality (1080p+, 30fps+)",
            "High Quality (720p+, 30fps+)", "Standard (480p+)", "Fast Download"
        ]
        quality_combo = ttk.Combobox(settings_content, textvariable=self.quality_var, values=quality_options, state="readonly")
        quality_combo.grid(row=1, column=0, columnspan=2, sticky=EW, pady=(0, 10))

        ttk.Label(settings_content, text="Output Format:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, sticky=W, pady=(0, 5))
        format_options = [
            "mp4 (Best Compatibility)", "mkv (Highest Quality)", "webm (Web Optimized)",
            "avi (Classic)", "mp3 (Audio Only)", "m4a (High Quality Audio)", "flac (Lossless Audio)"
        ]
        format_combo = ttk.Combobox(settings_content, textvariable=self.format_var, values=format_options, state="readonly", style='warning.TCombobox')
        format_combo.grid(row=3, column=0, columnspan=2, sticky=EW)

        # Output Path
        path_frame = self._create_styled_frame(parent, "Download Location")
        path_content = ttk.Frame(path_frame, padding=10)
        path_content.pack(fill=X, expand=True)
        path_entry = ttk.Entry(path_content, textvariable=self.output_path, font=('Consolas', 11))
        path_entry.pack(side=LEFT, fill=X, expand=True, ipady=2)
        browse_btn = ttk.Button(path_content, text="Browse", command=self.browse_folder, style='primary-outline.TButton')
        browse_btn.pack(side=RIGHT, padx=(10, 0))

        # Enhanced Action Buttons
        action_frame = ttk.Frame(parent, padding=(0, 15))
        action_frame.pack(fill=X, side=BOTTOM)
        action_frame.grid_columnconfigure((0, 1), weight=1)

        download_single_btn = ttk.Button(
            action_frame, text="Download Current", command=self.start_download, style='success.TButton'
        )
        download_single_btn.grid(row=0, column=0, sticky=EW, ipady=8, padx=(0, 5))
        self.download_single_btn = download_single_btn

        # Updated to use parallel download
        download_batch_btn = ttk.Button(
            action_frame, text="Parallel Download All", command=self.start_parallel_batch_download, style='primary.TButton'
        )
        download_batch_btn.grid(row=0, column=1, sticky=EW, ipady=8, padx=(5, 0))
        self.download_batch_btn = download_batch_btn

        info_btn = ttk.Button(
            action_frame, text="Get Video Info", command=self.get_video_info, style='info-outline.TButton'
        )
        info_btn.grid(row=1, column=0, columnspan=2, sticky=EW, pady=(10, 0))
        self.info_btn = info_btn

    def _populate_bulk_import_tab(self, parent):
        """Populates the bulk URL import tab."""
        ttk.Label(parent, text="Enter one URL per line:", font=('Segoe UI', 10, 'bold')).pack(anchor=W, pady=(0, 5))
        self.url_text = scrolledtext.ScrolledText(
            parent, height=10, font=('Consolas', 10), relief=FLAT,
            bg=self.style.colors.inputbg, fg=self.style.colors.fg,
            insertbackground=self.style.colors.primary
        )
        self.url_text.pack(fill=BOTH, expand=True, pady=(0, 15))

        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=X)
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ttk.Button(button_frame, text="Import from Text", command=self.import_from_text, style='primary-outline.TButton').grid(row=0, column=0, sticky=EW, padx=(0, 5))
        ttk.Button(button_frame, text="Import from File", command=self.import_from_file, style='success-outline.TButton').grid(row=0, column=1, sticky=EW, padx=5)
        ttk.Button(button_frame, text="Export Queue", command=self.export_urls, style='warning-outline.TButton').grid(row=0, column=2, sticky=EW, padx=(5, 0))
        ttk.Button(button_frame, text="Clear All", command=self.clear_url_list, style='danger-outline.TButton').grid(row=1, column=0, columnspan=3, sticky=EW, pady=(10, 0))

    def _populate_advanced_tab(self, parent):
        """Populates the advanced settings tab."""
        adv_frame = self._create_styled_frame(parent, "Fine-Tuning")
        adv_content = ttk.Frame(adv_frame, padding=10)
        adv_content.pack(fill=BOTH, expand=True)
        adv_content.grid_columnconfigure(1, weight=1)

        # Helper for creating rows
        def create_adv_row(label_text, row, var, values, default, style='primary.TCombobox'):
            ttk.Label(adv_content, text=label_text, font=('Segoe UI', 10)).grid(row=row, column=0, sticky=W, padx=(0, 15), pady=5)
            combo = ttk.Combobox(adv_content, textvariable=var, values=values, state="readonly", style=style)
            combo.grid(row=row, column=1, sticky=EW, pady=5)
            combo.set(default)

        create_adv_row("Min Frame Rate:", 0, self.fps_var, ["Any", "24+", "30+", "60+"], "30+")
        create_adv_row("Audio Quality:", 1, self.audio_quality_var, ["Best Available", "320kbps", "192kbps", "128kbps"], "Best Available")
        create_adv_row("YouTube Fix:", 2, self.youtube_fix_var, ["Smart Fix (Auto)", "Browser Cookies", "Bypass Mode", "OAuth2"], "Smart Fix (Auto)", style='danger.TCombobox')

        # Checkbuttons
        check_frame = ttk.Frame(adv_content)
        check_frame.grid(row=3, column=0, columnspan=2, sticky=W, pady=(15, 0))
        ttk.Checkbutton(check_frame, text="Download subtitles", variable=self.subtitle_var, style='primary.Roundtoggle.Toolbutton').pack(side=LEFT, padx=(0, 15))
        ttk.Checkbutton(check_frame, text="Download thumbnail", variable=self.thumbnail_var, style='primary.Roundtoggle.Toolbutton').pack(side=LEFT)

    def _create_progress_section(self, parent):
        """Creates the progress bar and status label section."""
        progress_frame = ttk.Labelframe(parent, text=" Progress ", style='primary.TLabelframe')
        progress_frame.grid(row=0, column=0, sticky="new", pady=(0, 15))
        progress_frame.grid_columnconfigure(0, weight=1)

        content = ttk.Frame(progress_frame, padding=10)
        content.grid(row=0, column=0, sticky=EW)
        content.grid_columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(
            content, variable=self.progress_var, maximum=100, style='success-striped.TProgressbar'
        )
        self.progress_bar.grid(row=0, column=0, sticky=EW, pady=(5, 10))

        self.status_label = ttk.Label(content, textvariable=self.status_var, font=('Segoe UI', 11))
        self.status_label.grid(row=1, column=0, sticky=EW)

    def _create_queue_section(self, parent):
        """Creates the download queue Treeview section."""
        queue_frame = ttk.Labelframe(parent, text=" Download Queue ", style='primary.TLabelframe')
        queue_frame.grid(row=2, column=0, sticky="nsew")
        queue_frame.grid_rowconfigure(0, weight=1)
        queue_frame.grid_columnconfigure(0, weight=1)

        tree_frame = ttk.Frame(queue_frame, padding=10)
        tree_frame.grid(row=0, column=0, sticky='nsew')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        columns = ('URL', 'Title', 'Quality', 'Size', 'Platform', 'Status')
        self.url_tree = ttk.Treeview(
            tree_frame, columns=columns, show='headings', style='primary.Treeview'
        )

        # Define column headings and widths
        self.url_tree.heading('URL', text='URL')
        self.url_tree.column('URL', width=150, minwidth=100)
        self.url_tree.heading('Title', text='Title')
        self.url_tree.column('Title', width=250, minwidth=150)
        self.url_tree.heading('Quality', text='Quality')
        self.url_tree.column('Quality', width=100, minwidth=80, anchor=CENTER)
        self.url_tree.heading('Size', text='Size')
        self.url_tree.column('Size', width=80, minwidth=60, anchor=CENTER)
        self.url_tree.heading('Platform', text='Platform')
        self.url_tree.column('Platform', width=100, minwidth=80, anchor=CENTER)
        self.url_tree.heading('Status', text='Status')
        self.url_tree.column('Status', width=120, minwidth=100)

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.url_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.url_tree.xview)
        self.url_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.url_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        self._setup_context_menu()

    def _setup_context_menu(self):
        """Sets up the right-click context menu for the queue."""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Remove", command=self.remove_selected_url)
        self.context_menu.add_command(label="Get Info", command=self.get_selected_info)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Move Up", command=self.move_url_up)
        self.context_menu.add_command(label="Move Down", command=self.move_url_down)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Cancel Task", command=self.cancel_selected_task)
        
        self.url_tree.bind("<Button-3>", self.show_context_menu)
        
    def show_context_menu(self, event):
        """Displays the context menu at the cursor's position."""
        item = self.url_tree.identify_row(event.y)
        if item:
            self.url_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def cancel_selected_task(self):
        """Cancel the selected download task."""
        selection = self.url_tree.selection()
        if selection:
            index = self.url_tree.index(selection[0])
            if index < len(self.url_list):
                item = self.url_list[index]
                if 'task_id' in item and item['task_id']:
                    if self.task_manager.cancel_task(item['task_id']):
                        item['status'] = 'Cancelled'
                        self.update_url_tree()
                        self.status_var.set("Task cancelled")
                    else:
                        messagebox.showinfo("Info", "Task could not be cancelled (may have already completed)")

    # --- Processing Presets Window ---
    def create_processing_presets_window(self):
        """Create a window for managing processing presets."""
        presets_window = bootstrap.Toplevel(title="Processing Presets Manager")
        presets_window.geometry("700x600")
        
        # Enhanced preset definitions
        self.processing_presets = {
            "Light Sharpening": {"method": "sharpen", "intensity": 0.7},
            "Strong Deblur": {"method": "deblur", "intensity": 2.0},
            "Detail Enhancement": {"method": "enhance", "intensity": 1.5},
            "Video Stabilization": {"method": "stabilize", "intensity": 1.2},
            "Ultra Sharp": {"method": "sharpen", "intensity": 2.5},
            "Gentle Enhancement": {"method": "enhance", "intensity": 0.8},
            "Noise Reduction": {"method": "deblur", "intensity": 1.2},
            "Cinema Mode": {"method": "enhance", "intensity": 1.8},
            "Sports Stabilization": {"method": "stabilize", "intensity": 2.0},
            "Professional Grade": {"method": "sharpen", "intensity": 1.8}
        }
        
        main_frame = ttk.Frame(presets_window, padding=15)
        main_frame.pack(fill=BOTH, expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(main_frame, text="Processing Presets Library:", font=('Segoe UI', 14, 'bold')).grid(row=0, column=0, sticky=W, pady=(0, 15))
        
        # Enhanced presets display with details
        presets_frame = ttk.Frame(main_frame)
        presets_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        presets_frame.grid_rowconfigure(0, weight=1)
        presets_frame.grid_columnconfigure(0, weight=1)
        
        # Presets treeview
        preset_columns = ('Name', 'Method', 'Intensity', 'Description')
        presets_tree = ttk.Treeview(
            presets_frame, columns=preset_columns, show='headings',
            style='success.Treeview'
        )
        
        presets_tree.heading('Name', text='Preset Name')
        presets_tree.column('Name', width=150, minwidth=120)
        presets_tree.heading('Method', text='Method')
        presets_tree.column('Method', width=100, minwidth=80)
        presets_tree.heading('Intensity', text='Intensity')
        presets_tree.column('Intensity', width=80, minwidth=60, anchor=CENTER)
        # Presets treeview
        preset_columns = ('Name', 'Method', 'Intensity', 'Description')
        presets_tree = ttk.Treeview(
            presets_frame, columns=preset_columns, show='headings',
            style='success.Treeview'
        )
        
        presets_tree.heading('Name', text='Preset Name')
        presets_tree.column('Name', width=150, minwidth=120)
        presets_tree.heading('Method', text='Method')
        presets_tree.column('Method', width=100, minwidth=80)
        presets_tree.heading('Intensity', text='Intensity')
        presets_tree.column('Intensity', width=80, minwidth=60, anchor=CENTER)
        presets_tree.heading('Description', text='Best For')
        presets_tree.column('Description', width=200, minwidth=150)
        
        presets_tree.grid(row=0, column=0, sticky='nsew')
        
        preset_scrollbar = ttk.Scrollbar(presets_frame, orient=VERTICAL, command=presets_tree.yview)
        presets_tree.configure(yscrollcommand=preset_scrollbar.set)
        preset_scrollbar.grid(row=0, column=1, sticky='ns')
        
        # Populate presets with descriptions
        preset_descriptions = {
            "Light Sharpening": "Subtle sharpening for slightly soft videos",
            "Strong Deblur": "Heavy blur removal for very blurry footage",
            "Detail Enhancement": "Enhance fine details and textures",
            "Video Stabilization": "Reduce camera shake and jitter",
            "Ultra Sharp": "Maximum sharpening (use carefully)",
            "Gentle Enhancement": "Light enhancement for good quality videos",
            "Noise Reduction": "Reduce grain and digital noise",
            "Cinema Mode": "Professional cinematic enhancement",
            "Sports Stabilization": "Strong stabilization for action footage",
            "Professional Grade": "High-end processing for professional use"
        }
        
        for preset_name, settings in self.processing_presets.items():
            description = preset_descriptions.get(preset_name, "Custom processing")
            presets_tree.insert('', 'end', values=(
                preset_name, settings['method'].title(), 
                f"{settings['intensity']:.1f}", description
            ))
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky=EW)
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        def apply_selected_preset():
            selection = presets_tree.selection()
            if selection:
                item = presets_tree.item(selection[0])
                preset_name = item['values'][0]
                settings = self.processing_presets[preset_name]
                
                # Apply to current active processing tab
                current_tab = self.processing_notebook.select()
                if current_tab:
                    tab_index = self.processing_notebook.index(current_tab)
                    # Find the corresponding tab data
                    for tab_data in self.processing_tab_manager.tabs.values():
                        if str(tab_data['frame']) == current_tab:
                            tab_data['method_var'].set(settings['method'])
                            tab_data['intensity_var'].set(settings['intensity'])
                            break
                
                messagebox.showinfo("Success", f"Applied preset: {preset_name}")
                presets_window.destroy()
            else:
                messagebox.showwarning("Warning", "Please select a preset first.")
        
        ttk.Button(
            button_frame, text="Apply to Active Tab", 
            command=apply_selected_preset, style='success.TButton'
        ).grid(row=0, column=0, sticky=EW, padx=(0, 5))
        
        ttk.Button(
            button_frame, text="Preview Settings", 
            command=lambda: self.preview_preset(presets_tree), style='info.TButton'
        ).grid(row=0, column=1, sticky=EW, padx=5)
        
        ttk.Button(
            button_frame, text="Close", 
            command=presets_window.destroy, style='secondary.TButton'
        ).grid(row=0, column=2, sticky=EW, padx=(5, 0))

    def preview_preset(self, presets_tree):
        """Preview selected preset settings."""
        selection = presets_tree.selection()
        if selection:
            item = presets_tree.item(selection[0])
            preset_name = item['values'][0]
            settings = self.processing_presets[preset_name]
            
            preview_msg = f"""
Preset: {preset_name}

Method: {settings['method'].title()}
Intensity: {settings['intensity']:.1f}

This preset is designed for: {item['values'][3]}

Would you like to apply this preset to the currently active processing tab?
            """
            
            if messagebox.askyesno("Preset Preview", preview_msg.strip()):
                # Apply preset logic here
                current_tab = self.processing_notebook.select()
                if current_tab:
                    for tab_data in self.processing_tab_manager.tabs.values():
                        if str(tab_data['frame']) == current_tab:
                            tab_data['method_var'].set(settings['method'])
                            tab_data['intensity_var'].set(settings['intensity'])
                            break
        else:
            messagebox.showwarning("Warning", "Please select a preset first.")

    # --- Original Download Methods (Enhanced) ---
    def get_quality_format_string(self):
        """Get the yt-dlp format string based on current settings"""
        quality_text = self.quality_var.get()
        quality_map = {
            "Ultra HD (4K+, 30fps+)": "ultra_hd",
            "Best Quality (1080p+, 30fps+)": "best_quality",
            "High Quality (720p+, 30fps+)": "high_quality",
            "Standard (480p+)": "standard",
            "Fast Download": "fast_download"
        }
        quality_preset = quality_map.get(quality_text, "best_quality")
        
        format_text = self.format_var.get()
        ext = "mp4"
        if "mkv" in format_text: ext = "mkv"
        elif "webm" in format_text: ext = "webm"
        elif "avi" in format_text: ext = "avi"
        
        fps_pref = self.fps_var.get()
        fps_filter = ""
        if fps_pref != "Any":
            fps_num = fps_pref.replace("+", "")
            fps_filter = f"[fps>={fps_num}]"
        
        if quality_preset == "ultra_hd":
            return f"bestvideo[height>=2160]{fps_filter}[ext={ext}]+bestaudio/best[height>=2160]{fps_filter}/best[height>=1440]{fps_filter}[ext={ext}]/best[height>=1440]{fps_filter}/best[ext={ext}]/best"
        elif quality_preset == "best_quality":
            return f"bestvideo[height>=1080]{fps_filter}[ext={ext}]+bestaudio/best[height>=1080]{fps_filter}/best[height>=720]{fps_filter}[ext={ext}]/best[height>=720]{fps_filter}/best[ext={ext}]/best"
        elif quality_preset == "high_quality":
            return f"bestvideo[height>=720]{fps_filter}[ext={ext}]+bestaudio/best[height>=720]{fps_filter}/best[height>=480]{fps_filter}[ext={ext}]/best[height>=480]{fps_filter}/best[ext={ext}]/best"
        else:
            return f"best[ext={ext}]/best"
    
    def get_enhanced_youtube_options(self):
        """Get enhanced YouTube options for better quality and reliability"""
        fix_method = self.youtube_fix_var.get()
        
        base_opts = {
            'extract_flat': False,
            'writesubtitles': self.subtitle_var.get(),
            'writeautomaticsub': self.subtitle_var.get(),
            'writethumbnail': self.thumbnail_var.get(),
            'writeinfojson': False,
            'ignoreerrors': False,
            'no_warnings': False,
            'merge_output_format': 'mp4' if 'mp4' in self.format_var.get() else 'mkv',
        }
        
        if "Smart Fix" in fix_method:
            base_opts.update({
                'extractor_args': {'youtube': {'skip': ['dash'], 'player_client': ['android', 'web', 'ios']}},
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            })
        elif "Browser Cookies" in fix_method:
            base_opts['cookiesfrombrowser'] = ('chrome', None, None, None)
        elif "Bypass Mode" in fix_method:
            base_opts.update({
                'extractor_args': {'youtube': {'skip': ['dash', 'hls'], 'player_client': ['android']}},
                'user_agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip',
            })
        elif "OAuth2" in fix_method:
            base_opts['username'] = 'oauth2'
        
        return base_opts

    def detect_platform(self, url):
        """Detect platform from URL"""
        domain_map = {
            'youtube.com': 'YouTube', 'youtu.be': 'YouTube', 'tiktok.com': 'TikTok',
            'instagram.com': 'Instagram', 'twitter.com': 'Twitter/X', 'x.com': 'Twitter/X',
            'facebook.com': 'Facebook', 'twitch.tv': 'Twitch', 'vimeo.com': 'Vimeo'
        }
        for domain, platform in domain_map.items():
            if domain in url.lower():
                return platform
        return 'Other'
    
    def add_url_to_list(self):
        """Add URL to download queue"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a video URL")
            return
            
        if not self.is_valid_url(url):
            messagebox.showerror("Error", "Invalid URL format")
            return
            
        if url in [item['url'] for item in self.url_list]:
            messagebox.showinfo("Info", "URL already in queue")
            return
        
        platform = self.detect_platform(url)
        item = {
            'url': url, 'title': 'Loading...', 'quality': 'Checking...', 'size': '...',
            'platform': platform, 'status': 'Queued'
        }
        self.url_list.append(item)
        self.update_url_tree()
        self.url_var.set("")
        self.status_var.set(f"Added {platform} video to queue")
        
        threading.Thread(target=self.get_url_details, args=(len(self.url_list)-1,), daemon=True).start()
    
    def get_url_details(self, index):
        """Get detailed information for a URL in a background thread."""
        if index >= len(self.url_list): return
            
        item = self.url_list[index]
        try:
            # Quick info extraction using 'extract_flat' to speed up link metadata gathering
            quick_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True, 'socket_timeout': 10}
            if item['platform'] == 'YouTube':
                quick_opts.update(self.get_enhanced_youtube_options())

            with yt_dlp.YoutubeDL(quick_opts) as ydl:
                info = ydl.extract_info(item['url'], download=False)

            # Try to obtain basic metadata from quick extract
            title = info.get('title') or (info.get('entries') and info['entries'][0].get('title'))
            item['title'] = (title[:60] if title else 'Unknown Title')

            height = info.get('height') or (info.get('entries') and info['entries'][0].get('height'))
            filesize = (info.get('filesize') or info.get('filesize_approx') or
                        (info.get('entries') and (info['entries'][0].get('filesize') or info['entries'][0].get('filesize_approx'))))

            if height: item['quality'] = f"{height}p"
            if filesize:
                if filesize > 1024*1024*1024: item['size'] = f"{filesize / (1024**3):.1f}GB"
                else: item['size'] = f"{filesize / (1024**2):.1f}MB"

            item['status'] = 'Ready'

        except Exception:
            # Fallback to a more thorough extraction (slower) if quick pass failed
            try:
                ydl_opts = {'quiet': True, 'no_warnings': True, 'socket_timeout': 30}
                if item['platform'] == 'YouTube':
                    ydl_opts.update(self.get_enhanced_youtube_options())
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(item['url'], download=False)

                item['title'] = info.get('title', 'Unknown Title')[:60]
                height = info.get('height')
                filesize = info.get('filesize') or info.get('filesize_approx')
                if height: item['quality'] = f"{height}p"
                if filesize:
                    if filesize > 1024*1024*1024: item['size'] = f"{filesize / (1024**3):.1f}GB"
                    else: item['size'] = f"{filesize / (1024**2):.1f}MB"
                item['status'] = 'Ready'
            except Exception:
                item['title'] = 'Error loading info'
                item['status'] = 'Error'
        
        self.root.after(0, self.update_url_tree)
    
    def update_url_tree(self):
        """Update the URL tree view with the current list."""
        self.url_tree.delete(*self.url_tree.get_children())
        
        for i, item in enumerate(self.url_list):
            display_url = item['url'][:25] + '...' if len(item['url']) > 25 else item['url']
            
            tag = 'odd' if i % 2 == 0 else 'even'
            if item['status'] in ['Downloading...', 'Processing']:
                tag = 'active'
            elif item['status'] in ['Downloaded', 'Completed']:
                tag = 'completed'
            elif item['status'] in ['Failed', 'Error', 'Cancelled']:
                tag = 'error'
                
            self.url_tree.insert('', 'end', values=(
                display_url, item['title'], item['quality'], item['size'],
                item['platform'], item['status']
            ), tags=(tag,))
        
        # Configure tag colors
        self.url_tree.tag_configure('odd', background=self.style.colors.bg)
        self.url_tree.tag_configure('even', background=self.style.colors.light)
        self.url_tree.tag_configure('active', background='#004080', foreground='white')
        self.url_tree.tag_configure('completed', background='#006600', foreground='white')
        self.url_tree.tag_configure('error', background='#800000', foreground='white')

    def progress_hook(self, d):
        """Enhanced progress hook for yt-dlp with task tracking."""
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                percent = (d['downloaded_bytes'] / total_bytes) * 100
                self.progress_var.set(percent)
                
                speed = d.get('_speed_str', '').strip()
                eta = d.get('_eta_str', '').strip()
                
                status_text = f"Downloading... {percent:.1f}%"
                if speed: status_text += f" at {speed}"
                if eta: status_text += f" (ETA: {eta})"
                
                self.status_var.set(status_text)
                
        elif d['status'] == 'finished':
            self.progress_var.set(100)
            filename = os.path.basename(d['filename'])
            self.status_var.set(f"Download Complete: {filename}")

    def download_video(self, url=None, update_status=True):
        """Core video download logic."""
        # License guard (extra safety for direct calls)
        if not self.require_license(show_message=False):
            if update_status:
                try:
                    messagebox.showwarning("License Required", "Downloads are disabled until you activate a license.")
                except:
                    pass
            return False

        if url is None: url = self.url_var.get().strip()
        if not url:
            if update_status: messagebox.showerror("Error", "No URL provided.")
            return False
        
        try:
            format_string = self.get_quality_format_string()
            
            ydl_opts = {
                'format': format_string,
                'outtmpl': os.path.join(self.output_path.get(), '%(title)s [%(id)s].%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'ignoreerrors': False,
                'no_warnings': False,
                'writesubtitles': self.subtitle_var.get(),
                'writeautomaticsub': self.subtitle_var.get(),
                'writethumbnail': self.thumbnail_var.get(),
            }
            
            if self.detect_platform(url) == 'YouTube':
                ydl_opts.update(self.get_enhanced_youtube_options())
            
            format_text = self.format_var.get()
            if any(audio in format_text for audio in ['mp3', 'm4a', 'flac']):
                audio_format = 'mp3' if 'mp3' in format_text else 'flac' if 'flac' in format_text else 'm4a'
                quality = '320' if self.audio_quality_var.get() == "320kbps" else '192'
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': audio_format, 'preferredquality': quality}]
                })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
            
        except Exception as e:
            error_msg = str(e)
            if update_status:
                self.status_var.set(f"Error: {error_msg[:50]}...")
                self.progress_var.set(0)
                messagebox.showerror("Download Error", f"An error occurred:\n\n{error_msg}")
            return False

    def start_download(self):
        """Starts a single video download in a new thread."""
        # License guard: block single download until licensed
        if not self.require_license(show_message=True):
            return

        self.progress_var.set(0)
        self.status_var.set("Initializing download...")
        threading.Thread(target=self.download_video, daemon=True).start()

    # --- Utility Methods ---
    def import_from_text(self):
        """Import URLs from the text area."""
        urls = [line.strip() for line in self.url_text.get('1.0', tk.END).split('\n') if line.strip()]
        imported_count = 0
        for url in urls:
            if self.is_valid_url(url) and url not in [item['url'] for item in self.url_list]:
                platform = self.detect_platform(url)
                item = {'url': url, 'title': 'Loading...', 'quality': '...', 'size': '...', 'platform': platform, 'status': 'Queued'}
                self.url_list.append(item)
                threading.Thread(target=self.get_url_details, args=(len(self.url_list)-1,), daemon=True).start()
                imported_count += 1
        
        if imported_count > 0:
            self.update_url_tree()
            self.status_var.set(f"Imported {imported_count} URLs")
            messagebox.showinfo("Success", f"Added {imported_count} new URLs to the queue.")
        else:
            messagebox.showwarning("Warning", "No new, valid URLs found in the text.")

    def import_from_file(self):
        """Import URLs from a text file."""
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not filepath: return
        with open(filepath, 'r', encoding='utf-8') as f:
            self.url_text.delete('1.0', tk.END)
            self.url_text.insert('1.0', f.read())
        self.import_from_text()

    def export_urls(self):
        """Export the current queue to a text file."""
        if not self.url_list:
            messagebox.showwarning("Warning", "Queue is empty. Nothing to export.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not filepath: return
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in self.url_list:
                f.write(f"{item['url']}\n")
        messagebox.showinfo("Success", f"Exported {len(self.url_list)} URLs.")

    def is_valid_url(self, url):
        """Basic URL validation."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def clear_url_list(self):
        """Clears the entire download queue."""
        if self.url_list and messagebox.askyesno("Confirm", "Clear all URLs from the queue?"):
            self.url_list.clear()
            self.update_url_tree()
            self.status_var.set("Queue cleared")

    def remove_selected_url(self):
        """Removes the selected URL from the queue."""
        selection = self.url_tree.selection()
        if selection:
            index = self.url_tree.index(selection[0])
            del self.url_list[index]
            self.update_url_tree()
            self.status_var.set("Removed item from queue")

    def get_selected_info(self):
        """Gets info for the selected URL."""
        selection = self.url_tree.selection()
        if selection:
            index = self.url_tree.index(selection[0])
            self.url_var.set(self.url_list[index]['url'])
            self.get_video_info()

    def move_url_up(self):
        """Moves the selected URL up in the queue."""
        selection = self.url_tree.selection()
        if selection:
            index = self.url_tree.index(selection[0])
            if index > 0:
                self.url_list[index], self.url_list[index-1] = self.url_list[index-1], self.url_list[index]
                self.update_url_tree()
                self.url_tree.selection_set(self.url_tree.get_children()[index-1])

    def move_url_down(self):
        """Moves the selected URL down in the queue."""
        selection = self.url_tree.selection()
        if selection:
            index = self.url_tree.index(selection[0])
            if index < len(self.url_list) - 1:
                self.url_list[index], self.url_list[index+1] = self.url_list[index+1], self.url_list[index]
                self.update_url_tree()
                self.url_tree.selection_set(self.url_tree.get_children()[index+1])

    def browse_folder(self):
        """Opens a dialog to select the download folder."""
        folder = filedialog.askdirectory(initialdir=self.output_path.get())
        if folder:
            self.output_path.set(folder)
            self.status_var.set(f"Download location set")
    
    def get_video_info(self):
        """Fetches and displays detailed video information."""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a video URL first.")
            return
        
        self.status_var.set("Fetching video information...")
        threading.Thread(target=self._get_info_worker, args=(url,), daemon=True).start()

    def _get_info_worker(self, url):
        """Worker thread for fetching video info."""
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            if self.detect_platform(url) == 'YouTube':
                ydl_opts.update(self.get_enhanced_youtube_options())
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            self.root.after(0, lambda: self._show_video_info_window(info))
            self.root.after(0, lambda: self.status_var.set("Video information loaded"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to get video info:\n\n{e}"))
            self.root.after(0, lambda: self.status_var.set("Failed to get video info"))

    def _show_video_info_window(self, info):
        """Displays the video information in a new window."""
        info_window = bootstrap.Toplevel(title="Video Information")
        info_window.geometry("800x600")
        
        text_widget = scrolledtext.ScrolledText(
            info_window, font=('Consolas', 10), wrap='word', relief=FLAT
        )
        text_widget.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        info_text = self._format_video_info(info)
        text_widget.insert('1.0', info_text)
        text_widget.config(state='disabled')

    def _format_video_info(self, info):
        """Formats the raw video info into a readable string."""
        title = info.get('title', 'N/A')
        uploader = info.get('uploader', 'N/A')
        duration = time.strftime('%H:%M:%S', time.gmtime(info.get('duration', 0)))
        
        return f"""
--- BASIC INFO ---
Title: {title}
Uploader: {uploader}
Duration: {duration}
Views: {info.get('view_count', 0):,}
Likes: {info.get('like_count', 0):,}
Platform: {info.get('extractor_key', 'N/A')}

--- TECHNICAL INFO ---
Resolution: {info.get('width', 'N/A')}x{info.get('height', 'N/A')}
FPS: {info.get('fps', 'N/A')}
Format: {info.get('ext', 'N/A')}
Filesize: {self._format_filesize(info.get('filesize') or info.get('filesize_approx'))}

--- DESCRIPTION ---
{info.get('description', 'No description available.')[:800]}...
"""

    def _format_filesize(self, size_bytes):
        """Format file size in human readable format."""
        if not size_bytes:
            return "N/A"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def clear_all_tasks(self):
        """Clear all active tasks and reset task manager"""
        if hasattr(self, 'task_manager'):
            # Cancel all active tasks
            for task_id in list(self.task_manager.active_tasks.keys()):
                self.task_manager.cancel_task(task_id)
            
            # Reset progress and status
            self.progress_var.set(0)
            self.status_var.set("All tasks cleared")
            
            # Update displays
            self.update_header_status()
            self.update_task_monitor()
            
            messagebox.showinfo("Tasks Cleared", "All active tasks have been cancelled and cleared.")
    
    def show_license_manager(self):
        """Show license management window"""
        license_window = bootstrap.Toplevel(title="License Manager")
        license_window.geometry("600x400")
        
        main_frame = ttk.Frame(license_window, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        ttk.Label(main_frame, text="License Manager", font=('Segoe UI', 16, 'bold')).pack(pady=(0, 20))
        
        # Current license info
        info_frame = ttk.Labelframe(main_frame, text=" Current License ", padding=15)
        info_frame.pack(fill='x', pady=(0, 15))
        
        is_valid, info = self.license_manager.get_license_info()
        if is_valid:
            issue_date = datetime.fromisoformat(info['issue_date'])
            expiry_date = datetime.fromisoformat(info['expiry_date'])
            days_remaining = (expiry_date - datetime.now()).days
            
            info_text = f"""Licensed User: {info['user_id'][:20]}...
Issue Date: {issue_date.strftime('%Y-%m-%d')}
Expiry Date: {expiry_date.strftime('%Y-%m-%d')}
Days Remaining: {days_remaining}
Status: {'Active' if days_remaining > 0 else 'Expired'}"""
                        
            ttk.Label(info_frame, text=info_text, font=('Consolas', 10)).pack(anchor='w')
        else:
            ttk.Label(info_frame, text="No valid license found", foreground='red').pack()
        
        # Actions
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill='x', pady=(15, 0))
        actions_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        ttk.Button(
            actions_frame,
            text="Activate New License",
            command=lambda: self.activate_new_license(license_window),
            style='success.TButton'
        ).grid(row=0, column=0, sticky='ew', padx=(0, 5))
        
        ttk.Button(
            actions_frame,
            text="Remove License",
            command=lambda: self.remove_current_license(license_window),
            style='danger.TButton'
        ).grid(row=0, column=1, sticky='ew', padx=5)
        
        ttk.Button(
            actions_frame,
            text="Close",
            command=license_window.destroy,
            style='secondary.TButton'
        ).grid(row=0, column=2, sticky='ew', padx=(5, 0))

    def show_locked_overlay(self, license_manager):
        """Show a modal overlay that blocks interaction until license activation."""
        if self._locked_overlay and tk.Toplevel.winfo_exists(self._locked_overlay):
            return
        self.locked = True
        overlay = tk.Toplevel(self.root)
        overlay.transient(self.root)
        overlay.geometry(f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_x()}+{self.root.winfo_y()}")
        overlay.overrideredirect(True)
        overlay.attributes('-topmost', True)
        # Do not call grab_set() here so the main window and keyboard shortcuts still work.
        # Disable main action controls while overlay is visible.
        try:
            self.update_controls_locked(True)
        except Exception:
            pass
        frame = ttk.Frame(overlay, padding=30, style='secondary.TFrame')
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text="License Required", font=('Segoe UI', 18, 'bold'), style='secondary.Inverse.TLabel').pack(pady=(0,10))
        ttk.Label(frame, text="This copy is locked. Activate your license to enable full functionality.", font=('Segoe UI', 11)).pack(pady=(0,15))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        def on_activate():
            dlg = LicenseDialog(self.root, license_manager)
            if dlg.show_activation_dialog():
                # license activated
                self.locked = False
                try:
                    # Re-enable controls before removing overlay
                    self.update_controls_locked(False)
                except Exception:
                    pass
                try:
                    overlay.destroy()
                except:
                    pass

        def on_contact_support():
            support_id = f"PRODL-{uuid.uuid4().hex[:8].upper()}"
            # Copy support id to clipboard
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(support_id)
                self.root.update()
            except:
                pass
            # Open user's mail client with prefilled mailto
            mailto = f"mailto:support@example.com?subject=License%20Request&body=Please%20help%20with%20license.%20Support%20ID:%20{support_id}"
            webbrowser.open(mailto)
            messagebox.showinfo("Contact Support", f"Support ID {support_id} copied to clipboard. An email composer was opened.")

        ttk.Button(btn_frame, text="Activate License", command=on_activate, style='success.TButton').pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="Contact Support", command=on_contact_support, style='info-outline.TButton').pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="Exit", command=self.root.quit, style='danger.TButton').pack(side=LEFT, padx=5)

        self._locked_overlay = overlay

    
    def activate_new_license(self, parent_window):
        """Activate a new license"""
        parent_window.destroy()
        dialog = LicenseDialog(self.root, self.license_manager)
        dialog.show_activation_dialog()
    
    def remove_current_license(self, parent_window):
        """Remove current license"""
        if messagebox.askyesno("Confirm", "Remove current license?"):
            if self.license_manager.remove_license():
                messagebox.showinfo("Success", "License removed successfully.")
                parent_window.destroy()
            else:
                messagebox.showerror("Error", "Could not remove license.")


# --- Main Application Entry Point ---
def main():
    """Main function to initialize and run the enhanced application."""
    print("Pro Download V6 starting...")
    root = bootstrap.Window(themename="superhero")
    license_manager = LicenseManager()

    # Create app immediately so the UI appears. If no valid license, lock the UI.
    app = VideoDownloader(root)
    app.license_manager = license_manager

    is_valid, _ = license_manager.get_license_info()
    if not is_valid:
        # Show main window and lock overlay to require activation/contact support
        root.deiconify()
        app.show_locked_overlay(license_manager)

    # ---- Global shortcuts to help activate license when UI is locked ----
    def _open_activation_dialog(event=None):
        try:
            dlg = LicenseDialog(root, license_manager)
            dlg.show_activation_dialog()
            # If activation succeeded, close overlay
            if not app.locked and getattr(app, '_locked_overlay', None):
                try:
                    app._locked_overlay.destroy()
                except:
                    pass
        except Exception as e:
            try:
                messagebox.showerror("Error", f"Could not open activation dialog: {e}")
            except:
                print("Could not open activation dialog:", e)

    def _paste_and_activate_from_clipboard(event=None):
        try:
            clip = root.clipboard_get().strip()
        except Exception:
            clip = None

        if not clip:
            try:
                messagebox.showinfo("No License", "Clipboard is empty. Copy the license key and try again.")
            except:
                print("Clipboard empty")
            return

        is_valid, info = license_manager.validate_license_key(clip)
        if is_valid:
            saved = license_manager.save_license(clip)
            if saved:
                try:
                    messagebox.showinfo("Activated", "License activated from clipboard. The tool is now unlocked.")
                except:
                    print("License activated")
                app.locked = False
                try:
                    if getattr(app, '_locked_overlay', None):
                        app._locked_overlay.destroy()
                except:
                    pass
            else:
                try:
                    messagebox.showerror("Error", "License validated but could not be saved to file.")
                except:
                    print("Could not save license file")
        else:
            try:
                messagebox.showerror("Invalid License", f"License invalid: {info}")
            except:
                print("License invalid:", info)

    # Bind global keys (works even when overlay has grab) so users can open activation or paste license
    try:
        root.bind_all('<Control-Shift-L>', _open_activation_dialog)
        root.bind_all('<Control-Shift-V>', _paste_and_activate_from_clipboard)
    except Exception:
        pass

    # Enhanced menu bar
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="New Processing Tab", command=lambda: app.processing_tab_manager.create_new_tab() if app.processing_tab_manager else None)
    file_menu.add_command(label="Enhanced Batch Processor", command=app.create_enhanced_batch_window)
    file_menu.add_command(label="Processing Presets", command=app.create_processing_presets_window)
    file_menu.add_separator()
    file_menu.add_command(label="Export Queue", command=app.export_urls)
    file_menu.add_command(label="Import URLs", command=app.import_from_file)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit)
    
    # Tools menu
    tools_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Tools", menu=tools_menu)
    tools_menu.add_command(label="Task Manager", command=lambda: messagebox.showinfo("Task Manager", "Task manager is integrated in the main interface"))
    tools_menu.add_command(label="Performance Monitor", command=lambda: app.show_performance_stats())
    tools_menu.add_command(label="License Manager", command=app.show_license_manager)
    tools_menu.add_separator()
    tools_menu.add_command(label="Clear All Tasks", command=app.clear_all_tasks)
    
    # Settings menu
    settings_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Settings", menu=settings_menu)
    settings_menu.add_command(label="Parallel Processing", command=lambda: app.show_parallel_settings())
    settings_menu.add_command(label="Default Paths", command=lambda: app.configure_default_paths())
    
    # Help menu
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="User Guide", command=lambda: app.show_user_guide())
    help_menu.add_command(label="Performance Tips", command=lambda: app.show_performance_tips())
    help_menu.add_separator()
    help_menu.add_command(label="About", command=lambda: messagebox.showinfo(
        "About Pro Video Downloader & Processor Suite v4.0", 
        "Pro Video Downloader & Processor Suite v4.0\n"
        "Parallel Processing Edition\n\n"
        "NEW FEATURES:\n"
        "• Concurrent downloads (2-5 simultaneous)\n"
        "• Parallel video processing (2-4 simultaneous)\n"
        "• Multiple processing tabs\n"
        "• Enhanced batch processing\n"
        "• Real-time task monitoring\n"
        "• Advanced preset system\n\n"
        "CAPABILITIES:\n"
        "• Download from 1000+ platforms\n"
        "• Advanced video enhancement\n"
        "• Professional quality settings\n"
        "• Optimized for performance\n\n"
        "Powered by yt-dlp, OpenCV, and concurrent.futures"
    ))
    
    # Add methods for menu items
    def show_performance_stats():
        """Show system performance statistics."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            stats_msg = f"""
SYSTEM PERFORMANCE STATS

CPU Usage: {cpu_percent:.1f}%
Memory Usage: {memory.percent:.1f}% ({memory.used // 1024**2} MB / {memory.total // 1024**2} MB)

ACTIVE TASKS:
Downloads: {len([t for t in app.task_manager.active_tasks.values() if t['type'] == 'download' and t['status'] == 'Running'])}
Processing: {len([t for t in app.task_manager.active_tasks.values() if t['type'] == 'processing' and t['status'] == 'Running'])}
Total Active: {app.task_manager.get_active_task_count()}

RECOMMENDATIONS:
• Keep CPU usage below 80% for optimal performance
• Reduce concurrent tasks if memory usage exceeds 80%
• Monitor task completion rates for efficiency
            """
            messagebox.showinfo("Performance Statistics", stats_msg.strip())
        except ImportError:
            messagebox.showinfo("Performance", "Install 'psutil' package for detailed system stats")
    
    def show_parallel_settings():
        """Show parallel processing settings dialog."""
        settings_window = bootstrap.Toplevel(title="Parallel Processing Settings")
        settings_window.geometry("500x400")
        
        main_frame = ttk.Frame(settings_window, padding=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(main_frame, text="Parallel Processing Configuration", font=('Segoe UI', 16, 'bold')).pack(pady=(0, 20))
        
        # Current settings display
        current_frame = ttk.Labelframe(main_frame, text=" Current Settings ", padding=15)
        current_frame.pack(fill=X, pady=(0, 20))
        
        ttk.Label(current_frame, text=f"Max Downloads: {app.max_concurrent_downloads.get()}").pack(anchor=W)
        ttk.Label(current_frame, text=f"Max Processing: {app.max_concurrent_processing.get()}").pack(anchor=W)
        ttk.Label(current_frame, text=f"Active Downloads: {len([t for t in app.task_manager.active_tasks.values() if t['type'] == 'download'])}").pack(anchor=W)
        ttk.Label(current_frame, text=f"Active Processing: {len([t for t in app.task_manager.active_tasks.values() if t['type'] == 'processing'])}").pack(anchor=W)
        
        # Quick presets
        presets_frame = ttk.Labelframe(main_frame, text=" Quick Presets ", padding=15)
        presets_frame.pack(fill=X, pady=(0, 20))
        
        presets = [
            ("Conservative", 2, 1),
            ("Balanced", 3, 2),
            ("Aggressive", 4, 3),
            ("Maximum", 5, 4)
        ]
        
        for name, downloads, processing in presets:
            ttk.Button(
                presets_frame, 
                text=f"{name} ({downloads}D/{processing}P)",
                command=lambda d=downloads, p=processing: [
                    app.max_concurrent_downloads.set(d),
                    app.max_concurrent_processing.set(p),
                    app.update_header_status()
                ],
                style='outline.TButton'
            ).pack(fill=X, pady=2)
        
        ttk.Button(main_frame, text="Close", command=settings_window.destroy).pack(pady=10)
    
    def configure_default_paths():
        """Configure default download and output paths."""
        paths_window = bootstrap.Toplevel(title="Default Paths Configuration")
        paths_window.geometry("600x300")
        
        main_frame = ttk.Frame(paths_window, padding=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(main_frame, text="Configure Default Paths", font=('Segoe UI', 16, 'bold')).pack(pady=(0, 20))
        
        # Download path
        download_frame = ttk.Labelframe(main_frame, text=" Download Location ", padding=15)
        download_frame.pack(fill=X, pady=(0, 15))
        
        path_frame = ttk.Frame(download_frame)
        path_frame.pack(fill=X)
        
        ttk.Entry(path_frame, textvariable=app.output_path, font=('Consolas', 10)).pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        ttk.Button(path_frame, text="Browse", command=app.browse_folder).pack(side=RIGHT)
        
        # Quick path buttons
        quick_frame = ttk.Frame(download_frame)
        quick_frame.pack(fill=X, pady=(10, 0))
        
        quick_paths = [
            ("Downloads", str(Path.home() / "Downloads")),
            ("Desktop", str(Path.home() / "Desktop")),
            ("Videos", str(Path.home() / "Videos")),
            ("Documents", str(Path.home() / "Documents"))
        ]
        
        for name, path in quick_paths:
            ttk.Button(
                quick_frame, text=name,
                command=lambda p=path: app.output_path.set(p),
                style='outline.TButton'
            ).pack(side=LEFT, padx=(0, 5))
        
        ttk.Button(main_frame, text="Close", command=paths_window.destroy).pack(pady=20)
    
    def show_user_guide():
        """Show comprehensive user guide."""
        guide_window = bootstrap.Toplevel(title="User Guide - v4.0")
        guide_window.geometry("900x700")
        
        text_widget = scrolledtext.ScrolledText(guide_window, font=('Segoe UI', 10), wrap='word')
        text_widget.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        guide_text = """
PRO VIDEO DOWNLOADER & PROCESSOR SUITE v4.0 - USER GUIDE

=== NEW PARALLEL PROCESSING FEATURES ===

1. CONCURRENT DOWNLOADS
   • Download 2-5 videos simultaneously
   • Configurable in Parallel Settings tab
   • Automatic load balancing
   • Real-time progress monitoring

2. MULTIPLE PROCESSING TABS
   • Open multiple video processing sessions
   • Each tab processes independently
   • Use "New Processing Tab" to create more
   • Close tabs when done to free resources

3. ENHANCED BATCH PROCESSING
   • Process multiple videos in parallel
   • Configurable concurrent processing limit
   • Progress tracking with ETA
   • Automatic error handling and retry

4. REAL-TIME TASK MONITORING
   • Active Tasks Monitor shows all running operations
   • Color-coded status indicators
   • Cancel individual tasks from context menu
   • Performance statistics integration

=== GETTING STARTED ===

BASIC DOWNLOAD:
1. Enter video URL in the Download tab
2. Select quality and format preferences
3. Set output location
4. Click "Download Current" or add to queue

PARALLEL DOWNLOADING:
1. Add multiple URLs to the queue
2. Adjust concurrent download limit (Parallel Settings)
3. Click "Parallel Download All"
4. Monitor progress in Active Tasks Monitor

VIDEO PROCESSING:
1. Open Processing tab (or create new tab)
2. Select input video file
3. Choose enhancement method and intensity
4. Set output location
5. Click "Process Video"

BATCH PROCESSING:
1. Go to Tools → Enhanced Batch Processor
2. Add multiple video files
3. Configure method, intensity, and parallel count
4. Click "Process Batch"

=== PERFORMANCE OPTIMIZATION ===

RECOMMENDED SETTINGS:
• Fast internet: 3-4 concurrent downloads
• Slow internet: 1-2 concurrent downloads
• High-end CPU: 3-4 concurrent processing
• Low-end CPU: 1-2 concurrent processing

TROUBLESHOOTING:
• High CPU usage: Reduce concurrent processing
• High memory usage: Close unused tabs
• Slow downloads: Check internet connection
• Processing errors: Try different intensity levels

=== KEYBOARD SHORTCUTS ===

Ctrl+N: New processing tab
Ctrl+O: Open file browser
Ctrl+S: Save/Export queue
Ctrl+Q: Quit application
F5: Refresh queue status

=== TIPS AND TRICKS ===

1. Use presets for common processing tasks
2. Monitor system resources in Performance Stats
3. Export/Import queues for batch operations
4. Use context menu for queue management
5. Close completed tabs to improve performance
        """
        
        text_widget.insert('1.0', guide_text)
        text_widget.config(state='disabled')
    
    def show_performance_tips():
        """Show performance optimization tips."""
        tips_window = bootstrap.Toplevel(title="Performance Tips")
        tips_window.geometry("700x500")
        
        text_widget = scrolledtext.ScrolledText(tips_window, font=('Segoe UI', 10), wrap='word')
        text_widget.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        tips_text = """
PERFORMANCE OPTIMIZATION TIPS

=== PARALLEL PROCESSING ===

DOWNLOAD OPTIMIZATION:
• Use 2-3 concurrent downloads for most systems
• Increase to 4-5 only with very fast internet (100+ Mbps)
• Monitor network usage to avoid ISP throttling
• Some sites may limit concurrent connections

VIDEO PROCESSING OPTIMIZATION:
• Use 1-2 concurrent processing on systems with 4-6 CPU cores
• Use 2-3 concurrent processing on systems with 8+ CPU cores
• Never exceed your CPU core count
• Close other applications during heavy processing

=== SYSTEM RESOURCES ===

MEMORY MANAGEMENT:
• Each processing tab uses 200-500 MB RAM
• Close unused tabs to free memory
• Monitor memory usage in Performance Stats
• Restart application if memory usage becomes excessive

CPU MANAGEMENT:
• Video processing is CPU-intensive
• Keep total CPU usage below 80%
• Use Task Manager to monitor CPU cores
• Consider processing overnight for large batches

STORAGE OPTIMIZATION:
• Use SSD for output location when possible
• Ensure sufficient free space (2x video size)
• Avoid network drives for processing
• Clean up temporary files regularly

=== NETWORK OPTIMIZATION ===

DOWNLOAD SPEED:
• Use wired connection when possible
• Close other bandwidth-intensive applications
• Consider download scheduling during off-peak hours
• Some platforms limit download speed

CONNECTION STABILITY:
• Stable connection is more important than speed
• Use download resume features when available
• Monitor for connection drops
• Consider using VPN for geo-restricted content

=== QUALITY SETTINGS ===

BALANCED APPROACH:
• Best Quality (1080p) for most use cases
• Ultra HD (4K) only if you have the bandwidth and storage
• Standard quality for mobile viewing
• Audio-only formats for podcasts/music

PROCESSING INTENSITY:
• Start with intensity 1.0 and adjust as needed
• Higher intensity ≠ always better quality
• Test on small clips before batch processing
• Different methods work better for different content

=== TROUBLESHOOTING ===

COMMON ISSUES:
• "Too many requests" → Reduce concurrent downloads
• "Out of memory" → Close tabs, reduce concurrent processing
• "Processing failed" → Try lower intensity or different method
• "Download failed" → Check URL, try different quality

PERFORMANCE MONITORING:
• Use built-in Performance Stats (Tools menu)
• Monitor Active Tasks for bottlenecks
• Check system Task Manager for resource usage
• Log errors for troubleshooting

=== BEST PRACTICES ===

WORKFLOW OPTIMIZATION:
1. Plan your batch operations
2. Group similar processing tasks
3. Use presets for consistency
4. Process during low system usage periods
5. Backup important processing settings
6. Update software components when available
        """
        
        text_widget.insert('1.0', tips_text)
        text_widget.config(state='disabled')
    
    # Bind methods to app
    app.show_performance_stats = show_performance_stats
    app.show_parallel_settings = show_parallel_settings
    # Use existing method on app if defined, otherwise bind a no-op
    if hasattr(app, 'clear_all_tasks'):
        app.clear_all_tasks = app.clear_all_tasks
    else:
        app.clear_all_tasks = lambda: None
    app.configure_default_paths = configure_default_paths
    app.show_user_guide = show_user_guide
    app.show_performance_tips = show_performance_tips
    
    def on_closing():
        """Enhanced closing handler with task cleanup."""
        active_tasks = app.task_manager.get_active_task_count()
        
        if active_tasks > 0:
            if messagebox.askyesno("Active Tasks", 
                                  f"You have {active_tasks} active tasks running. "
                                  "Closing will cancel all tasks. Continue?"):
                app.task_manager.shutdown()
                root.destroy()
        elif app.url_list and messagebox.askyesno("Exit Confirmation", 
                                                 "You have items in your queue. Exit anyway?"):
            app.task_manager.shutdown()
            root.destroy()
        elif not app.url_list and active_tasks == 0:
            app.task_manager.shutdown()
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Center window on screen
    try:
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry(f"+{x}+{y}")
    except:
        pass
    
    # Start periodic updates
    def update_displays():
        """Periodic update of displays."""
        app.update_header_status()
        app.update_task_monitor()
        root.after(2000, update_displays)  # Update every 2 seconds
    
    # Initial setup
    update_displays()
    
    root.mainloop()
    

if __name__ == "__main__":
    main()
    