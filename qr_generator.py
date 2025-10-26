import os
import json
import base64
import qrcode
import logging
from io import BytesIO
from PIL import Image
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# ---------- CONFIG ----------
MAX_IMAGE_SIZE_BYTES = 1000
DATA_DIR = "data"
OUTPUT_DIR = "qr_codes"
STATIC_KEY = b"1234567890abcdef1234567890abcdef"  # 32 bytes for AES-256
STATIC_IV = b"abcdef1234567890"                   # 16 bytes for AES CBC
MAX_QR_SIZE_BYTES = 2900                          # Safe QR capacity (~3 KB)
MAX_FILE_SIZE_MB = 2                              # Sanity check for files

# ---------- LOGGING SETUP ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ---------- UTILS ----------
def encrypt_data(data: bytes) -> bytes:
    """Encrypt the data using AES CBC."""
    pad_len = 16 - (len(data) % 16)
    logging.debug(f"Padding length: {pad_len} bytes (before encryption)")
    data += bytes([pad_len]) * pad_len

    cipher = Cipher(algorithms.AES(STATIC_KEY), modes.CBC(STATIC_IV), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(data) + encryptor.finalize()

    logging.info(f"Encrypted data size: {len(encrypted)} bytes")
    logging.debug(f"Encrypted data (base64): {base64.b64encode(encrypted).decode()[:200]}...")  # Truncated preview
    return encrypted

def compress_image_in_memory(image_path: str, max_size_bytes: int = MAX_IMAGE_SIZE_BYTES) -> bytes:
    """Compress the image to stay below the target size (in memory)."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")  # ensure consistent format

        quality = 85
        step = 5
        buffer = BytesIO()

        while quality > 5:
            buffer.seek(0)
            buffer.truncate(0)
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            size = buffer.tell()

            if size <= max_size_bytes:
                logging.info(f"Compressed image to {size} bytes (quality={quality})")
                buffer.seek(0)
                return buffer.read()

            quality -= step

        # If still large, just return the smallest one
        buffer.seek(0)
        compressed_data = buffer.read()
        logging.warning(f"Could not reach {max_size_bytes} bytes limit (final size={len(compressed_data)} bytes)")
        return compressed_data


def combine_data(image_path: str, json_path: str) -> bytes:
    """Combine image + json into a single serialized JSON bytes object."""
    img_size = os.path.getsize(image_path)
    logging.info(f"Reading image: {image_path} ({img_size} bytes ≈ {img_size / 1024:.2f} KB)")

    # Compress image if needed
    if img_size > MAX_IMAGE_SIZE_BYTES:
        logging.info(f"Image exceeds {MAX_IMAGE_SIZE_BYTES} bytes; compressing...")
        image_bytes = compress_image_in_memory(image_path)
    else:
        with open(image_path, "rb") as f:
            image_bytes = f.read()

    json_size = os.path.getsize(json_path)
    with open(json_path, "r") as json_f:
        json_data = json.load(json_f)
        logging.info(f"Loaded JSON from {json_path} ({json_size} bytes ≈ {json_size / 1024:.2f} KB)")
        logging.debug(f"JSON before encryption:\n{json.dumps(json_data, indent=2, ensure_ascii=False)}")

    # Encode image in Base64 for JSON-safe serialization (still needed for now)
    image_b64 = base64.b64encode(image_bytes).decode()

    combined = {
        "image": image_b64,
        "metadata": json_data
    }

    serialized = json.dumps(combined, separators=(",", ":")).encode()
    logging.info(f"Serialized combined JSON size: {len(serialized)} bytes")
    return serialized


def generate_qr(encrypted_data: bytes, output_path: str):
    """Generate and save a QR code."""
    encoded_text = base64.b64encode(encrypted_data).decode()
    logging.info(f"Base64 encoded data size: {len(encoded_text)} characters")

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(encoded_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)
    logging.info(f"QR code saved at: {output_path}")


def find_image_file(dir_path: str):
    """Find an image file in the directory with valid extension."""
    for ext in ("jpg", "jpeg", "png"):
        candidate = os.path.join(dir_path, f"image.{ext}")
        if os.path.exists(candidate):
            logging.debug(f"Found image file: {candidate}")
            return candidate
    return None


def validate_directory(dir_path: str) -> tuple[bool, str, str]:
    """Check for required files and size limits. Returns (is_valid, image_path, json_path)."""
    image_path = find_image_file(dir_path)
    json_path = os.path.join(dir_path, "data.json")

    if not image_path:
        logging.warning(f"Missing image file in {dir_path} (expected image.jpg/.jpeg/.png)")
        return False, None, None
    if not os.path.exists(json_path):
        logging.warning(f"Missing data.json file in {dir_path}")
        return False, None, None

    for file_path in [image_path, json_path]:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            logging.warning(f"File {file_path} exceeds {MAX_FILE_SIZE_MB} MB, skipping.")
            return False, None, None

    return True, image_path, json_path


def main():
    if not os.path.exists(DATA_DIR):
        logging.error(f"Data directory '{DATA_DIR}' does not exist.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    directories = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]

    if not directories:
        logging.warning("No data subdirectories found.")
        return

    logging.info(f"Found {len(directories)} data directories to process.")

    for dir_name in directories:
        dir_path = os.path.join(DATA_DIR, dir_name)
        logging.info(f"\n--- Processing directory: {dir_name} ---")

        is_valid, image_path, json_path = validate_directory(dir_path)
        if not is_valid:
            continue

        try:
            combined = combine_data(image_path, json_path)
            encrypted = encrypt_data(combined)
            encoded_size = len(base64.b64encode(encrypted))

            logging.info(f"Encoded (base64) size after encryption: {encoded_size} bytes")

            if encoded_size > MAX_QR_SIZE_BYTES:
                logging.warning(f"{dir_name}: Encrypted data too large ({encoded_size} bytes) for QR, skipping.")
                continue

            output_path = os.path.join(OUTPUT_DIR, f"{dir_name}_qr.png")
            generate_qr(encrypted, output_path)
            logging.info(f"✅ Generated QR for {dir_name} -> {output_path}")

        except Exception as e:
            logging.exception(f"❌ Error processing {dir_name}: {e}")


if __name__ == "__main__":
    main()
