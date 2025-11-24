import os
import time
import hashlib
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from typing import Dict

# Ceksum terakhir setiap file
file_hashes: Dict[str, str] = {}
last_push_time: float = 0.0
MIN_PUSH_INTERVAL: float = 10.0  # seconds to debounce rapid edits

def file_changed(file_path: str) -> bool:
    fp = os.path.abspath(file_path)
    if not os.path.exists(fp):
        return False
    try:
        # read in binary to avoid decode issues
        with open(fp, "rb") as f:
            content = f.read()
        new_hash = hashlib.md5(content).hexdigest()
        if fp not in file_hashes or file_hashes[fp] != new_hash:
            file_hashes[fp] = new_hash
            return True
    except Exception as exc:
        print(f"[auto_push] file_changed error: {exc}")
    return False

class AutoGitPushHandler(FileSystemEventHandler):
    def on_modified(self, event: FileSystemEvent) -> None:
        try:
            src = os.path.abspath(event.src_path)
        except Exception:
            src = getattr(event, "src_path", None)
        if event.is_directory or not (isinstance(src, str) and src.endswith(('.py', '.pyw'))):
            return
        # ignore changes in .git, virtualenvs, and cache directories
        if any(part in src.split(os.sep) for part in ('.git', 'env', 'venv', '.venv', '__pycache__')):
            return

        if file_changed(src):
            print(f"📦 File berubah: {src}")
            self.git_push()
        else:
            print(f"🟡 {src} disimpan tapi tidak berubah (skip)")

    def git_push(self) -> None:
        try:
            global last_push_time
            now = time.time()
            if now - last_push_time < MIN_PUSH_INTERVAL:
                print("⏳ Debounced push (recent push happened)")
                return

            status = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
            if not status:
                print("✅ Tidak ada perubahan untuk dipush.")
                return

            subprocess.run(["git", "add", "."], check=True)
            # commit only if changes staged
            try:
                subprocess.run(["git", "commit", "-m", "🧠 Auto-push file .py yang berubah"], check=True)
            except subprocess.CalledProcessError:
                # nothing to commit (race), continue to push staged changes
                pass

            branch = os.getenv('AUTO_PUSH_BRANCH', 'main')
            subprocess.run(["git", "push", "origin", branch], check=True)
            last_push_time = now
            print("🚀 Push berhasil.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Gagal push (CalledProcessError): {e}")
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