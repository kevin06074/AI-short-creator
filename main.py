import os
import subprocess
import sys

def run_script(script_name):
    """Safely run a Python script with error handling."""
    try:
        result = subprocess.run([sys.executable, script_name], 
                              check=True, 
                              capture_output=True, 
                              text=True)
        print(f"✓ Successfully executed {script_name}")
        if result.stdout:
            print(f"Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error executing {script_name}: {e}")
        print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"✗ Script not found: {script_name}")
        return False
    return True

def safe_remove(file_path):
    """Safely remove a file with error handling."""
    try:
        os.remove(file_path)
        print(f"✓ Successfully removed {file_path}")
    except FileNotFoundError:
        print(f"⚠ File not found: {file_path}")
    except OSError as e:
        print(f"✗ Error removing {file_path}: {e}")

# Execute scripts in sequence with error handling
scripts = [
    "video_downloader.py",
    "transcript_analysis.py", 
    "video_cutter.py",
    "face.py",
    "last_edit.py"
]

print("Starting video processing pipeline...")

for script in scripts:
    if not run_script(script):
        print(f"Pipeline stopped due to error in {script}")
        sys.exit(1)

# Clean up temporary files
safe_remove("output/best_video_1.mp4")
safe_remove("output/best_video_3.mp4")

# Run final processing
if run_script("process.py"):
    print("✓ Video processing pipeline completed successfully!")
else:
    print("✗ Pipeline failed at final processing step")
    sys.exit(1)
