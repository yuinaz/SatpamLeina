import os
import time
import hashlib
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Ceksum terakhir setiap file
file_hashes = {}

def file_changed(file_path):
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        new_hash = hashlib.md5(content).hexdigest()
        if file_path not in file_hashes or file_hashes[file_path] != new_hash:
            file_hashes[file_path] = new_hash
            return True
    except:
        pass
    return False

class AutoGitPushHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith(".py"):
            return

        if file_changed(event.src_path):
            print(f"📦 File berubah: {event.src_path}")
            self.git_push()
        else:
            print(f"🟡 {event.src_path} disimpan tapi tidak berubah (skip)")

    def git_push(self):
        try:
            status = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
            if not status:
                print("✅ Tidak ada perubahan untuk dipush.")
                return

            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "🧠 Auto-push file .py yang berubah"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("🚀 Push berhasil.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Gagal push: {e}")
        except Exception as e:
            print(f"❌ Error umum: {e}")

if __name__ == "__main__":
    path = "."
    print("👀 Memantau file .py... (Ctrl+C untuk berhenti)")
    event_handler = AutoGitPushHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=True)
    observer.start()

    try:
        while True:
            observer.join(timeout=1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 Pemantauan dihentikan.")
    observer.join()