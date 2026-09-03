import os
from pathlib import Path
from typing import Tuple, Type

from humitifier_common.utils.config_helpers import (
    add_lowercase_env_vars,
    generate_config_locations,
)
from pydantic import AmqpDsn, AnyHttpUrl, BaseModel, Field, RedisDsn, Secret
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from humitifier_network_indexer.logger import logger

# Pydantic expects environment variables to be in lowercase
# But that hurts my brain, so let's add a little helper to add a lowercase
# version of each env var (prefixed with HUMITIFIER_NETWORK_INDEXER_) to the environment
add_lowercase_env_vars("HUMITIFIER_NETWORK_INDEXER_")

# Get location of this file
_BASE_DIR = Path(__file__).parent

_CONFIG_LOCATIONS = generate_config_locations(
    _BASE_DIR, "scanner", "HUMITIFIER_NETWORK_INDEXER_CONFIG"
)

_SECRETS_DIR = os.environ.get("HUMITIFIER_SCANNER_SECRETS_DIR", None)

for loc in _CONFIG_LOCATIONS:
    if loc.exists():
        logger.debug(f"Using config file: {loc}")


##
## Config sections
##
class CeleryConfig(BaseModel):
    rabbit_mq_url: AmqpDsn | None = Field(description="RabbitMQ URL", default=None)
    redis_dsn: RedisDsn | None = Field(description="Redis URL", default=None)
    sentry_dsn: AnyHttpUrl | None = Field(None, description="Sentry DSN")
    sentry_insecure_cert: bool = Field(
        False, description="Insecure certificate; for local testing"
    )


##
## Main config
##
class _Settings:

    ##
    ## Common settings
    ##
    log_level: str = "INFO"

    ##
    ## Celery settings
    ##
    celery: CeleryConfig | None = None

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


class Settings(_Settings, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="humitifier_network_indexer_",
        env_nested_delimiter="__",
        toml_file=_CONFIG_LOCATIONS,
        secrets_dir=_SECRETS_DIR,
        extra="ignore",
    )


CONFIG = Settings()
