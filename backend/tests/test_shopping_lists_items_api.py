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


class TestShoppingListItems:
    """Test item management within shopping lists"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth and test list for each test"""
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
        
        # Create a test list
        unique_name = f"TEST_ItemsList_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json={"name": unique_name, "frequency": "weekly"}
        )
        if create_response.status_code != 200:
            pytest.skip(f"Failed to create test list: {create_response.text}")
        self.test_list_id = create_response.json()["id"]
        
        yield
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-lists/{self.test_list_id}", headers=self.headers)
    
    def test_add_item_to_list(self):
        """POST /api/shopping-lists/{id}/items - Add product to list"""
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/items",
            headers=self.headers,
            json={
                "product_id": TEST_PRODUCT_ID,
                "quantity": 2,
                "notes": "Test note"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["items_count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == TEST_PRODUCT_ID
        assert data["items"][0]["quantity"] == 2
        assert data["items"][0]["notes"] == "Test note"
        
        print("✓ Add item to list works")
    
    def test_add_item_increments_quantity_if_exists(self):
        """POST /api/shopping-lists/{id}/items - Adding existing product increments quantity"""
        # Add item first time
        requests.post(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/items",
            headers=self.headers,
            json={"product_id": TEST_PRODUCT_ID, "quantity": 2}
        )
        
        # Add same item again
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/items",
            headers=self.headers,
            json={"product_id": TEST_PRODUCT_ID, "quantity": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still be 1 item but with quantity 5
        assert data["items_count"] == 1
        assert data["items"][0]["quantity"] == 5
        
        print("✓ Adding existing product increments quantity")
    
    def test_add_nonexistent_product_fails(self):
        """POST /api/shopping-lists/{id}/items - Non-existent product returns 404"""
        fake_product_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/items",
            headers=self.headers,
            json={"product_id": fake_product_id, "quantity": 1}
        )
        
        assert response.status_code == 404
        print("✓ Adding non-existent product returns 404")
    
    def test_update_item_quantity(self):
        """PATCH /api/shopping-lists/{id}/items/{product_id} - Update item quantity"""
        # Add item first
        requests.post(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/items",
            headers=self.headers,
            json={"product_id": TEST_PRODUCT_ID, "quantity": 2}
        )
        
        # Update quantity
        response = requests.patch(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/items/{TEST_PRODUCT_ID}",
            headers=self.headers,
            json={"quantity": 10, "notes": "Updated note"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["items"][0]["quantity"] == 10
        assert data["items"][0]["notes"] == "Updated note"
        
        print("✓ Update item quantity works")
    
    def test_update_nonexistent_item_fails(self):
        """PATCH /api/shopping-lists/{id}/items/{product_id} - Non-existent item returns 404"""
        fake_product_id = str(uuid.uuid4())
        response = requests.patch(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/items/{fake_product_id}",
            headers=self.headers,
            json={"quantity": 5}
        )
        
        assert response.status_code == 404
        print("✓ Update non-existent item returns 404")
    
    def test_remove_item_from_list(self):
        """DELETE /api/shopping-lists/{id}/items/{product_id} - Remove item from list"""
        # Add item first
        requests.post(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/items",
            headers=self.headers,
            json={"product_id": TEST_PRODUCT_ID, "quantity": 2}
        )
        
        # Remove item
        response = requests.delete(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/items/{TEST_PRODUCT_ID}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        assert response.json()["product_id"] == TEST_PRODUCT_ID
        
        # Verify removal
        get_response = requests.get(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}",
            headers=self.headers
        )
        assert get_response.json()["items_count"] == 0
        
        print("✓ Remove item from list works")
    
    def test_remove_nonexistent_item_fails(self):
        """DELETE /api/shopping-lists/{id}/items/{product_id} - Non-existent item returns 404"""
        fake_product_id = str(uuid.uuid4())
        response = requests.delete(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/items/{fake_product_id}",
            headers=self.headers
        )
        
        assert response.status_code == 404
        print("✓ Remove non-existent item returns 404")


class TestShoppingListActions:
    """Test special actions on shopping lists"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth and test list with items for each test"""
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
        
        # Create a test list with items
        unique_name = f"TEST_ActionsList_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json={
                "name": unique_name,
                "frequency": "monthly",
                "items": [{"product_id": TEST_PRODUCT_ID, "quantity": 3}]
            }
        )
        if create_response.status_code != 200:
            pytest.skip(f"Failed to create test list: {create_response.text}")
        self.test_list_id = create_response.json()["id"]
        self.created_lists = [self.test_list_id]
        
        yield
        
        # Cleanup all created lists
        for list_id in self.created_lists:
            requests.delete(f"{BASE_URL}/api/shopping-lists/{list_id}", headers=self.headers)
    
    def test_use_shopping_list(self):
        """POST /api/shopping-lists/{id}/use - Mark list as used"""
        # Get initial use_count
        get_response = requests.get(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}",
            headers=self.headers
        )
        initial_use_count = get_response.json().get("use_count", 0)
        
        # Use the list
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/use",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["list_id"] == self.test_list_id
        assert "items" in data
        assert data["items_count"] == 1
        
        # Verify use_count incremented
        get_response2 = requests.get(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}",
            headers=self.headers
        )
        assert get_response2.json()["use_count"] == initial_use_count + 1
        assert get_response2.json()["last_used_at"] is not None
        
        print("✓ Use list works and increments counter")
    
    def test_use_nonexistent_list_fails(self):
        """POST /api/shopping-lists/{id}/use - Non-existent list returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists/{fake_id}/use",
            headers=self.headers
        )
        
        assert response.status_code == 404
        print("✓ Use non-existent list returns 404")
    
    def test_duplicate_shopping_list(self):
        """POST /api/shopping-lists/{id}/duplicate - Duplicate a list"""
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/duplicate",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Track for cleanup
        self.created_lists.append(data["id"])
        
        # Should be a new list
        assert data["id"] != self.test_list_id
        assert "(copie)" in data["name"]
        
        # Should have same items
        assert data["items_count"] == 1
        assert data["items"][0]["product_id"] == TEST_PRODUCT_ID
        
        # Should reset counters
        assert data["use_count"] == 0
        assert data["last_used_at"] is None
        
        print(f"✓ Duplicate list works: {data['id']}")
    
    def test_duplicate_with_custom_name(self):
        """POST /api/shopping-lists/{id}/duplicate?new_name=X - Duplicate with custom name"""
        custom_name = f"TEST_CustomDuplicate_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists/{self.test_list_id}/duplicate?new_name={custom_name}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Track for cleanup
        self.created_lists.append(data["id"])
        
        assert data["name"] == custom_name
        
        print("✓ Duplicate with custom name works")
    
    def test_duplicate_nonexistent_list_fails(self):
        """POST /api/shopping-lists/{id}/duplicate - Non-existent list returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists/{fake_id}/duplicate",
            headers=self.headers
        )
        
        assert response.status_code == 404
        print("✓ Duplicate non-existent list returns 404")


class TestFrequencyOptions:
    """Test frequency options endpoint"""
    
    def test_get_frequency_options(self):
        """GET /api/shopping-lists/options/frequencies - Get available frequencies"""
        # This endpoint might not require auth
        response = requests.get(f"{BASE_URL}/api/shopping-lists/options/frequencies")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "frequencies" in data
        frequencies = data["frequencies"]
        
        # Check all expected frequencies are present
        expected_values = ["weekly", "biweekly", "monthly", "quarterly", "one_time", "custom"]
        actual_values = [f["value"] for f in frequencies]
        
        for expected in expected_values:
            assert expected in actual_values, f"Missing frequency: {expected}"
        
        # Check structure of each frequency option
        for freq in frequencies:
            assert "value" in freq
            assert "label" in freq
            assert "icon" in freq
            assert "description" in freq
        
        print(f"✓ Frequency options endpoint returns {len(frequencies)} options")


class TestAllFrequencies:
    """Test creating lists with all frequency types"""
    
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
    
    @pytest.mark.parametrize("frequency", [
        "weekly", "biweekly", "monthly", "quarterly", "one_time", "custom"
    ])
    def test_create_list_with_frequency(self, frequency):
        """Test creating lists with each frequency type"""
        unique_name = f"TEST_{frequency}_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/shopping-lists",
            headers=self.headers,
            json={"name": unique_name, "frequency": frequency}
        )
        
        assert response.status_code == 200, f"Failed for frequency {frequency}: {response.text}"
        data = response.json()
        assert data["frequency"] == frequency
        
        print(f"✓ Created list with frequency: {frequency}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/shopping-lists/{data['id']}", headers=self.headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
