#!/usr/bin/env python3
"""
Get Garmin session token for accounts with 2FA enabled.

This script helps you authenticate with Garmin and get a session token
that can be used for automated access without re-entering 2FA codes.
"""

import getpass
import json


def get_session_with_2fa():
    """Authenticate with Garmin using email/password + 2FA."""
    from garth import Client
    
    print("=" * 60)
    print("Garmin Session Token Generator (with 2FA support)")
    print("=" * 60)
    print()
    
    email = input("Enter your Garmin email: ").strip()
    password = getpass.getpass("Enter your Garmin password: ")
    
    print()
    print("Attempting to authenticate...")
    print("(If 2FA is enabled, you'll receive a code via email/SMS)")
    print()
    
    client = Client()
    
    try:
        # Try to login - this will trigger 2FA
        client.login(email, password)
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Check if this is a 2FA prompt
        if "mfa" in error_msg or "verification" in error_msg or "code" in error_msg:
            print("2FA required! Check your email or phone for the verification code.")
            print()
            
            # Get 2FA code from user
            mfa_code = input("Enter the verification code: ").strip()
            
            try:
                # Complete 2FA
                client.login(email, password, mfa_code=mfa_code)
            except Exception as e2:
                print(f"Error completing 2FA: {e2}")
                return None
        else:
            print(f"Login error: {e}")
            return None
    
    # If we get here, login succeeded
    print()
    print("✓ Successfully authenticated with Garmin!")
    print()
    
    # Get the session token
    try:
        token = client.dumps()
        return token
    except Exception as e:
        print(f"Error getting session token: {e}")
        return None


def get_session_simple():
    """Simple approach - try basic login."""
    from garminconnect import Garmin
    
    print("=" * 60)
    print("Garmin Session Token Generator")
    print("=" * 60)
    print()
    
    email = input("Enter your Garmin email: ").strip()
    password = getpass.getpass("Enter your Garmin password: ")
    
    print()
    print("Attempting to authenticate...")
    
    try:
        client = Garmin(email, password)
        client.login()
        
        print()
        print("✓ Successfully authenticated with Garmin!")
        print()
        
        # Get the session token
        token = client.garth.dumps()
        return token
        
    except Exception as e:
        print(f"Login error: {e}")
        print()
        print("If you have 2FA enabled, try the alternative method below.")
        return None


def main():
    print()
    print("Choose authentication method:")
    print("  1. Simple (email + password only)")
    print("  2. With 2FA support")
    print()
    
    choice = input("Enter 1 or 2: ").strip()
    print()
    
    if choice == "2":
        token = get_session_with_2fa()
    else:
        token = get_session_simple()
    
    if token:
        print("=" * 60)
        print("SESSION TOKEN (copy everything below)")
        print("=" * 60)
        print()
        print(token)
        print()
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Copy the entire token above")
        print("2. Go to GitHub repo → Settings → Secrets → Actions")
        print("3. Add new secret: GARMIN_SESSION")
        print("4. Paste the token as the value")
        print()
        
        # Also save to file for convenience
        with open("garmin_session.txt", "w") as f:
            f.write(token)
        print("(Token also saved to garmin_session.txt)")
    else:
        print()
        print("Failed to get session token. Please try again.")


if __name__ == "__main__":
    main()

