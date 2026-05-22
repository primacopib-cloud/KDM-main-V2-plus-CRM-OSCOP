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

# Test product ID (from previous tests)
TEST_PRODUCT_ID = "a497f8dd-f948-4631-8783-3750659b27b5"


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
