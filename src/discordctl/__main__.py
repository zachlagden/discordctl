from __future__ import annotations

import asyncio
import logging

import sentry_sdk

from discordctl.config import Config
from discordctl.daemon.bot import run


def main() -> None:
    config = Config.from_env()
    logging.basicConfig(
        level=config.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    if config.sentry_dsn:
        sentry_sdk.init(dsn=config.sentry_dsn, traces_sample_rate=0.1)
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
