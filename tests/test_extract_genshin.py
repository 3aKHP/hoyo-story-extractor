"""测试 extract/genshin.py 原神提取器."""

from __future__ import annotations

import json
from pathlib import Path

from hoyo_story.extract.genshin import GenshinExtractor


class TestGenshinExtractor:
    """GenshinExtractor 的测试."""

    def test_game_name(self) -> None:
        assert GenshinExtractor.game_name == "genshin"

    def test_text_map_paths_format(self) -> None:
        assert len(GenshinExtractor.text_map_paths) == 2
        for path in GenshinExtractor.text_map_paths:
            assert "{lang}" in path, f"路径应包含 {{lang}} 占位符: {path}"

    def test_quest_data_path(self) -> None:
        assert GenshinExtractor.quest_data_path == "BinOutput/CodexQuest"

    def test_init_stores_raw_path_and_lang(self) -> None:
        ext = GenshinExtractor("/tmp/genshin_raw", lang="JP")
        assert ext.raw_repo_path == "/tmp/genshin_raw"
        assert ext.lang == "JP"

    def test_init_default_lang(self) -> None:
        ext = GenshinExtractor("/tmp/genshin_raw")
        assert ext.lang == "CHS"

    def test_load_text_map_merges_both(self, tmp_path: Path) -> None:
        """验证 TextMap + TextMap_Medium 被正确合并."""
        repo = tmp_path / "repo"
        textmap_dir = repo / "TextMap"
        textmap_dir.mkdir(parents=True)

        textmap_dir.joinpath("TextMapCHS.json").write_text(
            json.dumps({"1": "对话内容"}, ensure_ascii=False), encoding="utf-8"
        )
        textmap_dir.joinpath("TextMap_MediumCHS.json").write_text(
            json.dumps({"2": "角色名"}, ensure_ascii=False), encoding="utf-8"
        )

        ext = GenshinExtractor(str(repo))
        result = ext.load_text_map()
        assert result == {"1": "对话内容", "2": "角色名"}

    def test_extract_quests_end_to_end(self, tmp_path: Path) -> None:
        """完整流程：TextMap + CodexQuest → JSONL."""
        repo = tmp_path / "repo"

        # Create TextMaps
        tm = repo / "TextMap"
        tm.mkdir(parents=True)
        tm.joinpath("TextMapCHS.json").write_text(
            json.dumps({"100": "派蒙", "200": "你好呀", "300": "再见"}, ensure_ascii=False),
            encoding="utf-8",
        )
        tm.joinpath("TextMap_MediumCHS.json").write_text(
            json.dumps({"400": "旅行者"}, ensure_ascii=False),
            encoding="utf-8",
        )

        # Create CodexQuest
        cq = repo / "BinOutput" / "CodexQuest"
        cq.mkdir(parents=True)
        cq.joinpath("0001.json").write_text(
            json.dumps(
                {
                    "title": 200,
                    "subquests": [
                        {"title": 100, "speaker": 400, "text": 300},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        ext = GenshinExtractor(str(repo))
        out = tmp_path / "quest_CHS.jsonl"
        result_path = ext.extract_quests(str(out))

        assert result_path == str(out)
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        quest = json.loads(lines[0])
        assert quest["title"] == "你好呀"
        assert quest["subquests"][0]["title"] == "派蒙"
        assert quest["subquests"][0]["speaker"] == "旅行者"
        assert quest["subquests"][0]["text"] == "再见"
