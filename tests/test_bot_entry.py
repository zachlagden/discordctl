from discordctl.daemon.bot import make_intents


def test_intents_enable_all_privileged():
    intents = make_intents()
    assert intents.members is True
    assert intents.message_content is True
    assert intents.presences is True
    assert intents.guilds is True
    assert intents.voice_states is True
