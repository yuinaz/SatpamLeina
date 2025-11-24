import hashlib
import os

BLACKLIST_FILE = "blacklist_image_hashes.txt"

def calculate_md5(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
            return hashlib.md5(data).hexdigest()
    except Exception as e:
        print(f"❌ Gagal menghitung hash: {e}")
        return None

def add_hash_to_blacklist(file_path):
    if not os.path.exists(file_path):
        print("❌ File gambar tidak ditemukan.")
        return

    hash_value = calculate_md5(file_path)
    if not hash_value:
        return

    if not os.path.exists(BLACKLIST_FILE):
        open(BLACKLIST_FILE, "w").close()

    with open(BLACKLIST_FILE, "r+") as f:
        hashes = {line.strip() for line in f if line.strip()}
        if hash_value in hashes:
            print("⚠️ Hash gambar sudah ada di blacklist.")
        else:
            f.write(hash_value + "\n")
            print("✅ Hash gambar berhasil ditambahkan ke blacklist.")

if __name__ == "__main__":
    file_path = input("Masukkan path gambar phishing: ").strip().strip('"').strip("'")
    add_hash_to_blacklist(file_path)
