"""Test-only deterministic transport support; excluded from built packages."""

from __future__ import annotations

from conclave.github_foundation import (
    GitHubTransportFailure,
    GitHubTransportResponse,
    PreparedGitHubRequest,
    run_github_transport,
)


class FixtureGitHubTransport:
    """Record requests and return an exact sequence of local fixture outcomes."""

    def __init__(
        self, outcomes: list[GitHubTransportResponse | GitHubTransportFailure]
    ):
        self._outcomes = list(outcomes)
        self.requests: list[PreparedGitHubRequest] = []
        self.token_was_present: list[bool] = []

    def send(
        self, request: PreparedGitHubRequest, token: memoryview
    ) -> GitHubTransportResponse:
        self.requests.append(request)
        self.token_was_present.append(bool(token) and any(token))
        if not self._outcomes:
            raise GitHubTransportFailure(
                "TRANSPORT_CONNECTION_LOST", before_headers=True
            )
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, GitHubTransportFailure):
            raise outcome
        return outcome


run_fixture_transport = run_github_transport
