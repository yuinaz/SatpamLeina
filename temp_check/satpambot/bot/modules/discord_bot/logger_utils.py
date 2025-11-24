import os
from datetime import datetime
from discord import Message

LOG_PATH = "data/violations.log"

def log_violation(message: Message, image_hash: str, reason: str):
    """Catat pelanggaran terkait gambar ke file log."""
    user = f"{message.author} (ID: {message.author.id})"
    channel = f"{message.channel} (ID: {message.channel.id})"
    time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = (
        f"[{time_str} UTC] 🚨 Pelanggaran oleh {user} di {channel}\n"
        f"Alasan: {reason}\n"
        f"Hash: {image_hash}\n"
        f"Isi Pesan: {message.content}\n"
        f"{'-'*50}\n"
    )

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry)

def log_image_event(message: Message, image_hash: str):
    """(Opsional) Catat setiap deteksi gambar, meskipun tidak melanggar."""
    # Kosongkan fungsi ini jika logging non-pelanggaran tidak diperlukan
    pass


def log_blacklisted_image(message: Message, image_hash: str):
    """Compat wrapper untuk nama lama: log pelanggaran gambar blacklist."""
    return log_violation(message, image_hash, reason="blacklisted image")
