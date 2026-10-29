import os

os.environ.setdefault("BOT_TOKEN", "test")

import pytest  # noqa: E402

from bot.config import Settings  # noqa: E402


@pytest.mark.parametrize("raw", ["[@Tl_miwqsd]", "@tl_miwqsd", "tl_miwqsd, 123", '["@tl_miwqsd", 123]'])
def test_admin_by_username(raw):
    s = Settings(bot_token="t", admin_ids=raw)
    assert s.is_admin(1, "TL_MIWQSD")
    assert not s.is_admin(1, "someone")


def test_admin_by_id():
    s = Settings(bot_token="t", admin_ids="[123456789]")
    assert s.is_admin(123456789, None)
    assert not s.is_admin(42, None)


def test_no_admins():
    assert not Settings(bot_token="t", admin_ids="").is_admin(1, "x")
