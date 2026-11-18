from typing import Callable, Iterable, Tuple


CleanupAction = Tuple[str, Callable[[], None]]


class CleanupError(Exception):
    """Raised when one or more cleanup operations fail."""


def run_cleanup(actions: Iterable[CleanupAction]) -> None:
    failures = []

    for name, action in actions:
        try:
            action()
        except Exception as exc:
            failures.append((name, exc))

    if failures:
        details = "\n".join(
            f"- {name}: {type(exc).__name__}: {exc}" for name, exc in failures
        )

        raise CleanupError(f"{len(failures)} cleanup action(s) failed:\n{details}")
