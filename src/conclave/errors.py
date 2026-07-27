"""CONCLAVE error types.

Errors are deliberately specific. A governance tool that raises bare
exceptions cannot record *why* it refused to proceed, and refusing for a
recorded reason is most of the point.
"""


class ConclaveError(Exception):
    """Base for all CONCLAVE errors."""


class IntegrityError(ConclaveError):
    """Content failed a canonical-form or hash check.

    Raised rather than silently repaired. A tool that quietly fixes
    non-canonical input produces hashes that cannot be reproduced by
    anyone who did not run the same repair.
    """


class WorkspaceError(ConclaveError):
    """Workspace missing, malformed, or already present."""


class ValidationError(ConclaveError):
    """A packet failed schema or semantic validation."""


class LedgerError(ConclaveError):
    """Ledger chain is broken, or an append would violate append-only."""
