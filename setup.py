#!/usr/bin/env python3
"""Setup script for NetGuard."""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd):
    """Run a command and print output."""
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False

def setup_python_environment():
    """Set up Python virtual environment and install dependencies."""
    venv_path = Path('.venv')
    if not venv_path.exists():
        print("Creating virtual environment...")
        if not run_command([sys.executable, '-m', 'venv', '.venv']):
            return False

    # Determine the correct pip path
    if os.name == 'nt':  # Windows
        pip_path = venv_path / 'Scripts' / 'pip'
    else:  # Unix-like
        pip_path = venv_path / 'bin' / 'pip'

    # Upgrade pip
    print("Upgrading pip...")
    if not run_command([str(pip_path), 'install', '--upgrade', 'pip']):
        return False

    # Install requirements
    print("Installing requirements...")
    if not run_command([str(pip_path), 'install', '-r', 'requirements.txt']):
        return False

    return True

def main():
    """Main setup function."""
    if not setup_python_environment():
        print("Failed to set up Python environment")
        sys.exit(1)

    print("\nSetup completed successfully!")
    print("\nTo activate the virtual environment:")
    if os.name == 'nt':  # Windows
        print("    .venv\\Scripts\\activate")
    else:  # Unix-like
        print("    source .venv/bin/activate")

if __name__ == '__main__':
    main()
