from pathlib import Path
from datetime import datetime
import os
import subprocess

# Set up root and script paths
ROOT_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT_DIR / "bin"
EXPORT_SCRIPT = BIN_DIR / "export_savedsearches_btool.py"
UPLOAD_SCRIPT = BIN_DIR / "upload_to_wikijs.py"

# Generate log file path with timestamp
execution_time = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file_path = ROOT_DIR / f"logs/wikijs_upload_{execution_time}.log"
log_file_path.parent.mkdir(parents=True, exist_ok=True)

# Function to run a script with shared LOG_FILE environment
def run_script(script_path: Path):
    print(f"\n→ Executing {script_path.name} ...\n")
    result = subprocess.run(
        ["python", str(script_path)],
        cwd=ROOT_DIR,
        text=True,
        env={**os.environ, "LOG_FILE": str(log_file_path)},
    )
    if result.returncode != 0:
        raise RuntimeError(f"Error while executing {script_path.name} (Exit Code: {result.returncode})")

# Run both export and upload scripts
if __name__ == "__main__":
    run_script(EXPORT_SCRIPT)
    run_script(UPLOAD_SCRIPT)
    