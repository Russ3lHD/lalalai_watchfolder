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
    
    # Prefer v1 license/auth validation using voice_packs/list/ (returns 200 for valid keys)
    try:
        headers = { 'X-License-Key': license_key }
        response = requests.post(
            "https://www.lalal.ai/api/v1/voice_packs/list/",
            json={},
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json() or {}
            packs = data.get('packs', [])
            print("✅ License key appears valid (voice_packs/list returned 200)")
            print(f"   Available voice packs: {len(packs)}")
            return True

        # Fallback: try legacy billing endpoint if present
        if response.status_code in (401, 403):
            print(f"❌ Authentication failed: {response.status_code}")
            return False

        # Legacy fallback (some older accounts may still be validated via billing endpoint)
        response = requests.get(
            "https://www.lalal.ai/billing/get-limits/",
            params={'key': license_key},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print("✅ License key is valid (legacy billing response)!")
                print(f"   Plan: {result.get('option', 'Unknown')}")
                print(f"   Email: {result.get('email', 'Unknown')}")
                print(f"   Total minutes: {result.get('process_duration_limit', 0):.1f}")
                print(f"   Used minutes: {result.get('process_duration_used', 0):.1f}")
                print(f"   Remaining: {result.get('process_duration_left', 0):.1f} minutes")
                return True

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