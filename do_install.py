import subprocess, sys, os
log = os.path.join(os.path.dirname(__file__), "install_log.txt")
with open(log, "w") as f:
    f.write("Starting install...\n")
    f.flush()
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "gTTS", "rich", "Pillow", "requests"],
        capture_output=True, text=True, timeout=300
    )
    f.write(f"STDOUT:\n{r.stdout}\n")
    f.write(f"STDERR:\n{r.stderr}\n")
    f.write(f"Return code: {r.returncode}\n")
    
    # Also check what's installed
    r2 = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True)
    f.write(f"\nPIP LIST:\n{r2.stdout}\n")
    f.write("DONE\n")
