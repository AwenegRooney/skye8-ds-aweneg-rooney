import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv()


def get_engine(db_url: str | None = None) -> Engine:
    """
    Creates a SQLAlchemy engine using environment variables.
    """
    url = db_url or os.environ.get("DATABASE_URL")
    if url is None:
        raise ValueError("DATABASE _URL environment variable is not set")

    return create_engine(url)
