import sys
import base64
import json
import logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from pyzbar.pyzbar import decode
from PIL import Image

# ---------- CONFIG ----------
STATIC_KEY = b"1234567890abcdef1234567890abcdef"  # same AES-256 key
STATIC_IV = b"abcdef1234567890"                   # same AES CBC IV

# ---------- LOGGING ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ---------- UTILS ----------
def decrypt_data(encrypted_data: bytes) -> bytes:
    """Decrypt AES CBC data with static key and IV."""
    cipher = Cipher(algorithms.AES(STATIC_KEY), modes.CBC(STATIC_IV), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(encrypted_data) + decryptor.finalize()

    # Remove padding
    pad_len = decrypted[-1]
    return decrypted[:-pad_len]


def scan_qr(image_path: str) -> str:
    """Scan a single QR code from an image and return the decoded text."""
    img = Image.open(image_path)
    decoded_objs = decode(img)
    if not decoded_objs:
        raise ValueError("No QR code found in image.")
    return decoded_objs[0].data.decode()


def main():
    if len(sys.argv) != 2:
        logging.error("Usage: python qr_scanner.py <qr_image_path>")
        return

    qr_image_path = sys.argv[1]

    try:
        logging.info(f"Scanning QR: {qr_image_path}")
        qr_text = scan_qr(qr_image_path)

        # Step 1: Print encrypted string
        logging.info("Encrypted string (Base64):")
        print(qr_text)
        print("-" * 80)

        # Step 2: Decode base64 -> decrypt AES
        encrypted_bytes = base64.b64decode(qr_text)
        decrypted_bytes = decrypt_data(encrypted_bytes)
        combined_json = json.loads(decrypted_bytes.decode())

        # Step 3: Print metadata and image
        logging.info("Decrypted JSON metadata:")
        print(json.dumps(combined_json.get("metadata"), indent=4))
        print("-" * 80)

        image_b64 = combined_json.get("image")
        logging.info("Image Base64 string:")
        print(image_b64)
        print("\nFull image base64 can be copied to any base64-to-image viewer online.")

    except Exception as e:
        logging.exception(f"Error scanning QR: {e}")


if __name__ == "__main__":
    main()
