from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://tmgboard:tmgboard@localhost:5432/tmg_board"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # DocuSign
    docusign_integration_key: str = ""
    docusign_user_id: str = ""
    docusign_account_id: str = ""
    docusign_base_url: str = "https://demo.docusign.net/restapi"
    docusign_private_key_path: str = "./keys/docusign_private.pem"
    docusign_hmac_key: str = ""

    # S3 Storage
    storage_type: str = "s3"  # s3 or local
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-west-2"
    s3_bucket: str = "tmg-board-documents"

    # App
    base_url: str = "https://tmgboard.themany.com"
    debug: bool = False
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3100",
        "https://tmgboard.themany.com",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
