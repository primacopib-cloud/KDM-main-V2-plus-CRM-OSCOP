import os
from datetime import datetime, timezone
os.environ.setdefault('MONGO_URL','mongodb://mock:27017')
os.environ.setdefault('DB_NAME','kdm_test')
os.environ.setdefault('JWT_SECRET_KEY','kdmarche-oscop-b2b-ess-secret-key-2025')
os.environ.setdefault('STRIPE_SECRET_KEY','sk_test_dummy')

from mongomock_motor import AsyncMongoMockClient
import motor.motor_asyncio
_SHARED_MONGO_CLIENT = AsyncMongoMockClient()
class SingletonAsyncMongoMockClient:
    def __new__(cls, *args, **kwargs):
        return _SHARED_MONGO_CLIENT
motor.motor_asyncio.AsyncIOMotorClient = SingletonAsyncMongoMockClient

from auth import get_password_hash
import server
from server import app, db

# Test admin password is configurable via env so it isn't hard-coded.
_TEST_ADMIN_PASSWORD = os.environ.get('TEST_ADMIN_PASSWORD', 'AdminKDM2025!')


@app.on_event('startup')
async def seed_test_users_and_data():
    # ensure admin user required by tests
    existing = await db.users.find_one({'email': 'admin@kdmarche-oscop.fr'})
    if not existing:
        now = datetime.now(timezone.utc)
        await db.users.insert_one({
            'id': 'admin-test-id',
            'email': 'admin@kdmarche-oscop.fr',
            'password_hash': get_password_hash(_TEST_ADMIN_PASSWORD),
            'company_name': 'KDM Admin',
            'siret': '00000000000000',
            'contact_name': 'Admin',
            'phone': '0590000000',
            'subscription': 'ess-impact-pro',
            'credits': 10000,
            'is_admin': True,
            'role': 'admin',
            'created_at': now,
            'updated_at': now,
        })


# V2 deterministic project seed
@app.on_event('startup')
async def seed_v2_kdm_lolodrive_data():
    from test_seed import seed_test_database
    await seed_test_database(db)
