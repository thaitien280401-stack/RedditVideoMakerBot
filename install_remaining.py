import subprocess, sys, os
venv_pip = r"c:\Users\Administrator\Desktop\earn\RedditVideoMakerBot\venv\Scripts\pip.exe"
log_file = r"c:\Users\Administrator\Desktop\earn\RedditVideoMakerBot\install_result.txt"

packages = [
    "moviepy", "playwright", "translators", "pyttsx3", 
    "Flask", "clean-text", "unidecode", "ffmpeg-python", "yt-dlp"
]

results = []
for pkg in packages:
    try:
        r = subprocess.run(
            [venv_pip, "install", "--no-cache-dir", pkg],
            capture_output=True, text=True, timeout=180
        )
        status = "OK" if r.returncode == 0 else f"FAIL: {r.stderr[-300:]}"
        results.append(f"{pkg}: {status}")
    except subprocess.TimeoutExpired:
        results.append(f"{pkg}: TIMEOUT")
    except Exception as e:
        results.append(f"{pkg}: ERROR: {e}")

# Check pip list
r2 = subprocess.run([venv_pip, "list", "--format=columns"], capture_output=True, text=True, timeout=30)
results.append(f"\nPIP LIST:\n{r2.stdout}")

with open(log_file, "w", encoding="utf-8") as f:
    f.write("\n".join(results))
