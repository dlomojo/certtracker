import requests
import json

# Test configuration
API_BASE_URL = "https://6hiswqeu8e.execute-api.us-east-1.amazonaws.com/prod"

def test_auth_endpoints():
    """Test authentication endpoints"""
    
    print("🧪 Testing Auth Endpoints")
    print("=" * 40)
    
    # Test registration
    print("1. Testing user registration...")
    register_data = {
        "email": "test@example.com",
        "password": "testpass123",
        "name": "Test User"
    }
    
    response = requests.post(f"{API_BASE_URL}/auth/register", json=register_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        auth_data = response.json()
        token = auth_data['token']
        print(f"   ✅ Registration successful")
        print(f"   Token: {token[:20]}...")
    else:
        print(f"   ❌ Registration failed: {response.text}")
        return None
    
    # Test login
    print("\n2. Testing user login...")
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    response = requests.post(f"{API_BASE_URL}/auth/login", json=login_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        auth_data = response.json()
        token = auth_data['token']
        print(f"   ✅ Login successful")
        return token
    else:
        print(f"   ❌ Login failed: {response.text}")
        return None

def test_certification_endpoints(token):
    """Test certification endpoints"""
    
    print("\n🧪 Testing Certification Endpoints")
    print("=" * 40)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test creating certification
    print("1. Testing certification creation...")
    cert_data = {
        "name": "AWS Solutions Architect Associate",
        "provider": "Amazon Web Services",
        "issueDate": "2023-06-15",
        "expiryDate": "2025-06-15",
        "reminderDays": [90, 60, 30, 7]
    }
    
    response = requests.post(f"{API_BASE_URL}/certifications", json=cert_data, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        cert = response.json()
        cert_id = cert['id']
        print(f"   ✅ Certification created: {cert_id}")
    else:
        print(f"   ❌ Creation failed: {response.text}")
        return
    
    # Test getting certifications
    print("\n2. Testing certification retrieval...")
    response = requests.get(f"{API_BASE_URL}/certifications", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Retrieved {data['count']} certifications")
    else:
        print(f"   ❌ Retrieval failed: {response.text}")

if __name__ == "__main__":
    # Test auth endpoints
    token = test_auth_endpoints()
    
    if token:
        # Test certification endpoints
        test_certification_endpoints(token)
    
    print("\n🎉 API testing complete!")