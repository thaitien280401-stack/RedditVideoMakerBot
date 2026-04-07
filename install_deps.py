"""Install script - run this to install all dependencies."""
import subprocess
import sys
import os

def main():
    pip = os.path.join(os.path.dirname(sys.executable), "pip.exe")
    if not os.path.exists(pip):
        pip = [sys.executable, "-m", "pip"]
    else:
        pip = [pip]
    
    # Upgrade pip first
    print("=== Upgrading pip ===")
    subprocess.run([*pip, "install", "--upgrade", "pip"], check=False)
    
    # Core packages that we need (lighter list - skip heavy ML packages)
    packages = [
        "gTTS",
        "moviepy",
        "playwright",
        "praw",
        "requests",
        "rich",
        "toml",
        "translators",
        "pyttsx3",
        "tomlkit",
        "Flask",
        "clean-text",
        "unidecode",
        "ffmpeg-python",
        "yt-dlp",
        "Pillow",
    ]
    
    print(f"\n=== Installing {len(packages)} packages ===")
    for pkg in packages:
        print(f"\nInstalling {pkg}...")
        result = subprocess.run([*pip, "install", pkg], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  OK: {pkg}")
        else:
            print(f"  FAIL: {pkg} - {result.stderr[-200:] if result.stderr else 'unknown error'}")
    
    # Install playwright browsers
    print("\n=== Installing Playwright browsers ===")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
    
    # Check what's installed
    print("\n=== Installed packages ===")
    result = subprocess.run([*pip, "list", "--format=columns"], capture_output=True, text=True)
    print(result.stdout)
    
    # Write results to file
    with open("install_status.txt", "w") as f:
        f.write(result.stdout)
        f.write("\n\nINSTALL COMPLETE\n")
    
    print("\nDone! Results saved to install_status.txt")

if __name__ == "__main__":
    main()
