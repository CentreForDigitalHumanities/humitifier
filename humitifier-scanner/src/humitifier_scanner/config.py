import os
from pathlib import Path
from typing import Tuple, Type

from pydantic import AmqpDsn, AnyHttpUrl, BaseModel, Field, Secret
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from humitifier_scanner.logger import logger

# Pydantic expects environment variables to be in lowercase
# But that hurts my brain, so let's add a little helper to add a lowercase
# version of each env var (prefixed with HUMITIFIER_SCANNER_) to the environment
for env_var, value in os.environ.items():
    if env_var.startswith("HUMITIFIER_SCANNER_"):
        os.environ[env_var.lower()] = value

# Get location of this file
_BASE_DIR = Path(__file__).parent

_CONFIG_LOCATIONS = [
    _BASE_DIR / Path("../../.local/config.toml"),
    Path("~/.config/humitifier-scanner/config.toml").expanduser(),
    Path("~/.humitifier-scanner/config.toml").expanduser(),
    Path("/etc/humitifier-scanner/config.toml"),
    Path("/usr/local/etc/humitifier-scanner/config.toml"),
]
if config_in_env := os.environ.get("HUMITIFIER_SCANNER_CONFIG"):
    _CONFIG_LOCATIONS.insert(0, Path(config_in_env))

_SECRETS_DIR = os.environ.get("HUMITIFIER_SCANNER_SECRETS_DIR", None)

for loc in _CONFIG_LOCATIONS:
    if loc.exists():
        logger.debug(f"Using config file: {loc}")


##
## Config sections
##
class CeleryConfig(BaseModel):
    rabbit_mq_url: AmqpDsn = Field(description="RabbitMQ URL")
    sentry_dsn: AnyHttpUrl | None = Field(None, description="Sentry DSN")
    sentry_insecure_cert: bool = Field(
        False, description="Insecure certificate; for " "local testing"
    )
    # TODO: rabbitmq auth


class StandaloneConfig(BaseModel):
    api_url: str = Field(
        description="URL where the API is running, including the schema, port and trailing slash. e.g. http://localhost:8000/api/"
    )
    api_client_id: str = Field(description="Client ID for the API")
    api_client_secret: Secret[str] = Field(description="Client secret for the API")

    # Endpoints
    token_endpoint: str = Field(
        "oauth/token/",
        description="OAuth token endpoint, will be appended to the API URL",
    )
    upload_endpoint: str = Field(
        "upload_scans/",
        description="Scan result upload endpoint, will be appended to the API URL",
    )


class SSHBastionConfig(BaseModel):
    host: str
    user: str | None = None
    private_key: str | None = None
    private_key_password: Secret[str] | None = None


class SSHConfig(BaseModel):
    user: str
    private_key: str
    private_key_password: Secret[str] | None = None
    bastion: SSHBastionConfig | None = None


##
## Main config
##
class _Settings:

    ##
    ## Common settings
    ##
    ssh: SSHConfig | None = None
    log_level: str = "INFO"

    ##
    ## Celery settings
    ##
    celery: CeleryConfig | None = None

    ##
    ## Standalone mode settings
    ##
    standalone: StandaloneConfig | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # Customized to add a TOML config file source
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            TomlConfigSettingsSource(settings_cls),
        )


# The CLI uses its own version of the settings class, but Pydantic doesn't
# really like the inheritance. So we create two BaseSettings classes that
# inherit from the same _Settings class as a workaround.
class Settings(_Settings, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="humitifier_scanner_",
        env_nested_delimiter="__",
        toml_file=_CONFIG_LOCATIONS,
        secrets_dir=_SECRETS_DIR,
        extra="ignore",
    )


CONFIG = Settings()
