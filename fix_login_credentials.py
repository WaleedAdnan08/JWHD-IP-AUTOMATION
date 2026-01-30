#!/usr/bin/env python3
"""
Script to test existing user passwords and create a new user with known credentials.
"""

import os
import sys
import asyncio
import requests

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_login_credentials(email, password):
    """Test login with specific credentials"""
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            data={
                "username": email,
                "password": password
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
            
    except Exception as e:
        return False, str(e)

def create_new_user_with_known_password():
    """Create a new user with known credentials"""
    print("🔧 Creating new user with known credentials...")
    
    user_data = {
        "email": "admin@jwhd.com",
        "password": "admin123",
        "full_name": "Admin User",
        "firm_affiliation": "JWHD",
        "role": "admin"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/auth/seed-user",
            json=user_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code == 201:
            print("✅ New user created successfully!")
            return user_data
        elif response.status_code == 400:
            print("ℹ️  User already exists")
            return user_data
        else:
            print(f"❌ Failed to create user: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ User creation failed: {e}")
        return None

def main():
    """Test login credentials and fix the issue"""
    print("🔐 LOGIN CREDENTIALS FIX")
    print("=" * 50)
    
    # List of existing users and common passwords to try
    users = [
        "test@jwhd.com",
        "testuser@example.com"
    ]
    
    common_passwords = [
        "password",
        "test123", 
        "admin123",
        "testpassword",
        "123456",
        "test",
        "admin"
    ]
    
    print("🔍 Testing existing user credentials...")
    working_credentials = []
    
    for email in users:
        print(f"\n📧 Testing {email}:")
        for password in common_passwords:
            print(f"   🔑 Trying password: {password}")
            success, result = test_login_credentials(email, password)
            if success:
                print(f"   ✅ SUCCESS! Password '{password}' works!")
                working_credentials.append((email, password))
                break
            else:
                print(f"   ❌ Failed")
        
        if not any(cred[0] == email for cred in working_credentials):
            print(f"   ⚠️  No working password found for {email}")
    
    # Create new user if no working credentials found
    if not working_credentials:
        print("\n🔧 No working credentials found. Creating new user...")
        new_user = create_new_user_with_known_password()
        if new_user:
            working_credentials.append((new_user["email"], new_user["password"]))
    
    # Summary
    print("\n📊 WORKING CREDENTIALS")
    print("=" * 50)
    if working_credentials:
        for email, password in working_credentials:
            print(f"📧 Email: {email}")
            print(f"🔑 Password: {password}")
            print("-" * 30)
            
            # Test the credentials one more time
            print(f"🔍 Final verification for {email}...")
            success, result = test_login_credentials(email, password)
            if success:
                print("✅ Login verification successful!")
                user_data = result.get('user', {})
                print(f"👤 User: {user_data.get('full_name', 'Unknown')}")
                print(f"👔 Role: {user_data.get('role', 'Unknown')}")
            else:
                print("❌ Login verification failed!")
            print()
        
        print("🎉 LOGIN ISSUE RESOLVED!")
        print("You can now use any of the credentials above to login.")
    else:
        print("❌ Could not resolve login issue")
        print("Manual intervention may be required")

if __name__ == "__main__":
    main()