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

    def test_load_text_map_adds_v70_offset_alias(self, tmp_path: Path) -> None:
        """v6.7+ 的 Talk 内容 hash 需要 +512 偏移查询 TextMapCHS.

        TextMapCHS 中 key K 的文本,应可通过 K - 512 命中(即 Talk 文件里
        存的原始 hash H = K - 512)。同时不覆盖已有的直接命中。
        """
        repo = tmp_path / "repo"
        textmap_dir = repo / "TextMap"
        textmap_dir.mkdir(parents=True)

        textmap_dir.joinpath("TextMapCHS.json").write_text(
            json.dumps(
                {
                    "1129135042": "偏移内容",   # K = H + 512
                    "492422065": "直接内容",     # quest hash,直接命中
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        textmap_dir.joinpath("TextMap_MediumCHS.json").write_text(
            json.dumps({"2": "角色名"}, ensure_ascii=False),
            encoding="utf-8",
        )

        ext = GenshinExtractor(str(repo))
        result = ext.load_text_map()

        # 原始 key 仍在
        assert result["1129135042"] == "偏移内容"
        assert result["492422065"] == "直接内容"
        # Talk hash H = K - 512 可命中
        assert result["1129134530"] == "偏移内容"
        # Medium 内容不受影响
        assert result["2"] == "角色名"

    def test_load_text_map_offset_alias_does_not_override(self, tmp_path: Path) -> None:
        """偏移别名不覆盖已存在的直接命中."""
        repo = tmp_path / "repo"
        textmap_dir = repo / "TextMap"
        textmap_dir.mkdir(parents=True)

        textmap_dir.joinpath("TextMapCHS.json").write_text(
            json.dumps(
                {
                    "512": "偏移目标",   # K=512 → 别名 key 0
                    "0": "真实零号",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        textmap_dir.joinpath("TextMap_MediumCHS.json").write_text(
            json.dumps({}, ensure_ascii=False),
            encoding="utf-8",
        )

        ext = GenshinExtractor(str(repo))
        result = ext.load_text_map()
        # key 0 已存在(直接命中),偏移别名不覆盖
        assert result["0"] == "真实零号"

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
