import os
import sys
import subprocess

def main():
    # Detect if we are running as a PyInstaller bundled executable
    if getattr(sys, 'frozen', False):
        # We are running as an EXE
        base_dir = os.path.dirname(sys.executable)
    else:
        # We are running as a Python script
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Ensure current working directory is the project root
    os.chdir(base_dir)
    
    # Prepare to spawn the process without showing a black console window
    startupinfo = None
    creationflags = 0
    
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW

    # Define the command to launch the main UI
    if getattr(sys, 'frozen', False):
        # Rely on the user's installed python interpreter in systems path
        cmd = ["python", "launcher.py"]
    else:
        cmd = [sys.executable, "launcher.py"]

    try:
        subprocess.Popen(
            cmd,
            startupinfo=startupinfo,
            creationflags=creationflags,
            shell=False
        )
    except Exception as e:
        # If python is not found or other errors happen, this fallback handles it silently
        pass

if __name__ == '__main__':
    main()
