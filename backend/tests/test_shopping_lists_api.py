"""
Shopping Lists API Tests
Tests for the shopping lists feature allowing buyers to organize recurring orders
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials (loaded from env / .env.test — never hard-code prod values)
TEST_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@kdmarche-oscop.fr")
TEST_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "AdminKDM2025!")

# Test product ID (resolved dynamically from DB; env override supported)
def _first_product_id():
    try:
        from pymongo import MongoClient
        from dotenv import load_dotenv
        load_dotenv('/app/backend/.env')
        c = MongoClient(os.environ['MONGO_URL'])
        p = c[os.environ['DB_NAME']].products.find_one({}, {"id": 1})
        return p["id"] if p else "missing-product"
    except Exception:
        return "missing-product"

TEST_PRODUCT_ID = os.environ.get("TEST_PRODUCT_ID") or _first_product_id()


class TestShoppingListsAuth:
    """Test authentication requirements for shopping lists endpoints"""
    
    def test_get_lists_requires_auth(self):
        """GET /api/shopping-lists should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/shopping-lists")
        assert response.status_code == 401
        print("✓ GET /api/shopping-lists returns 401 without auth")
    
    def test_create_list_requires_auth(self):
        """POST /api/shopping-lists should return 401 without auth"""
        response = requests.post(f"{BASE_URL}/api/shopping-lists", json={
            "name": "Test List",
            "frequency": "weekly"
        })
        assert response.status_code == 401
        print("✓ POST /api/shopping-lists returns 401 without auth")
    
    def test_get_single_list_requires_auth(self):
        """GET /api/shopping-lists/{id} should return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/shopping-lists/some-id")
        assert response.status_code == 401
        print("✓ GET /api/shopping-lists/{id} returns 401 without auth")


class TestShoppingListsCRUD:
    """Test CRUD operations for shopping lists"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth for each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Authentication failed: {response.status_code}")
        self.token = response.json().get("access_token")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
    
    def test_create_shopping_list(self):
        """POST /api/shopping-lists - Create a new shopping list"""
        unique_name = f"TEST_Liste_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": unique_name,
            "description": "Test list for automated testing",
            "frequency": "weekly",
            "color": "#57D19A"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "id" in data
        assert data["name"] == unique_name
        assert data["description"] == payload["description"]
        assert data["frequency"] == "weekly"
        assert data["color"] == "#57D19A"
        assert data["items_count"] == 0
        assert data["use_count"] == 0
        assert "created_at" in data
        assert "updated_at" in data
        
        print(f"✓ Created shopping list: {data['id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-lists/{data['id']}", headers=self.headers)
    
    def test_create_list_with_items(self):
        """POST /api/shopping-lists - Create list with initial items"""
        unique_name = f"TEST_ListeAvecProduits_{uuid.uuid4().hex[:8]}"
        payload = {
            "name": unique_name,
            "frequency": "monthly",
            "items": [
                {"product_id": TEST_PRODUCT_ID, "quantity": 5}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["items_count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == TEST_PRODUCT_ID
        assert data["items"][0]["quantity"] == 5
        
        print(f"✓ Created shopping list with items: {data['id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-lists/{data['id']}", headers=self.headers)
    
    def test_create_list_duplicate_name_fails(self):
        """POST /api/shopping-lists - Duplicate name should fail"""
        unique_name = f"TEST_DuplicateName_{uuid.uuid4().hex[:8]}"
        
        # Create first list
        response1 = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json={"name": unique_name, "frequency": "weekly"}
        )
        assert response1.status_code == 200
        list_id = response1.json()["id"]
        
        # Try to create second list with same name
        response2 = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json={"name": unique_name, "frequency": "monthly"}
        )
        assert response2.status_code == 400
        assert "existe déjà" in response2.json().get("detail", "")
        
        print("✓ Duplicate name correctly rejected")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-lists/{list_id}", headers=self.headers)
    
    def test_get_shopping_lists(self):
        """GET /api/shopping-lists - Get all shopping lists"""
        response = requests.get(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        print(f"✓ GET /api/shopping-lists returned {len(data)} lists")
    
    def test_get_shopping_lists_with_frequency_filter(self):
        """GET /api/shopping-lists?frequency=weekly - Filter by frequency"""
        # Create a weekly list
        unique_name = f"TEST_WeeklyFilter_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json={"name": unique_name, "frequency": "weekly"}
        )
        assert create_response.status_code == 200
        list_id = create_response.json()["id"]
        
        # Filter by weekly
        response = requests.get(
            f"{BASE_URL}/api/shopping-lists?frequency=weekly",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned lists should be weekly
        for lst in data:
            assert lst["frequency"] == "weekly"
        
        print(f"✓ Frequency filter works - returned {len(data)} weekly lists")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-lists/{list_id}", headers=self.headers)
    
    def test_get_shopping_lists_with_sort(self):
        """GET /api/shopping-lists?sort_by=name&sort_order=asc - Sort lists"""
        response = requests.get(
            f"{BASE_URL}/api/shopping-lists?sort_by=name&sort_order=asc",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify sorting (if multiple lists exist)
        if len(data) > 1:
            names = [lst["name"] for lst in data]
            assert names == sorted(names), "Lists should be sorted by name ascending"
        
        print("✓ Sort by name works")
    
    def test_get_single_shopping_list(self):
        """GET /api/shopping-lists/{id} - Get single list with details"""
        # Create a list first
        unique_name = f"TEST_SingleGet_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json={
                "name": unique_name,
                "description": "Test description",
                "frequency": "monthly",
                "items": [{"product_id": TEST_PRODUCT_ID, "quantity": 3}]
            }
        )
        assert create_response.status_code == 200
        list_id = create_response.json()["id"]
        
        # Get the list
        response = requests.get(
            f"{BASE_URL}/api/shopping-lists/{list_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate full response
        assert data["id"] == list_id
        assert data["name"] == unique_name
        assert data["description"] == "Test description"
        assert data["frequency"] == "monthly"
        assert data["items_count"] == 1
        assert len(data["items"]) == 1
        
        # Check enriched product data
        item = data["items"][0]
        assert item["product_id"] == TEST_PRODUCT_ID
        assert item["quantity"] == 3
        # Product should be enriched with name, sku, etc.
        assert "product_name" in item
        
        print("✓ GET single list works with enriched product data")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-lists/{list_id}", headers=self.headers)
    
    def test_get_nonexistent_list_returns_404(self):
        """GET /api/shopping-lists/{id} - Non-existent list returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/shopping-lists/{fake_id}",
            headers=self.headers
        )
        
        assert response.status_code == 404
        print("✓ Non-existent list returns 404")
    
    def test_update_shopping_list(self):
        """PATCH /api/shopping-lists/{id} - Update list metadata"""
        # Create a list
        unique_name = f"TEST_Update_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json={"name": unique_name, "frequency": "weekly"}
        )
        assert create_response.status_code == 200
        list_id = create_response.json()["id"]
        
        # Update the list
        new_name = f"TEST_Updated_{uuid.uuid4().hex[:8]}"
        update_response = requests.patch(
            f"{BASE_URL}/api/shopping-lists/{list_id}",
            headers=self.headers,
            json={
                "name": new_name,
                "description": "Updated description",
                "frequency": "monthly",
                "color": "#8B5CF6"
            }
        )
        
        assert update_response.status_code == 200
        data = update_response.json()
        
        assert data["name"] == new_name
        assert data["description"] == "Updated description"
        assert data["frequency"] == "monthly"
        assert data["color"] == "#8B5CF6"
        
        # Verify persistence with GET
        get_response = requests.get(
            f"{BASE_URL}/api/shopping-lists/{list_id}",
            headers=self.headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["name"] == new_name
        
        print("✓ PATCH update works and persists")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-lists/{list_id}", headers=self.headers)
    
    def test_delete_shopping_list(self):
        """DELETE /api/shopping-lists/{id} - Delete a list"""
        # Create a list
        unique_name = f"TEST_Delete_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json={"name": unique_name, "frequency": "weekly"}
        )
        assert create_response.status_code == 200
        list_id = create_response.json()["id"]
        
        # Delete the list
        delete_response = requests.delete(
            f"{BASE_URL}/api/shopping-lists/{list_id}",
            headers=self.headers
        )
        
        assert delete_response.status_code == 200
        assert delete_response.json()["id"] == list_id
        
        # Verify deletion with GET
        get_response = requests.get(
            f"{BASE_URL}/api/shopping-lists/{list_id}",
            headers=self.headers
        )
        assert get_response.status_code == 404
        
        print("✓ DELETE works and list is removed")
    
    def test_delete_nonexistent_list_returns_404(self):
        """DELETE /api/shopping-lists/{id} - Non-existent list returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(
            f"{BASE_URL}/api/shopping-lists/{fake_id}",
            headers=self.headers
        )
        
        assert response.status_code == 404
        print("✓ DELETE non-existent list returns 404")


