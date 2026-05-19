import os

from dotenv import load_dotenv
from openai import AsyncClient


load_dotenv()
OPENAI__API_URL= os.getenv("OPENAI__API_URL")
OPENAI__API_KEY= os.getenv("OPENAI__API_KEY")

client = AsyncClient(
    base_url=OPENAI__API_URL,
    api_key=OPENAI__API_KEY,
)

