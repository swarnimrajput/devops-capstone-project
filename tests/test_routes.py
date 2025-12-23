"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import json
import logging
from unittest import TestCase

from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman


HTTPS_ENVIRON = {"wsgi.url_scheme": "https"}

DATABASE_URI = os.getenv(
    "DATABASE_URI",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        talisman.force_https = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ##################################################################
    #  H E L P E R   M E T H O D S
    ##################################################################
    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(
                BASE_URL,
                json=account.serialize()
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account"
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ##################################################################
    #  A C C O U N T   T E S T   C A S E S
    ##################################################################
    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        location = response.headers.get("Location")
        self.assertIsNotNone(location)

        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(
            new_account["date_joined"],
            str(account.date_joined)
        )

    def test_bad_request(self):
        """It should not Create an Account when sending wrong data"""
        response = self.client.post(
            BASE_URL,
            json={"name": "not enough data"}
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_unsupported_media_type(self):
        """It should not Create an Account with wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="text/html",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        )

    def test_read_an_account(self):
        """It should Read a single Account"""
        account = self._create_accounts(1)[0]

        response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.get_json()
        self.assertEqual(data["id"], account.id)
        self.assertEqual(data["name"], account.name)
        self.assertEqual(data["email"], account.email)

    def test_read_account_not_found(self):
        """It should return 404 when account is not found"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND
        )

    def test_list_accounts(self):
        """It should list all accounts"""
        accounts = self._create_accounts(5)
        response = self.client.get(BASE_URL)

        data = json.loads(response.text)
        self.assertEqual(len(accounts), len(data))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_empty_account_list(self):
        """It should return empty list when no accounts exist"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(response.text)), 0)

    def test_update_an_account(self):
        """It should Update a single Account"""
        account = self._create_accounts(1)[0]

        response = self.client.get(f"{BASE_URL}/{account.id}")
        data = response.get_json()
        data["email"] = "anewemail@gmail.com"

        update_response = self.client.put(
            f"{BASE_URL}/{account.id}",
            json=data,
        )
        self.assertEqual(
            update_response.status_code,
            status.HTTP_200_OK
        )

        verify_response = self.client.get(
            f"{BASE_URL}/{account.id}"
        )
        self.assertEqual(
            verify_response.get_json()["email"],
            data["email"]
        )

    def test_update_not_exist_account(self):
        """It should fail updating non-existent account"""
        response = self.client.put(
            f"{BASE_URL}/0",
            json={}
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND
        )

    def test_delete_an_account(self):
        """It should Delete a single Account"""
        account = self._create_accounts(1)[0]

        response = self.client.delete(
            f"{BASE_URL}/{account.id}"
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT
        )

        verify = self.client.get(BASE_URL)
        self.assertEqual(len(json.loads(verify.text)), 0)

    def test_method_not_allowed(self):
        """It should not allow illegal method calls"""
        response = self.client.delete(BASE_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get(
            "/",
            environ_overrides=HTTPS_ENVIRON
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        headers = {
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'self'; object-src 'none'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)

    def test_cors_security(self):
        """It should return CORS headers"""
        response = self.client.get(
            "/",
            environ_overrides=HTTPS_ENVIRON
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            "*"
        )
