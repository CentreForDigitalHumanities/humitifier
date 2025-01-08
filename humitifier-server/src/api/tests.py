from django.test import TestCase
from rest_framework.test import APIClient


class ApiTestCaseMixin:
    fixtures = [
        "test_data_source.json",
        "test_access_profile.json",
        "test_api_client.json",
    ]

    def setUp(self):
        super().setUp()

        self.system_client = APIClient()
        system_token_req = self.system_client.post(
            "/api/oauth/token/",
            data={
                "grant_type": "client_credentials",
                "client_id": "system",
                "client_secret": "topsy_krets",
            },
        )
        self.system_token = system_token_req.json()["access_token"]
        self.system_client.credentials(
            HTTP_AUTHORIZATION="Bearer %s" % self.system_token
        )

        self.read_client = APIClient()
        read_token_req = self.read_client.post(
            "/api/oauth/token/",
            data={
                "grant_type": "client_credentials",
                "client_id": "read",
                "client_secret": "topsy_krets",
            },
        )
        self.read_token = read_token_req.json()["access_token"]
        self.read_client.credentials(HTTP_AUTHORIZATION="Bearer %s" % self.read_token)


class OAuthTestCase(ApiTestCaseMixin, TestCase):

    def test_has_read_access(self):
        test_request = self.read_client.get("/api/hosts/")

        self.assertEqual(test_request.status_code, 200)

    def test_has_system_access(self):
        test_request = self.system_client.post(
            "/api/upload_scans/", data=[], format="json"
        )

        self.assertEqual(test_request.status_code, 200)

    def test_read_no_system_access(self):
        test_request = self.read_client.post(
            "/api/upload_scans/", data=[], format="json"
        )

        self.assertEqual(test_request.status_code, 403)

    def test_system_no_read_access(self):
        test_request = self.system_client.get("/api/hosts/")

        self.assertEqual(test_request.status_code, 403)
