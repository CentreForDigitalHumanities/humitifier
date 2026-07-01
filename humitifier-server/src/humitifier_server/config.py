from pathlib import Path

from pydantic import (
    AmqpDsn,
    AnyHttpUrl,
    BaseModel,
    Field,
    RedisDsn,
    Secret,
)
from typing import Literal, Tuple, Type

import os
from humitifier_common.utils.config_helpers import (
    add_lowercase_env_vars,
    generate_config_locations,
)

try:
    from humitifier_server.logger import logger
except ImportError:
    from logging import getLogger

    logger = getLogger(__name__)

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

# Pydantic expects environment variables to be in lowercase
# But that hurts my brain, so let's add a little helper to add a lowercase
# version of each env var (prefixed with HUMITIFIER_SERVER_) to the environment
add_lowercase_env_vars("HUMITIFIER_SERVER_")

# Get location of this file
_BASE_DIR = Path(__file__).parent

_CONFIG_LOCATIONS = generate_config_locations(
    _BASE_DIR, "server", "HUMITIFIER_SERVER_CONFIG"
)

_SECRETS_DIR = os.environ.get("HUMITIFIER_SCANNER_SECRETS_DIR", None)

for loc in _CONFIG_LOCATIONS:
    if loc.exists():
        logger.debug(f"Using config file: {loc}")


class DjangoConfig(BaseModel):
    secret_key: Secret[str] = Secret(
        "django-insecure-ffdjavjsp%s%b069$aai#h7odtbd#!q8uuhn1tv&y$gdq17_"
    )
    debug: bool = False
    allowed_hosts: list[str] = []
    enable_https: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class DatabaseConfig(BaseModel):
    database_name: str
    username: str
    password: Secret[str]
    host: str = "127.0.0.1"
    port: int = 5432


class StaticFilesConfig(BaseModel):
    enable_whitenoise: bool = True


class CookieConfig(BaseModel):
    domain: str | None = None
    session_name: str = "humitifier_sessionid"
    expire_at_browser_close: bool = True
    max_age: int = 43200  # 12 hours


class CeleryConfig(BaseModel):
    rabbit_mq_url: AmqpDsn | None = Field(description="RabbitMQ URL", default=None)
    redis_dsn: RedisDsn | None = Field(description="Redis URL", default=None)


class SentryConfig(BaseModel):
    dsn: AnyHttpUrl = Field(description="Sentry DSN")
    insecure_cert: bool = False


class OIDCConfig(BaseModel):
    enabled: bool = False
    session_refresh: bool = False
    auto_create_user: bool = False

    rp_client_id: str = ""
    rp_client_secret: Secret[str] = ""
    rp_scopes: list[str] = ["openid", "email", "profile"]
    rp_sign_algorithm: str = "RS256"
    rp_acr_values: str | None = None

    op_jwks_endpoint: str = ""
    op_authorization_endpoint: str = ""
    op_token_endpoint: str = ""
    op_userinfo_endpoint: str = ""


class HumitifierServerConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="humitifier_server_",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
        toml_file=_CONFIG_LOCATIONS,
        secrets_dir=_SECRETS_DIR,
        extra="ignore",
    )

    django: DjangoConfig = Field(default_factory=DjangoConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    static_files: StaticFilesConfig = Field(default_factory=StaticFilesConfig)
    cookie: CookieConfig = Field(default_factory=CookieConfig)
    celery: CeleryConfig = Field(default_factory=CeleryConfig)
    sentry: SentryConfig | None = None
    oidc: OIDCConfig | None = None

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


CONFIG = HumitifierServerConfig()
