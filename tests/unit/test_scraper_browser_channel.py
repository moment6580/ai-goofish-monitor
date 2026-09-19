import importlib


def _load_browser_module(monkeypatch, *, login_is_edge: bool, running_in_docker: bool):
    monkeypatch.setenv("LOGIN_IS_EDGE", "true" if login_is_edge else "false")
    monkeypatch.setenv("RUNNING_IN_DOCKER", "true" if running_in_docker else "false")

    import src.config as config_module
    import src.scraper.browser as browser_module

    importlib.reload(config_module)
    reloaded_browser = importlib.reload(browser_module)
    reloaded_browser.EDGE_DOCKER_WARNING_PRINTED = False
    return reloaded_browser


def test_resolve_browser_channel_uses_chromium_in_docker_even_when_edge_requested(monkeypatch, capsys):
    browser = _load_browser_module(monkeypatch, login_is_edge=True, running_in_docker=True)

    assert browser._resolve_browser_channel() == "chromium"
    assert "Docker 镜像未内置 Edge" in capsys.readouterr().out


def test_resolve_browser_channel_uses_msedge_locally_when_requested(monkeypatch):
    browser = _load_browser_module(monkeypatch, login_is_edge=True, running_in_docker=False)

    assert browser._resolve_browser_channel() == "msedge"
