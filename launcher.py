#!/usr/bin/env python3
"""
Lalal AI Voice Cleaner - Launcher
Choose between API and Desktop integration modes
"""

import sys
import subprocess
import os

def main():
    print("=" * 60)
    print("Lalal AI Voice Cleaner - Launcher")
    print("=" * 60)
    print()
    print("Choose your integration mode:")
    print("1. Desktop Integration (uses activation ID)")
    print("2. API Integration (uses license key)")
    print("3. Exit")
    print()
    
    while True:
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            print("\n🖥️  Launching Desktop Integration Mode...")
            print("This mode works with your Lalal AI desktop application")
            print("and activation ID.\n")
            subprocess.run([sys.executable, "main_desktop.py"])
            break
            
        elif choice == "2":
            print("\n🔌 Launching API Integration Mode...")
            print("This mode requires a Lalal AI API license key.")
            print("Get one at: https://www.lalal.ai/api/\n")
            subprocess.run([sys.executable, "main.py"])
            break
            
        elif choice == "3":
            print("\n👋 Goodbye!")
            break
            
        else:
            print("\n❌ Invalid choice. Please enter 1, 2, or 3.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()