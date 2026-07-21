from src.data_loader import GitHubDataLoader

loader = GitHubDataLoader()

repository = loader.get_repository(
    owner="microsoft",
    repository="vscode"
)

print("=" * 50)
print("Repository Information")
print("=" * 50)

print(f"Repository : {repository['name']}")
print(f"Owner      : {repository['owner']['login']}")
print(f"Stars      : {repository['stargazers_count']}")
print(f"Forks      : {repository['forks_count']}")
print(f"Language   : {repository['language']}")
print(f"Open Issues: {repository['open_issues_count']}")