"""
Test script to verify the quarantine API is working correctly.
Run this to test the quarantine endpoint directly.
"""

import requests
import json
import sys

def test_quarantine_api(user_id, base_url="http://localhost:8000"):
    """Test the quarantine API endpoint"""
    url = f"{base_url}/api/quarantine-user/"
    
    payload = {
        "user_id": user_id
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"\n{'='*60}")
    print(f"Testing Quarantine API")
    print(f"{'='*60}\n")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"\nSending request...\n")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"\nResponse Body:")
        try:
            response_data = response.json()
            print(json.dumps(response_data, indent=2))
            
            if response.status_code == 200 and response_data.get('status') == 'success':
                print(f"\n{'='*60}")
                print("✓ SUCCESS: Quarantine API is working!")
                print(f"{'='*60}\n")
                print(f"User ID {user_id} has been quarantined:")
                print(f"  - Sessions deleted: {response_data.get('sessions_deleted', 0)}")
                print(f"  - Account active: {response_data.get('account_now_active', 'unknown')}")
                return True
            else:
                print(f"\n{'='*60}")
                print("✗ ERROR: Quarantine API returned an error")
                print(f"{'='*60}\n")
                print(f"Error message: {response_data.get('message', 'Unknown error')}")
                return False
                
        except json.JSONDecodeError:
            print(f"Response (not JSON): {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n{'='*60}")
        print("✗ ERROR: Cannot connect to server")
        print(f"{'='*60}\n")
        print(f"Make sure Django server is running at {base_url}")
        print(f"Or update the base_url parameter")
        return False
    except requests.exceptions.Timeout:
        print(f"\n{'='*60}")
        print("✗ ERROR: Request timed out")
        print(f"{'='*60}\n")
        return False
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"✗ ERROR: {str(e)}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_quarantine_api.py <user_id> [base_url]")
        print("\nExample:")
        print("  python test_quarantine_api.py 1")
        print("  python test_quarantine_api.py 1 http://host.docker.internal:8000")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    base_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    
    success = test_quarantine_api(user_id, base_url)
    sys.exit(0 if success else 1)
