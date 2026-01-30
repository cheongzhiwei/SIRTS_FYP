"""
Test script to verify the workflow is receiving correct data from Django.
This simulates what n8n receives and helps debug workflow issues.
"""

import requests
import json
import sys
from datetime import datetime

def test_workflow_data(base_url="http://localhost:8000", n8n_webhook_url=None):
    """Test what data Django sends to n8n webhook"""
    
    # Default n8n webhook URL (update this to match your n8n setup)
    if not n8n_webhook_url:
        n8n_webhook_url = f"{base_url}/webhook-test/new-incident"
    
    print(f"\n{'='*70}")
    print(f"Testing Workflow Data from Django")
    print(f"{'='*70}\n")
    print(f"Django Base URL: {base_url}")
    print(f"n8n Webhook URL: {n8n_webhook_url}")
    print(f"\nThis script simulates the payload Django sends to n8n.\n")
    
    # Sample payload that Django sends (based on views.py)
    sample_payload = {
        "ticket_id": 123,
        "title": "Test Incident",
        "department": "IT",
        "laptop_serial": "SN123456",
        "reported_by": "testuser",
        "reported_by_id": 3,  # User ID
        "user_id": 3,  # Alternative field name
        "file_hash": "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f",
        "file_url": f"{base_url}/media/incident_attachments/test_file.pdf"
    }
    
    print("Sample Payload Structure:")
    print(json.dumps(sample_payload, indent=2))
    
    print(f"\n{'='*70}")
    print("Expected n8n Workflow Data Structure:")
    print(f"{'='*70}\n")
    print("When n8n receives this via webhook, the data structure will be:")
    print(json.dumps({
        "body": sample_payload
    }, indent=2))
    
    print(f"\n{'='*70}")
    print("n8n Expression Examples:")
    print(f"{'='*70}\n")
    print("To access data in n8n, use these expressions:")
    print(f"  - User ID: {{ $json.body.user_id }}")
    print(f"  - Reported By ID: {{ $json.body.reported_by_id }}")
    print(f"  - File Hash: {{ $json.body.file_hash }}")
    print(f"  - File URL: {{ $json.body.file_url }}")
    print(f"  - Ticket ID: {{ $json.body.ticket_id }}")
    
    print(f"\n{'='*70}")
    print("Testing Actual Webhook (if n8n is configured):")
    print(f"{'='*70}\n")
    
    try:
        print(f"Sending test payload to: {n8n_webhook_url}")
        response = requests.post(n8n_webhook_url, json=sample_payload, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code in [200, 201]:
            print("\n✓ Webhook is accessible and responding")
        else:
            print(f"\n⚠ Webhook returned status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to webhook at {n8n_webhook_url}")
        print("  This is normal if n8n is not running or webhook is not configured")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    print(f"\n{'='*70}")
    print("Verification Checklist:")
    print(f"{'='*70}\n")
    print("In your n8n workflow, verify:")
    print("  [ ] Webhook node receives data with 'body' property")
    print("  [ ] 'body.user_id' contains numeric user ID (not username)")
    print("  [ ] 'body.reported_by_id' contains numeric user ID")
    print("  [ ] 'body.file_hash' contains SHA256 hash (64 hex characters)")
    print("  [ ] 'body.file_url' contains accessible file URL")
    print("  [ ] 'body.ticket_id' contains numeric ticket ID")
    
    print(f"\n{'='*70}")
    print("Common Issues:")
    print(f"{'='*70}\n")
    print("1. If user_id is missing:")
    print("   → Check Django views.py report_incident() function")
    print("   → Verify 'user_id' and 'reported_by_id' are in payload")
    print()
    print("2. If file_hash is empty:")
    print("   → Check if file was uploaded with the incident")
    print("   → Verify file_hash is calculated in Django")
    print()
    print("3. If file_url is not accessible:")
    print("   → Check EXTERNAL_BASE_URL in Django settings")
    print("   → Verify file is saved in media/incident_attachments/")
    print()
    print("4. If workflow doesn't trigger quarantine:")
    print("   → Check VirusTotal scan results")
    print("   → Verify 'malicious' count > 0 in If1 condition")
    print("   → Check quarantine API endpoint is accessible")
    
    return True

if __name__ == '__main__':
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    n8n_url = sys.argv[2] if len(sys.argv) > 2 else None
    
    test_workflow_data(base_url, n8n_url)
