#!/usr/bin/env python3
"""
Lalal AI License Key Validator
Test your license key before using the main application
"""

import requests
import sys

def validate_license_key(license_key):
    """Test if a license key is valid for Lalal AI API"""
    
    print(f"Testing license key: {license_key[:8]}...")
    print(f"Key length: {len(license_key)} characters")
    
    # Basic format validation
    if len(license_key) < 20:
        print("❌ Key is too short - Lalal AI keys are typically 40+ characters")
        return False
    
    # Test API connection
    try:
        session = requests.Session()
        session.headers.update({
            'Authorization': f'license {license_key}',
            'User-Agent': 'LalalAIVoiceCleaner/1.0.0'
        })
        
        # Test API endpoint
        response = session.head("https://www.lalal.ai/api/upload/")
        
        if response.status_code == 200:
            print("✅ License key is valid!")
            return True
        elif response.status_code == 401:
            print("❌ Invalid license key - please check your key")
            return False
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {str(e)}")
        print("Make sure you have internet connectivity")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("Lalal AI License Key Validator")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        license_key = sys.argv[1]
    else:
        license_key = input("Enter your Lalal AI license key: ").strip()
    
    if not license_key:
        print("❌ No license key provided")
        return
    
    print()
    is_valid = validate_license_key(license_key)
    print()
    
    if is_valid:
        print("🎉 Your license key is ready to use!")
        print("You can now run the main application: python main.py")
    else:
        print("📝 To get a valid license key:")
        print("1. Visit https://www.lalal.ai/api/")
        print("2. Sign up for an account")
        print("3. Purchase API credits or start a trial")
        print("4. Copy your license key from your account dashboard")

if __name__ == "__main__":
    main()