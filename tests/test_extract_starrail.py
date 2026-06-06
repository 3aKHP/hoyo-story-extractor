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

    def test_load_text_map_supports_split_language_maps(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        textmap_dir = repo / "TextMap"
        textmap_dir.mkdir(parents=True)

        textmap_dir.joinpath("TextMapKR_0.json").write_text(
            json.dumps({"1": "대사"}, ensure_ascii=False), encoding="utf-8"
        )
        textmap_dir.joinpath("TextMapKR_1.json").write_text(
            json.dumps({"2": "이름"}, ensure_ascii=False), encoding="utf-8"
        )
        textmap_dir.joinpath("TextMapMainKR.json").write_text(
            json.dumps({"3": "메인"}, ensure_ascii=False), encoding="utf-8"
        )

        ext = StarrailExtractor(str(repo), lang="KR")
        result = ext.load_text_map()
        assert result == {"1": "대사", "2": "이름", "3": "메인"}

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
                    "1000": "三月七",
                    "2000": "走吧。",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        tm.joinpath("TextMapMainCHS.json").write_text("{}", encoding="utf-8")

        # MissionChapterConfig (uses stable hash on string values) — list format
        excel = repo / "ExcelOutput"
        excel.mkdir(parents=True)
        excel.joinpath("MissionChapterConfig.json").write_text(
            json.dumps(
                [{"ID": 100001, "ChapterName": "ChapterName"}],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # MainMission (uses Hash dict) — list format
        excel.joinpath("MainMission.json").write_text(
            json.dumps(
                [
                    {
                        "MainMissionID": 10001,
                        "Name": {"Hash": 123},
                        "NextMainMissionList": [],
                        "ChapterID": 100001,
                        "RewardID": 11000201,
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # SubMission (uses Hash dict) — list format
        excel.joinpath("SubMission.json").write_text(
            json.dumps(
                [
                    {
                        "SubMissionID": 100020104,
                        "TargetText": {"Hash": 456},
                        "DescrptionText": {"Hash": 789},
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        excel.joinpath("TalkSentenceConfig.json").write_text(
            json.dumps(
                {
                    "50001": {
                        "TextmapTalkSentenceName": {"Hash": 1000},
                        "TalkSentenceText": {"Hash": 2000},
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # MissionInfo (real TurnBasedGameData hierarchy)
        mission_dir = repo / "Config" / "Level" / "Mission" / "10001"
        mission_dir.mkdir(parents=True)
        mission_dir.joinpath("MissionInfo_10001.json").write_text(
            json.dumps(
                {
                    "MainMissionID": 10001,
                    "StartSubMissionList": [100020104],
                    "FinishSubMissionList": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        mission_dir.joinpath("MissionInfo_10001.partial.json").write_text(
            json.dumps(
                {
                    "SubMissionList": [
                        {
                            "ID": 100020104,
                            "MissionJsonPath": (
                                "Config/Level/Mission/10001/Mission_100020104.json"
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        mission_dir.joinpath("Mission_100020104.json").write_text(
            json.dumps(
                {
                    "OnStartSequece": [
                        {
                            "TaskList": [
                                {
                                    "$type": "RPG.GameCore.PlayAndWaitSimpleTalk",
                                    "SimpleTalkList": [{"TalkSentenceID": 50001}],
                                },
                            ]
                        }
                    ]
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
        assert entry["submissions"][0]["sessions"][0][0]["conversations"][0]["role"] == "三月七"
        assert entry["submissions"][0]["sessions"][0][0]["conversations"][0]["content"] == "走吧。"


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
                        {
                            "ids": ["1"],
                            "target": "离开看看外面",
                            "desc": "你移开视线...",
                            "sessions": [
                                [
                                    {
                                        "type": "RPG.GameCore.PlayAndWaitSimpleTalk",
                                        "conversations": [
                                            {"role": "三月七", "content": "走吧。"}
                                        ],
                                    }
                                ]
                            ],
                        }
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
        assert "**三月七**：走吧。" in content

    def test_empty_mission_is_skipped(self, tmp_path: Path) -> None:
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

        assert files == []
        assert list(out_dir.glob("*.txt")) == []

    def test_unresolved_mission_name_uses_id_fallback(self, tmp_path: Path) -> None:
        from hoyo_story.convert import convert_starrail_quests

        jsonl = tmp_path / "quests.jsonl"
        jsonl.write_text(
            json.dumps(
                {
                    "mission": {"id": "10001", "name": {"Hash": 123}},
                    "submissions": [{"target": "离开看看外面", "desc": ""}],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir = tmp_path / "out"
        files = convert_starrail_quests(str(jsonl), str(out_dir))

        assert len(files) == 1
        path = Path(files[0])
        assert path.name == "0001_mission_10001.txt"
        assert "# mission_10001" in path.read_text(encoding="utf-8")


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

        # Story discussion JSON with OnStartSequece
        story_dir = repo / "Story" / "Discussion" / "Mission" / "10001"
        story_dir.mkdir(parents=True)
        story_dir.joinpath("DS100010101.json").write_text(
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
        assert entry["_source_type"] == "Quest"
        assert entry["_source_file"] == "DS100010101.json"

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

        story_dir = repo / "Story" / "Discussion" / "Mission" / "10002"
        story_dir.mkdir(parents=True)
        story_dir.joinpath("DS100020101.json").write_text(
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

    def test_mission_act_talks_are_classified_as_quest(self, tmp_path: Path) -> None:
        """Mission/<id>/Act 对话应归入接近原神的 Quest 分类."""
        repo = tmp_path / "repo"

        tm = repo / "TextMap"
        tm.mkdir(parents=True)
        tm.joinpath("TextMapCHS.json").write_text(
            json.dumps({"100": "三月七", "200": "走吧。"}, ensure_ascii=False),
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

        act_dir = repo / "Config" / "Level" / "Mission" / "10001" / "Act"
        act_dir.mkdir(parents=True)
        act_dir.joinpath("Act10001.json").write_text(
            json.dumps(
                {
                    "OnStartSequece": [
                        {
                            "TaskList": [
                                {
                                    "$type": "RPG.GameCore.PlayAndWaitSimpleTalk",
                                    "SimpleTalkList": [{"TalkSentenceID": 50001}],
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

        entry = json.loads(out.read_text(encoding="utf-8").strip())
        assert entry["_source_type"] == "Quest"

    def test_rogue_dialogue_play_simple_talk_is_extracted(
        self,
        tmp_path: Path,
    ) -> None:
        repo = tmp_path / "repo"

        tm = repo / "TextMap"
        tm.mkdir(parents=True)
        tm.joinpath("TextMapCHS.json").write_text(
            json.dumps({"100": "黑塔", "200": "模拟宇宙启动。"}, ensure_ascii=False),
            encoding="utf-8",
        )
        tm.joinpath("TextMapMainCHS.json").write_text("{}", encoding="utf-8")

        excel = repo / "ExcelOutput"
        excel.mkdir(parents=True)
        excel.joinpath("TalkSentenceConfig.json").write_text(
            json.dumps(
                {
                    "9001": {
                        "TextmapTalkSentenceName": {"Hash": 100},
                        "TalkSentenceText": {"Hash": 200},
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        rogue_dir = repo / "Config" / "Level" / "RogueDialogue" / "82101"
        rogue_dir.mkdir(parents=True)
        rogue_dir.joinpath("821010001.json").write_text(
            json.dumps(
                {
                    "OnStartSequece": [
                        {
                            "TaskList": [
                                {
                                    "$type": "RPG.GameCore.PlaySimpleTalk",
                                    "SimpleTalkList": [{"TalkSentenceID": 9001}],
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

        entry = json.loads(out.read_text(encoding="utf-8").strip())
        assert entry["_source_type"] == "Rogue"
        conv = entry["sessions"][0][0]["conversations"][0]
        assert conv["role"] == "黑塔"
        assert conv["content"] == "模拟宇宙启动。"


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


class TestExtractAvatars:
    """StarrailExtractor.extract_avatars 的测试."""

    def test_extract_avatars_end_to_end(self, tmp_path: Path) -> None:
        """完整流程：TextMap + AvatarConfig + atlas/profile/voice → JSONL."""
        repo = tmp_path / "repo"

        tm = repo / "TextMap"
        tm.mkdir(parents=True)
        tm.joinpath("TextMapCHS.json").write_text(
            json.dumps(
                {
                    "100": "三月七",
                    "200": "冰属性角色",
                    "300": "角色详情",
                    "301": "喜欢拍照的列车乘员。",
                    "302": "初次见面",
                    "303": "你好，开拓者。",
                    "304": "秦且歌",
                    "305": "星穹列车",
                    "306": "毁灭",
                    "307": "角色活动跃迁",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        tm.joinpath("TextMapMainCHS.json").write_text("{}", encoding="utf-8")

        excel = repo / "ExcelOutput"
        excel.mkdir(parents=True)
        excel.joinpath("AvatarConfig.json").write_text(
            json.dumps(
                [
                    {
                        "AvatarID": 1001,
                        "AvatarName": {"Hash": 100},
                        "AvatarDesc": {"Hash": 200},
                        "DamageType": "Ice",
                        "AvatarBaseType": "Warrior",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        excel.joinpath("StoryAtlasTextmap.json").write_text(
            json.dumps(
                [{"StoryID": 1, "StoryName": {"Hash": 300}}],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        excel.joinpath("StoryAtlas.json").write_text(
            json.dumps(
                [
                    {
                        "AvatarID": 1001,
                        "StoryID": 1,
                        "Story": {"Hash": 301},
                        "Unlock": "Default",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        excel.joinpath("VoiceAtlas.json").write_text(
            json.dumps(
                [
                    {
                        "AvatarID": 1001,
                        "VoiceID": 1,
                        "VoiceTitle": {"Hash": 302},
                        "Voice_M": {"Hash": 303},
                        "SortID": 1,
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        excel.joinpath("AvatarAtlas.json").write_text(
            json.dumps(
                [{"AvatarID": 1001, "CV_CN": {"Hash": 304}, "CampID": 100}],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        excel.joinpath("AvatarCamp.json").write_text(
            json.dumps(
                [{"ID": 100, "Name": {"Hash": 305}}],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        excel.joinpath("AvatarBaseType.json").write_text(
            json.dumps(
                [{"ID": "Warrior", "BaseTypeText": {"Hash": 306}}],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        excel.joinpath("AvatarComefrom.json").write_text(
            json.dumps(
                [{"ID": 1001, "Desc": {"Hash": 307}}],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        ext = StarrailExtractor(str(repo))
        out = tmp_path / "avatars_CHS.jsonl"
        result_path = ext.extract_avatars(str(out))

        assert result_path == str(out)
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        avatar = json.loads(lines[0])
        assert avatar["name"] == "三月七"
        assert avatar["AvatarDesc"] == "冰属性角色"
        assert avatar["DamageType"] == "Ice"
        assert avatar["AvatarBaseTypeName"] == "毁灭"
        assert avatar["Camp"] == "星穹列车"
        assert avatar["Comefrom"] == "角色活动跃迁"
        assert avatar["cv"]["CV_CN"] == "秦且歌"
        assert avatar["stories"][0]["title"] == "角色详情"
        assert avatar["stories"][0]["content"] == "喜欢拍照的列车乘员。"
        assert avatar["voices"][0]["title"] == "初次见面"
        assert avatar["voices"][0]["content"] == "你好，开拓者。"

    def test_extract_avatars_missing_file_raises(self, tmp_path: Path) -> None:
        ext = StarrailExtractor(str(tmp_path / "repo"))
        with pytest.raises(FileNotFoundError):
            ext.extract_avatars()


class TestExtractMisc:
    """StarrailExtractor.extract_misc 的测试."""

    def test_extract_misc_items(self, tmp_path: Path) -> None:
        """完整流程：TextMap + ItemConfig → JSONL."""
        repo = tmp_path / "repo"

        tm = repo / "TextMap"
        tm.mkdir(parents=True)
        tm.joinpath("TextMapCHS.json").write_text(
            json.dumps(
                {"100": "信用点", "200": "星际和平公司发行的货币"},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        tm.joinpath("TextMapMainCHS.json").write_text("{}", encoding="utf-8")

        excel = repo / "ExcelOutput"
        excel.mkdir(parents=True)
        excel.joinpath("ItemConfig.json").write_text(
            json.dumps(
                [
                    {
                        "ID": 2,
                        "ItemName": {"Hash": 100},
                        "ItemDesc": {"Hash": 200},
                        "Rarity": "Rare",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        ext = StarrailExtractor(str(repo))
        out_dir = tmp_path / "misc"
        results = ext.extract_misc(str(out_dir))

        assert "items" in results
        lines = Path(results["items"]).read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        item = json.loads(lines[0])
        assert item["name"] == "信用点"
        assert item["desc"] == "星际和平公司发行的货币"
        assert item["Rarity"] == "Rare"

    def test_extract_misc_skips_test_names(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"

        tm = repo / "TextMap"
        tm.mkdir(parents=True)
        tm.joinpath("TextMapCHS.json").write_text(
            json.dumps({"100": "test_item"}, ensure_ascii=False),
            encoding="utf-8",
        )
        tm.joinpath("TextMapMainCHS.json").write_text("{}", encoding="utf-8")

        excel = repo / "ExcelOutput"
        excel.mkdir(parents=True)
        excel.joinpath("ItemConfig.json").write_text(
            json.dumps(
                [{"ID": 1, "ItemName": {"Hash": 100}}],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        ext = StarrailExtractor(str(repo))
        with pytest.raises(ValueError):
            ext.extract_misc()


class TestConvertStarrailAvatars:
    """convert_starrail_avatars 的测试."""

    def test_single_avatar(self, tmp_path: Path) -> None:
        from hoyo_story.convert import convert_starrail_avatars

        jsonl = tmp_path / "avatars.jsonl"
        jsonl.write_text(
            json.dumps(
                {
                    "id": "1001",
                    "name": "三月七",
                    "AvatarDesc": "冰属性角色\\n来自列车",
                    "DamageType": "Ice",
                    "AvatarBaseTypeName": "存护",
                    "Rarity": "CombatPowerAvatarRarityType4",
                    "Camp": "星穹列车",
                    "Comefrom": "角色活动跃迁",
                    "cv": {"CV_CN": "秦且歌"},
                    "stories": [
                        {
                            "title": "角色详情",
                            "content": "精灵古怪的少女。\\n<i>喜欢拍照。</i>",
                        }
                    ],
                    "voices": [
                        {"title": "初次见面", "content": "你好，{NICKNAME}。"}
                    ],
                    "JsonPath": "Config/ConfigCharacter/Avatar.json",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir = tmp_path / "out"
        files = convert_starrail_avatars(str(jsonl), str(out_dir))

        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# 三月七" in content
        assert "冰属性角色\n来自列车" in content
        assert "**属性**: Ice" in content
        assert "**命途**: 存护" in content
        assert "**稀有度**: 4星" in content
        assert "**阵营**: 星穹列车" in content
        assert "**中文 CV**: 秦且歌" in content
        assert "## 档案" in content
        assert "### 角色详情" in content
        assert "精灵古怪的少女。\n喜欢拍照。" in content
        assert "## 语音" in content
        assert "**初次见面**：你好，{NICKNAME}。" in content
        assert "JsonPath" not in content

    def test_duplicate_names_do_not_overwrite(self, tmp_path: Path) -> None:
        from hoyo_story.convert import convert_starrail_avatars

        jsonl = tmp_path / "avatars.jsonl"
        jsonl.write_text(
            "\n".join(
                [
                    json.dumps(
                        {"id": "8001", "name": "{NICKNAME}", "AvatarDesc": "男主"},
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {"id": "8002", "name": "{NICKNAME}", "AvatarDesc": "女主"},
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir = tmp_path / "out"
        files = convert_starrail_avatars(str(jsonl), str(out_dir))

        assert len(files) == 2
        assert Path(files[0]).name == "0001_{NICKNAME}.txt"
        assert Path(files[1]).name == "0002_{NICKNAME}.txt"
        assert len(list(out_dir.glob("*.txt"))) == 2

    def test_metadata_only_avatar_is_skipped(self, tmp_path: Path) -> None:
        from hoyo_story.convert import convert_starrail_avatars

        jsonl = tmp_path / "avatars.jsonl"
        jsonl.write_text(
            json.dumps(
                {
                    "id": "8003",
                    "name": "{NICKNAME}",
                    "DamageType": "Fire",
                    "AvatarBaseTypeName": "存护",
                    "Rarity": "CombatPowerAvatarRarityType5",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir = tmp_path / "out"
        files = convert_starrail_avatars(str(jsonl), str(out_dir))

        assert files == []
        assert list(out_dir.glob("*.txt")) == []


class TestConvertStarrailMisc:
    """convert_starrail_misc 的测试."""

    def test_single_item(self, tmp_path: Path) -> None:
        from hoyo_story.convert import convert_starrail_misc

        jsonl = tmp_path / "misc.jsonl"
        jsonl.write_text(
            json.dumps(
                {
                    "id": "2",
                    "name": "信用点",
                    "desc": "星际货币\\n<i>通用货币</i>",
                    "Rarity": "Rare",
                    "ItemIconPath": "SpriteOutput/ItemIcon/2.png",
                    "ItemBGDesc": "duplicate",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir = tmp_path / "out"
        files = convert_starrail_misc(str(jsonl), str(out_dir))

        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# 信用点" in content
        assert "星际货币\n通用货币" in content
        assert "**Rarity**: Rare" in content
        assert "ItemIconPath" not in content
        assert "ItemBGDesc" not in content

    def test_item_without_description_is_skipped(self, tmp_path: Path) -> None:
        from hoyo_story.convert import convert_starrail_misc

        jsonl = tmp_path / "misc.jsonl"
        jsonl.write_text(
            json.dumps(
                {
                    "id": "23",
                    "name": "活跃度",
                    "ItemMainType": "Virtual",
                    "Rarity": "Rare",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        out_dir = tmp_path / "out"
        files = convert_starrail_misc(str(jsonl), str(out_dir))

        assert files == []
        assert list(out_dir.glob("*.txt")) == []
