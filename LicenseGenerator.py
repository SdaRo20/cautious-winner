import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path
import uuid
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import ttkbootstrap as bootstrap
import os

# --- Core License Manager Class (Copied from combined file) ---
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
            # Decode and decrypt
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

# --- GUI for License Generation ---
class LicenseGeneratorGUI:
    """GUI tool for generating license keys."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Pro Downloader License Key Generator")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        self.license_manager = LicenseManager()
        
        self.duration_var = tk.IntVar(value=30)
        self.user_id_var = tk.StringVar()
        self.extra_data_var = tk.StringVar()
        self.license_key_var = tk.StringVar()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Builds the main user interface."""
        style = bootstrap.Style(theme='superhero')
        self.root.configure(bg=style.colors.bg)
        
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill='both', expand=True)
        
        # Header
        ttk.Label(main_frame, text="License Key Generator", font=('Segoe UI', 20, 'bold')).pack(pady=(0, 20))
        
        # Inputs Frame
        input_frame = ttk.Labelframe(main_frame, text=" License Details ", padding=20)
        input_frame.pack(fill='x', pady=(0, 15))
        input_frame.grid_columnconfigure(1, weight=1)
        
        # Duration
        ttk.Label(input_frame, text="Duration (days):", font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, sticky='w', pady=5, padx=(0, 10))
        duration_spin = ttk.Spinbox(
            input_frame, 
            from_=1, to=3650, 
            increment=1,
            textvariable=self.duration_var,
            width=10,
            style='info.TSpinbox'
        )
        duration_spin.grid(row=0, column=1, sticky='ew')
        
        # User ID
        ttk.Label(input_frame, text="User ID (optional):", font=('Segoe UI', 11, 'bold')).grid(row=1, column=0, sticky='w', pady=5, padx=(0, 10))
        ttk.Entry(input_frame, textvariable=self.user_id_var, font=('Consolas', 10)).grid(row=1, column=1, sticky='ew')
        
        # Extra Data
        ttk.Label(input_frame, text="Extra Data (JSON):", font=('Segoe UI', 11, 'bold')).grid(row=2, column=0, sticky='w', pady=5, padx=(0, 10))
        ttk.Entry(input_frame, textvariable=self.extra_data_var, font=('Consolas', 10)).grid(row=2, column=1, sticky='ew')
        
        # Generate Button
        ttk.Button(
            main_frame,
            text="Generate License Key",
            command=self.generate_key,
            style='success.TButton'
        ).pack(fill='x', ipady=10, pady=(15, 20))
        
        # Output Frame
        output_frame = ttk.Labelframe(main_frame, text=" Generated License Key ", padding=15)
        output_frame.pack(fill='both', expand=True)
        
        self.license_key_text = tk.Text(
            output_frame,
            height=10,
            font=('Consolas', 10),
            wrap='word',
            bg=style.colors.bg,
            fg=style.colors.fg
        )
        self.license_key_text.pack(fill='both', expand=True, pady=(0, 10))
        
        # Copy Button
        ttk.Button(
            output_frame,
            text="Copy to Clipboard",
            command=self.copy_to_clipboard,
            style='info-outline.TButton'
        ).pack(fill='x', ipady=5)
        
    def generate_key(self):
        """Generates a license key based on user input."""
        try:
            duration_days = self.duration_var.get()
            user_id = self.user_id_var.get().strip()
            
            extra_data = {}
            if self.extra_data_var.get().strip():
                try:
                    extra_data = json.loads(self.extra_data_var.get().strip())
                except json.JSONDecodeError:
                    messagebox.showerror("Error", "Invalid JSON format for extra data.")
                    return
            
            license_key, _ = self.license_manager.generate_license_key(
                duration_days, 
                user_id if user_id else None, 
                extra_data
            )
            
            self.license_key_text.delete('1.0', 'end')
            self.license_key_text.insert('1.0', license_key)
            messagebox.showinfo("Success", "License key generated successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate license: {e}")
            
    def copy_to_clipboard(self):
        """Copies the generated key to the clipboard."""
        license_key = self.license_key_text.get('1.0', 'end').strip()
        if license_key:
            self.root.clipboard_clear()
            self.root.clipboard_append(license_key)
            self.root.update()
            messagebox.showinfo("Success", "License key copied to clipboard.")
        else:
            messagebox.showwarning("Warning", "No license key to copy.")

# --- Main Entry Point ---
if __name__ == "__main__":
    root = bootstrap.Window(themename="superhero")
    app = LicenseGeneratorGUI(root)
    
    # Center window
    try:
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry(f"+{x}+{y}")
    except:
        pass
        
    root.mainloop()
