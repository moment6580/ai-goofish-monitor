import os

import pytest

from src.infrastructure.config.settings import (
    get_app_settings,
    get_scraper_settings,
    reload_settings,
)


@pytest.fixture()
def restore_settings():
    """保存相关环境变量，测试结束后还原并重载配置，避免污染其他用例。"""
    keys = ("RUN_HEADLESS", "SERVER_PORT")
    saved = {k: os.environ.get(k) for k in keys}
    yield
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    reload_settings()


def test_reload_settings_refreshes_getters(restore_settings):
    os.environ["RUN_HEADLESS"] = "false"
    reload_settings()
    assert get_scraper_settings().run_headless is False

    os.environ["RUN_HEADLESS"] = "true"
    reload_settings()
    assert get_scraper_settings().run_headless is True


def test_get_settings_returns_current_instance(restore_settings):
    before = get_app_settings()
    os.environ["SERVER_PORT"] = "9999"
    reload_settings()
    after = get_app_settings()
    assert after is not before
    assert after.server_port == 9999
