"""测试 extract/starrail.py 星铁提取器."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hoyo_story.extract.starrail import StarrailExtractor, get_stable_hash


class TestStableHash:
    """stable hash 算法的测试."""

    def test_empty_string(self) -> None:
        """空字符串的 stable hash 是已知的 371857150."""
        assert get_stable_hash("") == 371857150

    def test_known_string(self) -> None:
        """已知字符串产生预期哈希值."""
        assert get_stable_hash("ChapterName") == 981257900
        assert get_stable_hash("SkillPointName_1001101") == 2078331665

    def test_consistency(self) -> None:
        """同一字符串多次计算结果一致."""
        assert get_stable_hash("test") == get_stable_hash("test")

    def test_different_strings_different_hashes(self) -> None:
        """不同字符串产生不同哈希（大概率）."""
        assert get_stable_hash("a") != get_stable_hash("b")

    def test_32bit_range(self) -> None:
        """返回值在 32-bit 无符号整数范围内."""
        h = get_stable_hash("x" * 1000)
        assert 0 <= h <= 0xFFFFFFFF


class TestStarrailExtractor:
    """StarrailExtractor 的测试."""

    def test_game_name(self) -> None:
        assert StarrailExtractor.game_name == "starrail"

    def test_text_map_paths_format(self) -> None:
        assert len(StarrailExtractor.text_map_paths) == 2
        for path in StarrailExtractor.text_map_paths:
            assert "{lang}" in path, f"路径应包含 {{lang}} 占位符: {path}"

    def test_init_stores_raw_path_and_lang(self) -> None:
        ext = StarrailExtractor("/tmp/starrail_raw", lang="JP")
        assert ext.raw_repo_path == "/tmp/starrail_raw"
        assert ext.lang == "JP"

    def test_init_default_lang(self) -> None:
        ext = StarrailExtractor("/tmp/starrail_raw")
        assert ext.lang == "CHS"

    def test_load_text_map_merges_both(self, tmp_path: Path) -> None:
        """验证 TextMap + TextMapMain 被正确合并."""
        repo = tmp_path / "repo"
        textmap_dir = repo / "TextMap"
        textmap_dir.mkdir(parents=True)

        textmap_dir.joinpath("TextMapCHS.json").write_text(
            json.dumps({"1": "对话内容"}, ensure_ascii=False), encoding="utf-8"
        )
        textmap_dir.joinpath("TextMapMainCHS.json").write_text(
            json.dumps({"2": "角色名"}, ensure_ascii=False), encoding="utf-8"
        )

        ext = StarrailExtractor(str(repo))
        result = ext.load_text_map()
        assert result == {"1": "对话内容", "2": "角色名"}

    def test_load_talk_sentence_map(self, tmp_path: Path) -> None:
        """验证 TalkSentenceConfig.json 被正确加载."""
        repo = tmp_path / "repo"
        excel_dir = repo / "ExcelOutput"
        excel_dir.mkdir(parents=True)

        talk_data = {
            "10001": {
                "TextmapTalkSentenceName": {"Hash": 123},
                "TalkSentenceText": {"Hash": 456},
            },
            "10002": {
                "TextmapTalkSentenceName": {"Hash": 789},
                "TalkSentenceText": {"Hash": 101112},
            },
        }
        excel_dir.joinpath("TalkSentenceConfig.json").write_text(
            json.dumps(talk_data, ensure_ascii=False), encoding="utf-8"
        )

        ext = StarrailExtractor(str(repo))
        result = ext._load_talk_sentence_map()
        assert result == talk_data

    def test_load_talk_sentence_map_missing_raises(self, tmp_path: Path) -> None:
        """TalkSentenceConfig 缺失时抛出 FileNotFoundError."""
        ext = StarrailExtractor(str(tmp_path / "repo"))
        with pytest.raises(FileNotFoundError):
            ext._load_talk_sentence_map()
