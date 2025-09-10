# Pro Video Downloader & Processor Suite (Airplant)

This repository contains a set of Python utilities and GUI tools for downloading and processing videos at scale. It includes a license generator tool and an enhanced (work-in-progress) Pro downloader UI with parallel download and processing features.

## Key files

- `LicenseGenerator/LicenseGenerator.py` - A small GUI tool to generate encrypted license keys (uses `cryptography`, `ttkbootstrap`).
- `LicenseGenerator/Pro DownloadV6.py` - Combined/enhanced application skeleton for a Pro Video Downloader + Processor (UI & licensing integration). This file contains many TODOs and placeholders and is not a finished release.
- `requirements.txt` - Primary Python dependencies used across the project.

Other utility scripts, sample data, and resources are present in the repository.

## Quick start

1. Create and activate a virtual environment (recommended):

```powershell
python -m venv venv; .\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Generate a license key (for testing):

```powershell
python LicenseGenerator\LicenseGenerator.py
```

Use the GUI to generate a license key. The generator uses an internal `LicenseManager` to create encrypted license tokens.

4. Run the (work-in-progress) Pro downloader GUI:

```powershell
python LicenseGenerator\Pro\ DownloadV6.py
```

Note: `Pro DownloadV6.py` is a combined/partial file (many functions are placeholders). Review and complete missing implementations before relying on it in production.

## License system

The license system uses PBKDF2-HMAC + Fernet symmetric encryption to create encrypted, signed license blobs. The generator stores the signature and expiry inside the encrypted payload. The core implementation is in `LicenseGenerator/LicenseGenerator.py` and is also referenced inside the `Pro DownloadV6.py` file.

## Development notes

- The repo includes experimental scripts and multiple utilities. Some scripts are legacy or duplicates—review names before running.
- `Pro DownloadV6.py` contains many TODOs and unfinished UI wiring. If you want, I can help finish specific features (e.g., video processing pipeline, task manager, or the license activation dialog).

## Contributing

If you'd like changes, open an issue or ask here. I can help tidy up the downloader app, wire missing functions, or add tests.

## Contact

This README was added automatically; for further edits tell me what sections to expand or what commands to include.

---
Generated and committed by an automated assistant.
