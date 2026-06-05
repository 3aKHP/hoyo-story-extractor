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

    def test_extract_quests_end_to_end(self, tmp_path: Path) -> None:
        """完整流程：TextMap + ExcelOutput + MissionInfo → JSONL."""
        repo = tmp_path / "repo"

        # TextMap
        tm = repo / "TextMap"
        tm.mkdir(parents=True)
        tm.joinpath("TextMapCHS.json").write_text(
            json.dumps(
                {
                    "981257900": "第一章",  # stable_hash("ChapterName")
                    "123": "风暴之眼",      # MainMission Name
                    "456": "离开看看外面",   # SubMission TargetText
                    "789": "你移开视线...",  # SubMission DescrptionText
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        tm.joinpath("TextMapMainCHS.json").write_text("{}", encoding="utf-8")

        # MissionChapterConfig (uses stable hash on string values)
        excel = repo / "ExcelOutput"
        excel.mkdir(parents=True)
        excel.joinpath("MissionChapterConfig.json").write_text(
            json.dumps(
                {"100001": {"ChapterName": "ChapterName"}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # MainMission (uses Hash dict)
        excel.joinpath("MainMission.json").write_text(
            json.dumps(
                {
                    "10001": {
                        "Name": {"Hash": 123},
                        "NextMainMissionList": [],
                        "ChapterID": 100001,
                        "RewardID": 11000201,
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # SubMission (uses Hash dict)
        excel.joinpath("SubMission.json").write_text(
            json.dumps(
                {
                    "100020104": {
                        "TargetText": {"Hash": 456},
                        "DescrptionText": {"Hash": 789},
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # MissionInfo (hierarchy)
        mission_dir = repo / "Config" / "Level" / "Mission" / "10001"
        mission_dir.mkdir(parents=True)
        mission_dir.joinpath("MissionInfo_10001.json").write_text(
            json.dumps(
                {
                    "MainMissionID": 10001,
                    "SubMissionList": [{"ID": 100020104}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        ext = StarrailExtractor(str(repo))
        out = tmp_path / "quests_CHS.jsonl"
        result_path = ext.extract_quests(str(out))

        assert result_path == str(out)
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["mission"]["name"] == "风暴之眼"
        assert entry["mission"]["chapter_id"] == "100001"
        assert entry["mission"]["chapter"]["ChapterName"] == "第一章"
        assert len(entry["submissions"]) == 1
        assert entry["submissions"][0]["target"] == "离开看看外面"
        assert entry["submissions"][0]["desc"] == "你移开视线..."
        assert entry["submissions"][0]["ids"] == ["100020104"]


class TestConvertStarrailQuests:
    """convert_starrail_quests 的测试."""

    def test_single_mission_basic(self, tmp_path: Path) -> None:
        from hoyo_story.convert import convert_starrail_quests

        jsonl = tmp_path / "quests.jsonl"
        jsonl.write_text(
            json.dumps(
                {
                    "mission": {
                        "name": "风暴之眼",
                        "chapter": {"ChapterName": "第一章", "StageName": "第一幕"},
                    },
                    "submissions": [
                        {"ids": ["1"], "target": "离开看看外面", "desc": "你移开视线..."}
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir = tmp_path / "out"
        files = convert_starrail_quests(str(jsonl), str(out_dir))

        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# 风暴之眼" in content
        assert "> 第一章 第一幕" in content
        assert "### 离开看看外面" in content
        assert "你移开视线..." in content

    def test_empty_mission(self, tmp_path: Path) -> None:
        from hoyo_story.convert import convert_starrail_quests

        jsonl = tmp_path / "quests.jsonl"
        jsonl.write_text(
            json.dumps(
                {"mission": {"name": "空任务"}, "submissions": []},
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir = tmp_path / "out"
        files = convert_starrail_quests(str(jsonl), str(out_dir))

        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# 空任务" in content
        assert "(empty mission)" in content


class TestExtractTalks:
    """StarrailExtractor.extract_talks 的测试."""

    def test_extract_talks_end_to_end(self, tmp_path: Path) -> None:
        """完整流程：TextMap + TalkSentenceConfig + Story JSON → JSONL."""
        repo = tmp_path / "repo"

        # TextMap
        tm = repo / "TextMap"
        tm.mkdir(parents=True)
        tm.joinpath("TextMapCHS.json").write_text(
            json.dumps(
                {
                    "100": "三月七",
                    "200": "你好呀",
                    "300": "卡芙卡",
                    "400": "听我说...",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        tm.joinpath("TextMapMainCHS.json").write_text("{}", encoding="utf-8")

        # TalkSentenceConfig
        excel = repo / "ExcelOutput"
        excel.mkdir(parents=True)
        excel.joinpath("TalkSentenceConfig.json").write_text(
            json.dumps(
                {
                    "50001": {
                        "TextmapTalkSentenceName": {"Hash": 100},
                        "TalkSentenceText": {"Hash": 200},
                    },
                    "50002": {
                        "TextmapTalkSentenceName": {"Hash": 300},
                        "TalkSentenceText": {"Hash": 400},
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # Story JSON with OnStartSequece
        story_dir = repo / "Config" / "Level" / "Story"
        story_dir.mkdir(parents=True)
        story_dir.joinpath("Story_10001.json").write_text(
            json.dumps(
                {
                    "OnStartSequece": [
                        {
                            "TaskList": [
                                {
                                    "$type": "RPG.GameCore.PlayAndWaitSimpleTalk",
                                    "SimpleTalkList": [
                                        {"TalkSentenceID": 50001}
                                    ],
                                },
                                {
                                    "$type": "RPG.GameCore.PlayOptionTalk",
                                    "OptionList": [
                                        {
                                            "TalkSentenceID": 50002,
                                            "TriggerCustomString": {
                                                "Value": "TalkSentence_50003"
                                            },
                                        }
                                    ],
                                },
                                {"$type": "RPG.GameCore.EndPerformance"},
                            ]
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        ext = StarrailExtractor(str(repo))
        out = tmp_path / "talks_CHS.jsonl"
        result_path = ext.extract_talks(str(out))

        assert result_path == str(out)
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["_source_type"] == "Story"
        assert entry["_source_file"] == "Story_10001.json"

        sessions = entry["sessions"]
        assert len(sessions) == 1
        session = sessions[0]
        assert len(session) == 3  # PlayAndWaitSimpleTalk + PlayOptionTalk + EndPerformance

        # First item: simple talk
        assert session[0]["type"] == "RPG.GameCore.PlayAndWaitSimpleTalk"
        assert session[0]["conversations"][0]["role"] == "三月七"
        assert session[0]["conversations"][0]["content"] == "你好呀"

        # Second item: option talk
        assert session[1]["type"] == "RPG.GameCore.PlayOptionTalk"
        assert session[1]["options"][0]["role"] == "卡芙卡"
        assert session[1]["options"][0]["content"] == "听我说..."
        assert session[1]["options"][0]["next_talk_sentence_id"] == 50003

        # Third item: end performance
        assert session[2]["type"] == "RPG.GameCore.EndPerformance"

    def test_merge_wait_custom_string(self, tmp_path: Path) -> None:
        """验证 WaitCustomString 与 PlayAndWaitSimpleTalk 的去重合并."""
        repo = tmp_path / "repo"

        tm = repo / "TextMap"
        tm.mkdir(parents=True)
        tm.joinpath("TextMapCHS.json").write_text(
            json.dumps({"100": "三月七", "200": "重复内容"}, ensure_ascii=False),
            encoding="utf-8",
        )
        tm.joinpath("TextMapMainCHS.json").write_text("{}", encoding="utf-8")

        excel = repo / "ExcelOutput"
        excel.mkdir(parents=True)
        excel.joinpath("TalkSentenceConfig.json").write_text(
            json.dumps(
                {
                    "50001": {
                        "TextmapTalkSentenceName": {"Hash": 100},
                        "TalkSentenceText": {"Hash": 200},
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        story_dir = repo / "Config" / "Level" / "Story"
        story_dir.mkdir(parents=True)
        story_dir.joinpath("Story_10002.json").write_text(
            json.dumps(
                {
                    "OnStartSequece": [
                        {
                            "TaskList": [
                                {
                                    "$type": "RPG.GameCore.WaitCustomString",
                                    "CustomString": {"Value": "TalkSentence_50001"},
                                },
                                {
                                    "$type": "RPG.GameCore.PlayAndWaitSimpleTalk",
                                    "SimpleTalkList": [
                                        {"TalkSentenceID": 50001}
                                    ],
                                },
                                {"$type": "RPG.GameCore.EndPerformance"},
                            ]
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        ext = StarrailExtractor(str(repo))
        out = tmp_path / "talks_CHS.jsonl"
        ext.extract_talks(str(out))

        entry = json.loads(out.read_text(encoding="utf-8").strip().split("\n")[0])
        session = entry["sessions"][0]
        # WaitCustomString should be merged away (duplicate with PlayAndWaitSimpleTalk)
        assert len(session) == 2
        assert session[0]["type"] == "RPG.GameCore.PlayAndWaitSimpleTalk"
        assert session[1]["type"] == "RPG.GameCore.EndPerformance"


class TestConvertStarrailTalks:
    """convert_starrail_talks 的测试."""

    def test_single_story_basic(self, tmp_path: Path) -> None:
        from hoyo_story.convert import convert_starrail_talks

        jsonl = tmp_path / "talks.jsonl"
        jsonl.write_text(
            json.dumps(
                {
                    "_source_type": "Story",
                    "_source_file": "Story_10001.json",
                    "sessions": [
                        [
                            {
                                "type": "RPG.GameCore.PlayAndWaitSimpleTalk",
                                "conversations": [
                                    {"role": "三月七", "content": "你好呀"}
                                ],
                            },
                            {
                                "type": "RPG.GameCore.PlayOptionTalk",
                                "options": [
                                    {"role": "{NICKNAME}", "content": "选项A"}
                                ],
                            },
                        ]
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir = tmp_path / "out"
        files = convert_starrail_talks(str(jsonl), str(out_dir))

        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# Story Story_10001.json" in content
        assert "**三月七**：你好呀" in content
        assert "> {NICKNAME}：选项A" in content

    def test_empty_talk_skipped(self, tmp_path: Path) -> None:
        from hoyo_story.convert import convert_starrail_talks

        jsonl = tmp_path / "talks.jsonl"
        jsonl.write_text(
            json.dumps(
                {
                    "_source_type": "Story",
                    "_source_file": "Empty.json",
                    "sessions": [],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir = tmp_path / "out"
        files = convert_starrail_talks(str(jsonl), str(out_dir))
        assert len(files) == 0
