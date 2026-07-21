import pandas as pd

from src.analytics_engine import AnalyticsEngine

repo_df = pd.DataFrame([
    {
        'repository_name': 'vscode',
        'full_name': 'microsoft/vscode',
        'owner_login': 'microsoft',
        'stars': 100,
        'forks': 50,
        'watchers': 100,
        'open_issues': 10,
        'language': 'Python',
        'default_branch': 'main',
        'created_at': '2020-01-01T00:00:00Z',
    }
])
commits_df = pd.DataFrame([
    {'sha': 'a1', 'author_login': 'alice', 'commit_author_date': '2024-01-01T00:00:00Z'},
    {'sha': 'b2', 'author_login': 'bob', 'commit_author_date': '2024-01-02T00:00:00Z'},
    {'sha': 'c3', 'author_login': 'alice', 'commit_author_date': '2024-01-03T00:00:00Z'},
])
contributors_df = pd.DataFrame([
    {'login': 'alice', 'id': 1, 'contributions': 10, 'type': 'User', 'site_admin': False},
    {'login': 'bob', 'id': 2, 'contributions': 5, 'type': 'User', 'site_admin': False},
])
issues_df = pd.DataFrame([
    {
        'issue_id': 1,
        'number': 1,
        'title': 'Bug',
        'state': 'open',
        'comments': 2,
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-02T00:00:00Z',
        'closed_at': None,
        'user_login': 'alice',
        'user_id': 1,
        'assignee_login': 'bob',
        'assignee_id': 2,
        'is_pull_request': False,
    },
    {
        'issue_id': 2,
        'number': 2,
        'title': 'Fix',
        'state': 'closed',
        'comments': 1,
        'created_at': '2024-01-03T00:00:00Z',
        'updated_at': '2024-01-04T00:00:00Z',
        'closed_at': '2024-01-05T00:00:00Z',
        'user_login': 'bob',
        'user_id': 2,
        'assignee_login': 'alice',
        'assignee_id': 1,
        'is_pull_request': False,
    },
])
languages_df = pd.DataFrame([
    {'language': 'Python', 'bytes': 1000},
    {'language': 'TypeScript', 'bytes': 500},
])

engine = AnalyticsEngine(
    repository_df=repo_df,
    commits_df=commits_df,
    contributors_df=contributors_df,
    issues_df=issues_df,
    languages_df=languages_df,
)

print('repository_summary', engine.repository_summary())
print('commit_statistics', engine.commit_statistics())
print('contributor_statistics', engine.contributor_statistics())
print('issue_statistics', engine.issue_statistics())
print('language_statistics', engine.language_statistics().to_dict(orient='records'))
print('activity_summary', engine.activity_summary())
