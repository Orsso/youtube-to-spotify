#!/usr/bin/env python3
"""
Automated setup script for YouTube to Spotify migrator.
"""

import os
import sys
import subprocess
import shutil

def check_python_version():
    """Check if Python version is 3.8+"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    if os.path.exists('venv'):
        print("✅ Virtual environment already exists")
        return True
    
    try:
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
        print("✅ Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to create virtual environment")
        return False

def install_dependencies():
    """Install required dependencies"""
    venv_python = os.path.join('venv', 'bin', 'python')
    if os.name == 'nt':  # Windows
        venv_python = os.path.join('venv', 'Scripts', 'python.exe')
    
    if not os.path.exists(venv_python):
        print("❌ Virtual environment not found")
        return False
    
    try:
        print("📦 Installing dependencies...")
        subprocess.run([venv_python, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    if os.path.exists('.env'):
        print("✅ .env file already exists")
        return True
    
    if os.path.exists('.env.example'):
        try:
            shutil.copy('.env.example', '.env')
            print("✅ Created .env file from template")
            print("⚠️  Please edit .env file with your API credentials")
            return True
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
            return False
    else:
        print("❌ .env.example template not found")
        return False

def test_installation():
    """Test if the installation works"""
    venv_python = os.path.join('venv', 'bin', 'python')
    if os.name == 'nt':  # Windows
        venv_python = os.path.join('venv', 'Scripts', 'python.exe')
    
    try:
        print("🧪 Testing installation...")
        result = subprocess.run([
            venv_python, '-c', 
            'from youtube_to_spotify import TitleParser; print("Import successful")'
        ], capture_output=True, text=True, check=True)
        print("✅ Installation test passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation test failed: {e}")
        return False

def print_next_steps():

    print("\n" + "="*60)
    print("[SETUP COMPLETE]")
    print("="*60)
    print("\nNext steps:")
    print("1. Edit the .env file with your API credentials:")
    print("   - YouTube Data API v3 key")
    print("   - Spotify Client ID and Secret")
    print("   - Your Spotify username")
    print("\n2. Activate the virtual environment:")
    if os.name == 'nt':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("\n3. Run the migration tool:")
    print("   python youtube_to_spotify.py")
    print("\n4. Or try the demo:")
    print("   python example_usage.py")
    print("\nFor detailed setup instructions, see README.md")
    print("="*60)

def main():
    """Main setup function"""
    print("YouTube to Spotify Migration Tool - Setup")
    print("="*50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Create virtual environment
    if not create_virtual_environment():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Create .env file
    if not create_env_file():
        return False
    
    # Test installation
    if not test_installation():
        return False
    
    # Print next steps
    print_next_steps()
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
