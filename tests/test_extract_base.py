"""测试 extract/base.py 的公共逻辑."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hoyo_story.extract.base import (
    QUEST_KEY_MAPS,
    BaseExtractor,
    detect_quest_version,
    merge_text_maps,
    replace_hashes,
    resolve_quest_keys,
)


class TestQuestKeyMaps:
    """版本感知的 quest key 映射."""

    def test_all_versions_have_all_roles(self) -> None:
        roles = {
            "text", "speaker", "dialogs", "text_obj", "subquests", "items", "subq_title"
        }
        assert set(QUEST_KEY_MAPS) == {"6.6", "6.7", "7.0", "7.2"}
        for version, keys in QUEST_KEY_MAPS.items():
            assert set(keys) == roles, f"{version} missing roles"

    def test_versions_have_distinct_keys(self) -> None:
        # 每个版本的混淆 key 应互不相同(上游每版本重新混淆)
        for role in ("subquests", "items", "speaker"):
            seen = {QUEST_KEY_MAPS[v][role] for v in QUEST_KEY_MAPS}
            assert len(seen) == len(QUEST_KEY_MAPS), f"{role} keys not distinct across versions"

    def test_6_6_matches_module_defaults(self) -> None:
        keys = resolve_quest_keys("6.6")
        assert keys["subquests"] == "IKECHKLEFFK"
        assert keys["text"] == "OPKOJIEHJAE"
        assert keys["speaker"] == "KDDMHACHOGH"
        assert keys["dialogs"] == "JOIPGFEDKFO"
        assert keys["text_obj"] == "LEMPMANEBOB"
        assert keys["items"] == "DLLOBLBEBPM"
        assert keys["subq_title"] == "CGJPNLJCKKB"

    def test_7_0_keys(self) -> None:
        keys = resolve_quest_keys("7.0")
        assert keys["subquests"] == "EBNBLBEIFFJ"
        assert keys["text"] == "BNJEGIAOKGM"
        assert keys["speaker"] == "IILBCFJNPGA"
        assert keys["dialogs"] == "OFKGPGLHIDJ"
        assert keys["text_obj"] == "JGPDCLOJKLC"
        assert keys["items"] == "PEAKPGNONFA"
        assert keys["subq_title"] == "OGEGCCLHIHP"

    def test_resolve_unknown_version_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown genshin data version"):
            resolve_quest_keys("9.9")

    def test_detect_quest_version(self) -> None:
        assert detect_quest_version({"EBNBLBEIFFJ": []}) == "7.0"
        assert detect_quest_version({"HLCINEMBGEF": []}) == "6.7"
        assert detect_quest_version({"IKECHKLEFFK": []}) == "6.6"

    def test_detect_unknown_version_returns_empty(self) -> None:
        assert detect_quest_version({"unknown": 1}) == ""

    def test_detect_7_0_quest_does_not_match_6_6(self) -> None:
        # 7.0 quest 只含 7.0 的 key,不应误判为 6.6
        quest = {"EBNBLBEIFFJ": [], "ALOHJMPDFKI": {}, "CBLIMBBBKNK": {}}
        assert detect_quest_version(quest) == "7.0"


class TestReplaceHashes:
    """replace_hashes() 的单元测试."""

    def test_replace_int_in_dict(self) -> None:
        want = {"textId": "你好，世界"}
        assert replace_hashes({"textId": 12345}, {"12345": "你好，世界"}) == want

    def test_replace_int_in_nested_dict(self) -> None:
        text_map = {"1": "one", "2": "two"}
        result = replace_hashes(
            {"outer": {"inner": 1, "deep": {"value": 2}}}, text_map
        )
        assert result == {"outer": {"inner": "one", "deep": {"value": "two"}}}

    def test_replace_int_in_list(self) -> None:
        text_map = {"100": "hundred", "200": "two hundred"}
        assert replace_hashes([100, 200, 300], text_map) == ["hundred", "two hundred", 300]

    def test_int_not_in_map_preserved(self) -> None:
        assert replace_hashes(99999, {"1": "a"}) == 99999

    def test_string_passthrough(self) -> None:
        assert replace_hashes("hello", {"1": "a"}) == "hello"

    def test_bool_preserved(self) -> None:
        result = replace_hashes({"flag": True, "data": [False]}, {"0": "zero", "1": "one"})
        assert result == {"flag": True, "data": [False]}

    def test_empty_structures(self) -> None:
        assert replace_hashes({}, {}) == {}
        assert replace_hashes([], {}) == []
        assert replace_hashes({"a": 1}, {}) == {"a": 1}

    @pytest.mark.parametrize(
        ("obj", "text_map", "expected"),
        [
            (42, {"42": "life"}, "life"),
            (42, {}, 42),
            (None, {}, None),
            (3.14, {}, 3.14),
        ],
    )
    def test_scalar_values(self, obj, text_map, expected) -> None:
        assert replace_hashes(obj, text_map) == expected


class TestMergeTextMaps:
    """merge_text_maps() 的单元测试."""

    def test_single_file(self, tmp_path: Path) -> None:
        f = tmp_path / "map.json"
        f.write_text(json.dumps({"1": "hello", "2": "world"}), encoding="utf-8")
        result = merge_text_maps([str(f)])
        assert result == {"1": "hello", "2": "world"}

    def test_merge_two_files(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.json"
        f1.write_text(json.dumps({"1": "hello"}), encoding="utf-8")
        f2 = tmp_path / "b.json"
        f2.write_text(json.dumps({"2": "world"}), encoding="utf-8")
        result = merge_text_maps([str(f1), str(f2)])
        assert result == {"1": "hello", "2": "world"}

    def test_later_overrides_earlier(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.json"
        f1.write_text(json.dumps({"1": "old"}), encoding="utf-8")
        f2 = tmp_path / "b.json"
        f2.write_text(json.dumps({"1": "new"}), encoding="utf-8")
        result = merge_text_maps([str(f1), str(f2)])
        assert result == {"1": "new"}

    def test_missing_file_skipped(self, tmp_path: Path) -> None:
        result = merge_text_maps([str(tmp_path / "nonexistent.json")])
        assert result == {}

    def test_empty_list(self) -> None:
        assert merge_text_maps([]) == {}


class _ConcreteExtractor(BaseExtractor):
    """Minimal concrete extractor for testing the base class."""
    game_name = "test"
    text_map_paths = ["test_{lang}.json"]
    quest_data_path = "quests"


class TestBaseExtractor:
    """BaseExtractor 的单元测试."""

    def test_init_defaults(self) -> None:
        ext = _ConcreteExtractor("/tmp/repo")
        assert ext.raw_repo_path == "/tmp/repo"
        assert ext.lang == "CHS"

    def test_init_custom_lang(self) -> None:
        ext = _ConcreteExtractor("/tmp/repo", lang="JP")
        assert ext.lang == "JP"

    def test_load_text_map(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        f = repo / "test_CHS.json"
        f.write_text(json.dumps({"1": "hello"}), encoding="utf-8")

        ext = _ConcreteExtractor(str(repo))
        result = ext.load_text_map()
        assert result == {"1": "hello"}

    def test_extract_quests(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        quest_dir = repo / "quests"
        quest_dir.mkdir(parents=True)

        # Create a TextMap
        textmap = repo / "test_CHS.json"
        textmap.write_text(json.dumps({"123": "Hello World"}), encoding="utf-8")

        # Create quests with integer hashes
        quest_dir.joinpath("q1.json").write_text(
            json.dumps({"title": 123, "body": 456}), encoding="utf-8"
        )
        quest_dir.joinpath("q2.json").write_text(
            json.dumps({"title": 123, "extra": "plain"}), encoding="utf-8"
        )

        ext = _ConcreteExtractor(str(repo))
        out = tmp_path / "out.jsonl"
        result_path = ext.extract_quests(str(out))

        assert result_path == str(out)
        assert out.exists()

        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

        q1 = json.loads(lines[0])
        assert q1["title"] == "Hello World"
        assert q1["body"] == 456  # Not in text map, preserved

        q2 = json.loads(lines[1])
        assert q2["title"] == "Hello World"
        assert q2["extra"] == "plain"
