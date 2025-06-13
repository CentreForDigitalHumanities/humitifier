from django.test import TestCase
from rest_framework.test import APIClient

from hosts.models import DataSource, DataSourceType, Host
from humitifier_common.scan_data import ScanInput, ScanOutput


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

    def assertRequestSuccessful(self, request):
        message = request.data
        self.assertEqual(
            request.status_code, 200, f"Request was not successful: {message}"
        )

    def assertRequestUnsuccessful(self, request):
        message = request.data
        self.assertGreaterEqual(
            request.status_code, 400, f"Request was successful: {message}"
        )


class OAuthTestCase(ApiTestCaseMixin, TestCase):

    def setUp(self):
        super().setUp()

        self.scan_obj = ScanOutput(
            original_input=ScanInput(hostname="fake.mcfake.com", artefacts={}),
            scan_date="2011-11-10T00:00:00Z",
            hostname="example.org",
            facts={},
            metrics={},
            errors=[],
        )

    def _create_host(self, overrides: dict = None):
        host_data = {
            "fqdn": "example.org",
            "data_source_id": 1,
            "department": "Example",
            "customer": "Example",
            "contact": "x@example.org",
            "has_tofu_config": False,
            "otap_stage": "test",
        }

        if overrides:
            host_data.update(overrides)

        Host.objects.create(**host_data)

    def test_has_read_access(self):
        test_request = self.read_client.get("/api/hosts/")

        self.assertRequestSuccessful(test_request)

    def test_has_system_access(self):
        self._create_host()
        test_request = self.system_client.post(
            "/api/upload_scans/", data=self.scan_obj.model_dump(), format="json"
        )

        self.assertRequestSuccessful(test_request)

    def test_read_no_system_access(self):
        self._create_host()
        test_request = self.read_client.post(
            "/api/upload_scans/", data=self.scan_obj.model_dump(), format="json"
        )

        self.assertRequestUnsuccessful(test_request)

    def test_system_no_read_access(self):
        test_request = self.system_client.get("/api/hosts/")

        self.assertRequestUnsuccessful(test_request)


class HostSyncTestCase(ApiTestCaseMixin, TestCase):

    def setUp(self):
        super().setUp()

        self.data_source = DataSource.objects.filter(
            source_type=DataSourceType.API
        ).first()

    def _create_host(self, overrides: dict = None):
        host_data = {
            "fqdn": "example.org",
            "data_source": self.data_source,
            "department": "Example",
            "customer": "Example",
            "contact": "x@example.org",
            "has_tofu_config": False,
            "otap_stage": "test",
        }

        if overrides:
            host_data.update(overrides)

        Host.objects.create(**host_data)

    def _send_sync(self, hosts):
        return self.system_client.post(
            "/api/inventory_sync/",
            data={
                "data_source": self.data_source.identifier,
                "hosts": hosts,
            },
            format="json",
        )

    def test_new_host(self):
        self.assertEqual(self.data_source.hosts.count(), 0)

        test_request = self._send_sync(
            [
                {
                    "fqdn": "example.org",
                    "department": "Example",
                    "customer": "Example",
                    "contact": "x@example.org",
                    "has_tofu_config": False,
                    "otap_stage": "development",
                },
            ]
        )

        self.assertRequestSuccessful(test_request)

        response = test_request.data
        self.assertEqual(response["updated"], [])
        self.assertEqual(response["created"], ["example.org"])
        self.assertEqual(response["archived"], [])

        self.assertEqual(self.data_source.hosts.count(), 1)

        host = Host.objects.get(fqdn="example.org")
        self.assertEqual(host.department, "Example")
        self.assertEqual(host.customer, "Example")
        self.assertEqual(host.contact, "x@example.org")
        self.assertEqual(host.has_tofu_config, False)
        self.assertEqual(host.otap_stage, "development")
        self.assertEqual(host.billable, False)

    def test_new_billable_host(self):
        self.assertEqual(self.data_source.hosts.count(), 0)

        test_request = self._send_sync(
            [
                {
                    "fqdn": "example.org",
                    "department": "Example",
                    "customer": "Example",
                    "contact": "x@example.org",
                    "has_tofu_config": False,
                    "otap_stage": "development",
                    "billable": True,
                },
            ]
        )

        self.assertRequestSuccessful(test_request)

        response = test_request.data
        self.assertEqual(response["updated"], [])
        self.assertEqual(response["created"], ["example.org"])
        self.assertEqual(response["archived"], [])

        self.assertEqual(self.data_source.hosts.count(), 1)

        host = Host.objects.get(fqdn="example.org")
        self.assertEqual(host.billable, True)

    def test_existing_host_update(self):
        self._create_host()

        self.assertEqual(self.data_source.hosts.count(), 1)

        test_request = self._send_sync(
            [
                {
                    "fqdn": "example.org",
                    "department": "Another department",
                    "customer": "Another customer",
                    "contact": "y@example.org",
                    "has_tofu_config": True,
                    "otap_stage": "development",
                },
            ]
        )

        self.assertRequestSuccessful(test_request)

        response = test_request.data
        self.assertEqual(response["updated"], ["example.org"])
        self.assertEqual(response["created"], [])
        self.assertEqual(response["archived"], [])

        self.assertEqual(self.data_source.hosts.count(), 1)

        host = Host.objects.get(fqdn="example.org")
        self.assertEqual(host.department, "Another department")
        self.assertEqual(host.contact, "y@example.org")
        self.assertEqual(host.has_tofu_config, True)
        self.assertEqual(host.otap_stage, "development")

    def test_existing_billable_host_update(self):
        self._create_host()

        self.assertEqual(self.data_source.hosts.count(), 1)

        test_request = self._send_sync(
            [
                {
                    "fqdn": "example.org",
                    "department": "Another department",
                    "customer": "Another customer",
                    "contact": "y@example.org",
                    "has_tofu_config": True,
                    "otap_stage": "development",
                    "billable": True,
                },
            ]
        )

        self.assertRequestSuccessful(test_request)

        response = test_request.data
        self.assertEqual(response["updated"], ["example.org"])
        self.assertEqual(response["created"], [])
        self.assertEqual(response["archived"], [])

        self.assertEqual(self.data_source.hosts.count(), 1)

        host = Host.objects.get(fqdn="example.org")
        self.assertEqual(host.billable, True)

    def test_archive_host(self):
        self._create_host()

        self.assertEqual(self.data_source.hosts.count(), 1)

        test_request = self._send_sync([])

        self.assertRequestSuccessful(test_request)

        response = test_request.data
        self.assertEqual(response["updated"], [])
        self.assertEqual(response["created"], [])
        self.assertEqual(response["archived"], ["example.org"])

        # It shouldn't have been deleted
        self.assertEqual(self.data_source.hosts.count(), 1)
        # But it should now have archived=True
        self.assertEqual(self.data_source.hosts.filter(archived=False).count(), 0)

    def test_unarchive_host(self):
        self._create_host({"archived": True})

        self.assertEqual(self.data_source.hosts.count(), 1)
        self.assertEqual(self.data_source.hosts.filter(archived=False).count(), 0)

        test_request = self._send_sync(
            [
                {
                    "fqdn": "example.org",
                    "department": "Example",
                    "customer": "Example",
                    "contact": "x@example.org",
                    "has_tofu_config": False,
                    "otap_stage": "development",
                },
            ]
        )
        self.assertRequestSuccessful(test_request)

        response = test_request.data
        self.assertEqual(response["updated"], ["example.org"])
        self.assertEqual(response["created"], [])
        self.assertEqual(response["archived"], [])

        self.assertEqual(self.data_source.hosts.count(), 1)
        self.assertEqual(self.data_source.hosts.filter(archived=False).count(), 1)

    def test_archive_host_twice(self):
        # This test makes sure we only display an archived server if it was archived during this sync
        self._create_host()

        self.assertEqual(self.data_source.hosts.count(), 1)

        self._send_sync([])

        test_request = self._send_sync([])

        response = test_request.data

        self.assertEqual(response["updated"], [])
        self.assertEqual(response["created"], [])
        self.assertEqual(response["archived"], [])

        self.assertRequestSuccessful(test_request)

    def test_ignore_other_hosts(self):
        other_data_source = DataSource.objects.create()
        self._create_host({"data_source": other_data_source})

        self.assertEqual(Host.objects.count(), 1)
        self.assertEqual(self.data_source.hosts.count(), 0)

        test_request = self._send_sync([])

        self.assertRequestSuccessful(test_request)

        response = test_request.data
        self.assertEqual(response["updated"], [])
        self.assertEqual(response["created"], [])
        self.assertEqual(response["archived"], [])

        self.assertEqual(Host.objects.count(), 1)
        self.assertEqual(self.data_source.hosts.count(), 0)

    def test_fail_already_claimed_host(self):
        other_data_source = DataSource.objects.create()
        self._create_host({"data_source": other_data_source})

        self.assertEqual(Host.objects.count(), 1)
        self.assertEqual(self.data_source.hosts.count(), 0)

        test_request = self._send_sync(
            [
                {
                    "fqdn": "example.org",
                    "department": "Example",
                    "customer": "Example",
                    "contact": "x@example.org",
                    "has_tofu_config": False,
                    "otap_stage": "development",
                },
            ]
        )

        self.assertRequestUnsuccessful(test_request)

        self.assertEqual(Host.objects.count(), 1)
        self.assertEqual(self.data_source.hosts.count(), 0)

    def test_claim_unclaimed_host(self):
        self._create_host({"data_source": None})

        self.assertEqual(Host.objects.count(), 1)
        self.assertEqual(self.data_source.hosts.count(), 0)

        test_request = self._send_sync(
            [
                {
                    "fqdn": "example.org",
                    "department": "Example",
                    "customer": "Example",
                    "contact": "x@example.org",
                    "has_tofu_config": False,
                    "otap_stage": "development",
                },
            ]
        )

        self.assertRequestSuccessful(test_request)

        response = test_request.data
        self.assertEqual(response["updated"], ["example.org"])
        self.assertEqual(response["created"], [])
        self.assertEqual(response["archived"], [])

        self.assertEqual(Host.objects.count(), 1)
        self.assertEqual(self.data_source.hosts.count(), 1)
