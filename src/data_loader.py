import requests
from src.config import GITHUB_TOKEN

BASE_URL = "https://api.github.com"


class GitHubDataLoader:
    """
    Handles communication with the GitHub REST API.
    """

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }

    def get_repository(self, owner, repository):
        """
        Fetch repository information.
        """

        url = f"{BASE_URL}/repos/{owner}/{repository}"

        response = requests.get(
            url,
            headers=self.headers
        )

        if response.status_code == 200:
            return response.json()

        raise Exception(
            f"GitHub API Error: {response.status_code}\n{response.text}"
        )