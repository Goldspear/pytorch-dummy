"""GitHub Utilities"""

import json
import os

from dataclasses import dataclass
from typing import Any, Callable, cast, Dict, List, Optional
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass
class GitHubComment:
    body_text: str
    created_at: str
    author_login: str
    author_association: str
    editor_login: Optional[str]
    database_id: int


def gh_fetch_url(
    url: str, *,
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None,
    method: Optional[str] = None,
    reader: Callable[[Any], Any] = lambda x: x.read()
) -> Any:
    if headers is None:
        headers = {}
    token = os.environ.get("GITHUB_TOKEN")
    if token is not None and url.startswith('https://api.github.com/'):
        headers['Authorization'] = f'token {token}'
    data_ = json.dumps(data).encode() if data is not None else None
    try:
        with urlopen(Request(url, headers=headers, data=data_, method=method)) as conn:
            return reader(conn)
    except HTTPError as err:
        if err.code == 403 and all(key in err.headers for key in ['X-RateLimit-Limit', 'X-RateLimit-Used']):
            print(f"Rate limit exceeded: {err.headers['X-RateLimit-Used']}/{err.headers['X-RateLimit-Limit']}")
        raise


def gh_fetch_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if params is not None and len(params) > 0:
        url += '?' + '&'.join(f"{name}={quote(str(val))}" for name, val in params.items())
    return cast(List[Dict[str, Any]], gh_fetch_url(url, headers=headers, data=data, reader=json.load))


def gh_fetch_json_dict(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any] :
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if params is not None and len(params) > 0:
        url += '?' + '&'.join(f"{name}={quote(str(val))}" for name, val in params.items())
    return cast(Dict[str, Any], gh_fetch_url(url, headers=headers, data=data, reader=json.load))


def _gh_post_comment(url: str, comment: str, dry_run: bool = False) -> List[Dict[str, Any]]:
    if dry_run:
        print(comment)
        return []
    return gh_fetch_json(url, data={"body": comment})


def gh_post_pr_comment(org: str, project: str, pr_num: int, comment: str, dry_run: bool = False) -> List[Dict[str, Any]]:
    return _gh_post_comment(f'https://api.github.com/repos/{org}/{project}/issues/{pr_num}/comments', comment, dry_run)


def gh_post_commit_comment(org: str, project: str, sha: str, comment: str, dry_run: bool = False) -> List[Dict[str, Any]]:
    return _gh_post_comment(f'https://api.github.com/repos/{org}/{project}/commits/{sha}/comments', comment, dry_run)


def gh_post_delete_comment(org: str, project: str, comment_id: int) -> None:
    url = f"https://api.github.com/repos/{org}/{project}/issues/comments/{comment_id}"
    gh_fetch_url(url, method="DELETE")