import urllib.request
import urllib.error
import json
import sys

def seed_user():
    url = "http://localhost:8000/api/v1/auth/seed-user"
    payload = {
        "email": "admin@jwhd.com",
        "password": "password123",
        "full_name": "Admin User",
        "role": "attorney"
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status in (200, 201):
                print("Success! User created. Login with: Email: admin@jwhd.com, Password: password123")
            else:
                print(f"Unexpected status code: {response.status}")
                print(response.read().decode('utf-8'))
                
    except urllib.error.URLError as e:
        if hasattr(e, 'reason'):
             print("Error: Could not connect to backend. Make sure the backend server is running on port 8000.")
        elif hasattr(e, 'code'):
            error_body = e.read().decode('utf-8')
            if e.code == 400 and "User with this email already exists" in error_body:
                print("User already exists. Login with: Email: admin@jwhd.com, Password: password123")
            else:
                print(f"Error {e.code}: {error_body}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    seed_user()