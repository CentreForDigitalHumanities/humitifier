import base64

import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session
from urllib.parse import urljoin

from humitifier_common.scan_data import ScanInput, ScanOutput
from humitifier_scanner.config import CONFIG, StandaloneConfig
from humitifier_scanner.logger import logger


class HumitifierAPIClient:

    def __init__(self):
        config = CONFIG.standalone
        if not config:
            raise RuntimeError("No API configuration configured")

        self.config: StandaloneConfig = config
        self._client = None

        self._setup_client()

    def _setup_client(self):
        logger.debug("Setting up API client")
        _client_id = self.config.api_client_id
        _client_secret = self.config.api_client_secret.get_secret_value()

        auth = HTTPBasicAuth(_client_id, _client_secret)
        oauth_client = BackendApplicationClient(
            client_id=self.config.api_client_id, scope=self.config.api_client_scope
        )
        self.client = OAuth2Session(
            client=oauth_client,
        )
        token = self.client.fetch_token(
            token_url=self._token_endpoint,
            auth=auth,
        )
        logger.debug(f"Got token {token}")

    #
    # API methods
    #

    def get_scan_spec(self, host: str) -> ScanInput | None:
        logger.debug(f"Getting scan spec for host {host}")
        url = urljoin(self._scan_spec_endpoint, host)
        if not url.endswith("/"):
            url += "/"

        r = self.client.get(url=url)

        if r.ok:
            try:
                data = r.json()
                return ScanInput(**data)
            except:
                logger.error("Got invalid json")
                return None

        logger.error(f"Request failed - Status code {r.status_code} - Body: {r.text}")
        return None

    def upload_scan(self, data: ScanOutput) -> bool:
        logger.debug(f"Uploading scan data")

        r = self.client.post(
            url=self._upload_endpoint,
            json=data.model_dump(mode="json"),
        )

        if not r.ok:
            logger.error(
                f"Request failed - Status code {r.status_code} - Body: {r.text}"
            )

        return r.ok

    #
    # Properties
    #

    @property
    def _token_endpoint(self):
        root = self.config.api_url
        token_endpoint = self.config.token_endpoint
        return urljoin(root, token_endpoint)

    @property
    def _upload_endpoint(self):
        root = self.config.api_url
        upload_endpoint = self.config.upload_endpoint
        return urljoin(root, upload_endpoint)

    @property
    def _scan_spec_endpoint(self):
        root = self.config.api_url
        scan_spec_endpoint = self.config.scan_spec_endpoint
        return urljoin(root, scan_spec_endpoint)
