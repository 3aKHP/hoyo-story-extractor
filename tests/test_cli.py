"""CLI behavior tests."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from hoyo_story.cli import app

runner = CliRunner()


def _write_minimal_genshin_raw(raw: Path) -> None:
    textmap = raw / "TextMap"
    quest_dir = raw / "BinOutput" / "CodexQuest"
    textmap.mkdir(parents=True)
    quest_dir.mkdir(parents=True)

    (textmap / "TextMapCHS.json").write_text(
        json.dumps({"100": "测试任务", "200": "任务描述", "300": "第一章", "500": "你好"}),
        encoding="utf-8",
    )
    (textmap / "TextMap_MediumCHS.json").write_text(
        json.dumps({"400": "派蒙"}, ensure_ascii=False),
        encoding="utf-8",
    )

    quest = {
        "HGCJLMOIAFL": {"OPKOJIEHJAE": 100},
        "PIPCMJHBHAH": {"OPKOJIEHJAE": 200},
        "JBANEJCMNHJ": {"OPKOJIEHJAE": 300},
        "IKECHKLEFFK": [
            {
                "CGJPNLJCKKB": {"OPKOJIEHJAE": 100},
                "DLLOBLBEBPM": [
                    {
                        "KDDMHACHOGH": {"OPKOJIEHJAE": 400},
                        "JOIPGFEDKFO": [
                            {"LEMPMANEBOB": {"OPKOJIEHJAE": 500}},
                        ],
                    }
                ],
            }
        ],
    }
    (quest_dir / "0001.json").write_text(
        json.dumps(quest, ensure_ascii=False),
        encoding="utf-8",
    )


def test_fetch_missing_env_is_user_friendly(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("GENSHIN_RAW_REPO", raising=False)

    result = runner.invoke(app, ["fetch", "genshin", str(tmp_path / "raw")])

    assert result.exit_code == 1
    assert "GENSHIN_RAW_REPO" in result.output
    assert "Traceback" not in result.output


def test_unimplemented_game_is_rejected_without_traceback(tmp_path: Path) -> None:
    result = runner.invoke(app, ["pipeline", "starrail", str(tmp_path), str(tmp_path / "out")])

    assert result.exit_code != 0
    assert "planned but not implemented" in result.output
    assert "Traceback" not in result.output


def test_pipeline_missing_raw_path_fails_without_empty_success(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "pipeline",
            "genshin",
            str(tmp_path / "missing"),
            str(tmp_path / "out"),
            "--type",
            "quests",
        ],
    )

    assert result.exit_code == 1
    assert "Missing TextMap" in result.output
    assert "✓ 0 files" not in result.output
    assert "Traceback" not in result.output


def test_pipeline_genshin_quests_minimal_smoke(tmp_path: Path, monkeypatch) -> None:
    raw = tmp_path / "raw"
    out = tmp_path / "out"
    _write_minimal_genshin_raw(raw)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["pipeline", "genshin", str(raw), str(out), "--type", "quests"],
    )

    assert result.exit_code == 0
    files = list(out.glob("*.txt"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "**派蒙**：你好" in content
