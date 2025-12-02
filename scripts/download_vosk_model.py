#!/usr/bin/env python3
import os
import sys
import zipfile
import urllib.request
import ssl
from pathlib import Path

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"
MODEL_ZIP = "vosk-model-small-cn-0.22.zip"
MODEL_DIR_NAME = "vosk-model-small-cn-0.22"

# Determine the project root directory (parent of 'scripts')
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TARGET_DIR = PROJECT_ROOT / "models"

def download_and_extract_model():
    # Ensure models directory exists
    if not TARGET_DIR.exists():
        TARGET_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {TARGET_DIR}")

    target_path = TARGET_DIR / MODEL_DIR_NAME
    
    # Check if model already exists
    if target_path.exists():
        print(f"Model already exists at: {target_path}")
        return

    zip_path = TARGET_DIR / MODEL_ZIP

    # Download
    if not zip_path.exists():
        print(f"Downloading model from {MODEL_URL}...")
        try:
            # Create unverified context to avoid SSL errors on some systems
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(MODEL_URL, context=context) as response, open(zip_path, 'wb') as out_file:
                out_file.write(response.read())
            print("Download complete.")
        except Exception as e:
            print(f"Download failed: {e}")
            return

    # Extract
    print(f"Extracting {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(TARGET_DIR)
        print("Extraction complete.")
        
        # Cleanup zip file
        os.remove(zip_path)
        print("Removed zip file.")
        
    except Exception as e:
        print(f"Extraction failed: {e}")

if __name__ == "__main__":
    download_and_extract_model()
