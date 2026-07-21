import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read GitHub Token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")