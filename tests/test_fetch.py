"""测试 fetch.py 的 raw data 获取逻辑."""

from __future__ import annotations

import os

import pytest

from hoyo_story import fetch as fetch_module
from hoyo_story.fetch import (
    GAME_PATHS,
    GENSHIN_PATHS,
    STARRAIL_PATHS,
    fetch_raw,
    get_repo_url,
)


class TestGetRepoUrl:
    """get_repo_url() 的单元测试."""

    def test_valid_game_with_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GENSHIN_RAW_REPO", "https://github.com/example/genshin.git")
        assert get_repo_url("genshin") == "https://github.com/example/genshin.git"

    def test_env_not_set_raises(self) -> None:
        for key in ("GENSHIN_RAW_REPO", "STARRAIL_RAW_REPO", "ZZZ_RAW_REPO"):
            os.environ.pop(key, None)
        with pytest.raises(ValueError, match="未设置"):
            get_repo_url("genshin")

    def test_invalid_game_raises(self) -> None:
        with pytest.raises(ValueError, match="未知游戏"):
            get_repo_url("invalid_game")

    def test_each_supported_game(self, monkeypatch: pytest.MonkeyPatch) -> None:
        test_cases = [
            ("genshin", "GENSHIN_RAW_REPO", "https://github.com/example/genshin.git"),
            ("starrail", "STARRAIL_RAW_REPO", "https://github.com/example/sr.git"),
            ("zzz", "ZZZ_RAW_REPO", "https://gitea.example/zzz.git"),
        ]
        for game, env_var, url in test_cases:
            monkeypatch.setenv(env_var, url)
            assert get_repo_url(game) == url


class TestFetchRaw:
    """fetch_raw() 的单元测试 — 使用 git init 模拟."""

    def test_fetch_raw_clone_succeeds(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        """fetch_raw() 调用 clone 和 no-cone sparse checkout."""
        calls: list[tuple[list[str], str | None]] = []

        def fake_run_git(args: list[str], cwd: str | None = None) -> None:
            calls.append((args, cwd))

        monkeypatch.setenv("GENSHIN_RAW_REPO", "https://example.com/genshin.git")
        monkeypatch.setattr(fetch_module, "_run_git", fake_run_git)

        target = tmp_path / "target"
        fetch_raw("genshin", str(target), proxy="http://127.0.0.1:7897")

        assert len(calls) == 2
        clone_args, clone_cwd = calls[0]
        assert clone_cwd is None
        assert clone_args[:4] == ["clone", "--depth=1", "--filter=blob:none", "--sparse"]
        assert "http.proxy=http://127.0.0.1:7897" in clone_args
        assert clone_args[-2:] == ["https://example.com/genshin.git", str(target)]

        sparse_args, sparse_cwd = calls[1]
        assert sparse_cwd == str(target)
        assert sparse_args[:3] == ["sparse-checkout", "set", "--no-cone"]
        assert "/BinOutput/Talk/" in sparse_args
        assert "/ExcelBinOutput/AvatarExcelConfigData.json" in sparse_args
        assert "/Readable/CHS/" in sparse_args

    def test_fetch_raw_env_not_set(self, tmp_path) -> None:
        for key in ("GENSHIN_RAW_REPO", "STARRAIL_RAW_REPO", "ZZZ_RAW_REPO"):
            os.environ.pop(key, None)
        with pytest.raises(ValueError, match="未设置"):
            fetch_raw("genshin", str(tmp_path / "target"))

    def test_game_paths_have_entries(self) -> None:
        """每个支持的游戏都有默认 sparse checkout 路径."""
        assert len(GENSHIN_PATHS) > 0
        assert len(STARRAIL_PATHS) > 0

    def test_game_paths_registered(self) -> None:
        assert GAME_PATHS["genshin"] is GENSHIN_PATHS
        assert GAME_PATHS["starrail"] is STARRAIL_PATHS
