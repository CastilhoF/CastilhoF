"""Tests for GitHub API repo pagination behavior."""

import requests

from generator.github_api import GitHubAPI


class DummyResponse:
    """Minimal response stub for GitHubAPI tests."""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.headers = {}
        self.text = ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


class TestRepoPagination:
    def test_uses_public_repo_listing_without_token(self, monkeypatch):
        api = GitHubAPI("galaxy-dev", token="")
        calls = []

        def fake_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            return DummyResponse([{"name": "nebula-ui"}])

        monkeypatch.setattr(api, "_request", fake_request)

        pages = list(api._paginate_repos())

        assert len(pages) == 1
        assert calls[0][1] == f"{api.REST_URL}/users/galaxy-dev/repos"
        assert calls[0][2]["params"] == {"per_page": 100, "type": "owner", "page": 1}

    def test_uses_authenticated_repo_listing_for_matching_token_user(self, monkeypatch):
        api = GitHubAPI("galaxy-dev", token="secret")
        calls = []

        def fake_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            if url == f"{api.REST_URL}/user":
                return DummyResponse({"login": "galaxy-dev"})
            if url == f"{api.REST_URL}/user/repos":
                return DummyResponse([{"name": "private-repo"}])
            raise AssertionError(f"Unexpected URL: {url}")

        monkeypatch.setattr(api, "_request", fake_request)

        pages = list(api._paginate_repos())

        assert len(pages) == 1
        assert calls[0][1] == f"{api.REST_URL}/user"
        assert calls[1][1] == f"{api.REST_URL}/user/repos"
        assert calls[1][2]["params"] == {
            "per_page": 100,
            "visibility": "all",
            "affiliation": "owner",
            "page": 1,
        }

    def test_falls_back_to_public_repo_listing_for_different_token_user(
        self, monkeypatch
    ):
        api = GitHubAPI("galaxy-dev", token="secret")
        calls = []

        def fake_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            if url == f"{api.REST_URL}/user":
                return DummyResponse({"login": "another-user"})
            if url == f"{api.REST_URL}/users/galaxy-dev/repos":
                return DummyResponse([{"name": "public-repo"}])
            raise AssertionError(f"Unexpected URL: {url}")

        monkeypatch.setattr(api, "_request", fake_request)

        pages = list(api._paginate_repos())

        assert len(pages) == 1
        assert calls[0][1] == f"{api.REST_URL}/user"
        assert calls[1][1] == f"{api.REST_URL}/users/galaxy-dev/repos"
        assert calls[1][2]["params"] == {"per_page": 100, "type": "owner", "page": 1}
