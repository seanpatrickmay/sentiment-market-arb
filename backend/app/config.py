from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: AnyUrl = "postgresql+psycopg2://sentiment_arb_user:sentiment_arb_password@db:5432/sentiment_arb"

    polymarket_api_base: str = "https://api.polymarket.com"
    polymarket_api_key: str | None = None

    kalshi_api_base: str = "https://trading-api.kalshi.com/v1"
    kalshi_api_key: str | None = None
    kalshi_api_secret: str | None = None

    min_worst_case_roi: float = 0.005  # 0.5%
    min_total_stake: float = 10.0
    max_stake_per_leg: float = 50.0

    class Config:
        env_prefix = ""
        env_file = ".env"


settings = Settings()
