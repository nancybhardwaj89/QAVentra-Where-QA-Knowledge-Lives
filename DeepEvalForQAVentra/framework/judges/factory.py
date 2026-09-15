"""Judge factory — swap providers without touching test files."""

from framework import config

_cached_judge = None


def get_judge():
    """Returns a singleton judge instance.

    Cached so every metric across every test file shares one client
    instead of opening a new connection per metric.
    """
    global _cached_judge
    if _cached_judge is not None:
        return _cached_judge

    provider = config.JUDGE_PROVIDER.lower()

    if provider == "nvidia":
        from .nvidia_judge import NvidiaJudge
        _cached_judge = NvidiaJudge()
    else:
        raise ValueError(
            f"Unknown JUDGE_PROVIDER '{provider}'. "
            "Add a judge class under framework/judges/ and register it here."
        )

    return _cached_judge