# QR Code Encryption Project

A Python project to encrypt data (images + JSON) and encode it into QR codes, with a scanner to decrypt and view the data.  
Designed to handle sensitive or structured data securely in QR format.

---
## Features

### QR Generator (qr_generator.py)
- Combines an image (.jpg, .jpeg, or .png) and a JSON file into a single encrypted payload.
- Encrypts data using AES-256-CBC with a static key and IV.
- Generates a single QR code per data folder.
- Automatically validates:
  - Presence of required files
  - File size limits
- Logs progress and warnings in the terminal.

### QR Scanner (qr_scanner.py)
- Scans a QR code image from the command line.
- Prints:
  - The encrypted Base64 string
  - Decrypted JSON metadata
  - Base64 image string
- Decrypts using the same AES key and IV.

---

## Installation

1. Clone the repository
>git clone <repo-url> cd <repo-folder>
2. Install Python dependencies:
>pip install -r requirements.txt
3. Linux users: Install ZBar for pyzbar:
>sudo apt-get install libzbar0
---

## Usage

### Generate QR Codes

1. Place data folders inside `data/` =>`data/d1/image.jpg data/d1/data.json`
2. Run the generator:
> python qr_scanner.py qr_codes/d1_qr.png
3. Output:
   - Encrypted Base64 string
   - Decrypted JSON metadata
   - Base64 image string (preview first 200 chars)

---

## Limitations

- Maximum payload per single QR code is ~2–3 KB (AES encrypted + Base64).  
- Current scanner supports single QR code only.

---

## Encryption Details

- Algorithm: AES-256-CBC  
- Key & IV: Static (defined in the scripts)  
- Padding: PKCS7  

---

## Dependencies

- Python 3.8+  
- cryptography  
- qrcode  
- Pillow  
- pyzbar (or opencv-python for ZBar-free scanning)

---

## Future Improvements

- Multi-part QR code support for larger datasets (>3 KB)  
- Automatic QR grid scanning and merging  
- Optional direct image display in scanner instead of Base64







