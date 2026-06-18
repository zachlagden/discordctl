from __future__ import annotations

import logging

import discord
from aiohttp import web

from discordctl.config import Config
from discordctl.daemon.server import build_app
from discordctl.ops.audit import AuditWriter
from discordctl.ops.registry import REGISTRY, load_all_handlers

log = logging.getLogger(__name__)


def make_intents() -> discord.Intents:
    return discord.Intents.all()


class ControlBot(discord.Client):
    def __init__(self, config: Config) -> None:
        super().__init__(intents=make_intents())
        self.config = config
        self.audit = AuditWriter(config.audit_path)
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    async def setup_hook(self) -> None:
        load_all_handlers()
        log.info("loaded %d ops", len(REGISTRY.ops()))

    async def on_ready(self) -> None:
        if self._site is not None:
            return

        app = build_app(bot=self, config=self.config, audit=self.audit)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self.config.bus_host, port=self.config.bus_port)
        await site.start()
        self._runner, self._site = runner, site
        log.info(
            "control bus on %s:%s as %s", self.config.bus_host, self.config.bus_port, self.user
        )


async def run(config: Config) -> None:
    bot = ControlBot(config)
    async with bot:
        await bot.start(config.discord_token)
