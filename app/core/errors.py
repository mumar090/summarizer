class SummarizationError(Exception):
    """A permanent failure: retrying will not help (bad URL, 404, unsupported content...).

    The message is shown to API clients, so it must not leak internals.
    """


class TransientError(SummarizationError):
    """A failure that is likely to succeed on retry (timeouts, 5xx, LLM busy...)."""


class UnsafeURLError(SummarizationError):
    """The URL points to a private, loopback or otherwise non-public address."""
