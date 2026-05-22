"""
Test suite for Favorites API endpoints
Tests: GET/POST/DELETE /api/user-prefs/favorites, toggle, clear all
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials (loaded from env / .env.test — never hard-code prod values)
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@kdmarche-oscop.fr")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "AdminKDM2025!")

# Test product ID (Riz long grain 5kg)
TEST_PRODUCT_ID = "a497f8dd-f948-4631-8783-3750659b27b5"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    # API returns access_token, not token
    token = data.get("access_token") or data.get("token")
    assert token, "No token in login response"
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }


class TestFavoritesAPIAuth:
    """Test authentication requirements for favorites endpoints"""
    
    def test_get_favorites_requires_auth(self):
        """GET /api/user-prefs/favorites should require authentication"""
        response = requests.get(f"{BASE_URL}/api/user-prefs/favorites")
        assert response.status_code == 401
        
    def test_get_favorite_ids_requires_auth(self):
        """GET /api/user-prefs/favorites/ids should require authentication"""
        response = requests.get(f"{BASE_URL}/api/user-prefs/favorites/ids")
        assert response.status_code == 401
        
    def test_add_favorite_requires_auth(self):
        """POST /api/user-prefs/favorites/{id} should require authentication"""
        response = requests.post(f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}")
        assert response.status_code == 401
        
    def test_remove_favorite_requires_auth(self):
        """DELETE /api/user-prefs/favorites/{id} should require authentication"""
        response = requests.delete(f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}")
        assert response.status_code == 401
        
    def test_toggle_favorite_requires_auth(self):
        """POST /api/user-prefs/favorites/{id}/toggle should require authentication"""
        response = requests.post(f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}/toggle")
        assert response.status_code == 401
        
    def test_clear_favorites_requires_auth(self):
        """DELETE /api/user-prefs/favorites should require authentication"""
        response = requests.delete(f"{BASE_URL}/api/user-prefs/favorites")
        assert response.status_code == 401


class TestFavoritesAPICRUD:
    """Test CRUD operations for favorites"""
    
    def test_get_favorites_empty_or_list(self, auth_headers):
        """GET /api/user-prefs/favorites should return favorites list"""
        response = requests.get(
            f"{BASE_URL}/api/user-prefs/favorites",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "favorites" in data
        assert "total" in data
        assert isinstance(data["favorites"], list)
        assert isinstance(data["total"], int)
        
    def test_get_favorite_ids_lightweight(self, auth_headers):
        """GET /api/user-prefs/favorites/ids should return only IDs"""
        response = requests.get(
            f"{BASE_URL}/api/user-prefs/favorites/ids",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "product_ids" in data
        assert "count" in data
        assert isinstance(data["product_ids"], list)
        
    def test_add_favorite_valid_product(self, auth_headers):
        """POST /api/user-prefs/favorites/{id} should add product to favorites"""
        # First clear any existing favorites
        requests.delete(f"{BASE_URL}/api/user-prefs/favorites", headers=auth_headers)
        
        response = requests.post(
            f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == TEST_PRODUCT_ID
        assert data["is_favorite"] == True
        assert "message" in data
        
    def test_add_favorite_duplicate(self, auth_headers):
        """POST /api/user-prefs/favorites/{id} should handle duplicate gracefully"""
        # Add same product again
        response = requests.post(
            f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_favorite"] == True
        assert "déjà" in data["message"].lower() or "already" in data["message"].lower()
        
    def test_add_favorite_invalid_product(self, auth_headers):
        """POST /api/user-prefs/favorites/{id} should return 404 for invalid product"""
        response = requests.post(
            f"{BASE_URL}/api/user-prefs/favorites/invalid-product-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404
        
    def test_verify_favorite_in_list(self, auth_headers):
        """GET /api/user-prefs/favorites should include added product"""
        response = requests.get(
            f"{BASE_URL}/api/user-prefs/favorites",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        product_ids = [f["product_id"] for f in data["favorites"]]
        assert TEST_PRODUCT_ID in product_ids
        
    def test_verify_favorite_in_ids(self, auth_headers):
        """GET /api/user-prefs/favorites/ids should include added product"""
        response = requests.get(
            f"{BASE_URL}/api/user-prefs/favorites/ids",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert TEST_PRODUCT_ID in data["product_ids"]
        
    def test_favorites_include_product_details(self, auth_headers):
        """GET /api/user-prefs/favorites should include product details"""
        response = requests.get(
            f"{BASE_URL}/api/user-prefs/favorites?include_details=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find our test product
        test_fav = next((f for f in data["favorites"] if f["product_id"] == TEST_PRODUCT_ID), None)
        assert test_fav is not None, "Test product not found in favorites"
        
        # Check product details are included
        assert "product_name" in test_fav
        assert "added_at" in test_fav
        # product_sku, product_image, product_price_ht are optional
        
    def test_remove_favorite(self, auth_headers):
        """DELETE /api/user-prefs/favorites/{id} should remove from favorites"""
        response = requests.delete(
            f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == TEST_PRODUCT_ID
        assert data["is_favorite"] == False
        
    def test_verify_favorite_removed(self, auth_headers):
        """GET /api/user-prefs/favorites/ids should not include removed product"""
        response = requests.get(
            f"{BASE_URL}/api/user-prefs/favorites/ids",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert TEST_PRODUCT_ID not in data["product_ids"]
        
    def test_remove_nonexistent_favorite(self, auth_headers):
        """DELETE /api/user-prefs/favorites/{id} should handle non-favorite gracefully"""
        response = requests.delete(
            f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_favorite"] == False


class TestFavoritesToggle:
    """Test toggle functionality"""
    
    def test_toggle_add_favorite(self, auth_headers):
        """POST /api/user-prefs/favorites/{id}/toggle should add if not present"""
        # First ensure it's not in favorites
        requests.delete(f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}", headers=auth_headers)
        
        response = requests.post(
            f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}/toggle",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == TEST_PRODUCT_ID
        assert data["is_favorite"] == True
        
    def test_toggle_remove_favorite(self, auth_headers):
        """POST /api/user-prefs/favorites/{id}/toggle should remove if present"""
        response = requests.post(
            f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}/toggle",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == TEST_PRODUCT_ID
        assert data["is_favorite"] == False
        
    def test_toggle_add_again(self, auth_headers):
        """POST /api/user-prefs/favorites/{id}/toggle should add again after removal"""
        response = requests.post(
            f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}/toggle",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_favorite"] == True
        
    def test_toggle_invalid_product(self, auth_headers):
        """POST /api/user-prefs/favorites/{id}/toggle should return 404 for invalid product"""
        response = requests.post(
            f"{BASE_URL}/api/user-prefs/favorites/invalid-product-xyz/toggle",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestFavoritesClearAll:
    """Test clear all favorites functionality"""
    
    def test_clear_all_favorites(self, auth_headers):
        """DELETE /api/user-prefs/favorites should clear all favorites"""
        # First add a favorite to ensure there's something to clear
        requests.post(
            f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}",
            headers=auth_headers
        )
        
        response = requests.delete(
            f"{BASE_URL}/api/user-prefs/favorites",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
    def test_verify_all_cleared(self, auth_headers):
        """GET /api/user-prefs/favorites should return empty after clear"""
        response = requests.get(
            f"{BASE_URL}/api/user-prefs/favorites/ids",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert len(data["product_ids"]) == 0


class TestFavoritesResponseStructure:
    """Test response structure and data types"""
    
    def test_favorites_response_structure(self, auth_headers):
        """Verify FavoritesResponse structure"""
        # Add a favorite first
        requests.post(
            f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}",
            headers=auth_headers
        )
        
        response = requests.get(
            f"{BASE_URL}/api/user-prefs/favorites",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level structure
        assert "favorites" in data
        assert "total" in data
        assert isinstance(data["total"], int)
        
        if len(data["favorites"]) > 0:
            fav = data["favorites"][0]
            # Check FavoriteItem structure
            assert "product_id" in fav
            assert "added_at" in fav
            # Optional fields
            assert "product_name" in fav or fav.get("product_name") is None
            
    def test_toggle_response_structure(self, auth_headers):
        """Verify FavoriteToggleResponse structure"""
        response = requests.post(
            f"{BASE_URL}/api/user-prefs/favorites/{TEST_PRODUCT_ID}/toggle",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check FavoriteToggleResponse structure
        assert "product_id" in data
        assert "is_favorite" in data
        assert "message" in data
        assert isinstance(data["is_favorite"], bool)
        
    def test_cleanup(self, auth_headers):
        """Cleanup: Clear all favorites after tests"""
        requests.delete(f"{BASE_URL}/api/user-prefs/favorites", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
