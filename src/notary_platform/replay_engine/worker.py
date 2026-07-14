"""Replay Engine worker entrypoint."""

import logging

LOGGER = logging.getLogger(__name__)


def run_once() -> None:
    """Run one placeholder replay-engine iteration."""
    LOGGER.info("Replay Engine worker scaffold is idle; no queue integration configured yet.")


def main() -> None:
    """Start the Replay Engine worker scaffold."""
    logging.basicConfig(level=logging.INFO)
    run_once()


if __name__ == "__main__":
    main()
