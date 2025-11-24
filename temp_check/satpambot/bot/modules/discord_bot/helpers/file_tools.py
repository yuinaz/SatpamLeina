import os

def read_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        f.write(data.strip())
