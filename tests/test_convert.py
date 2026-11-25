"""测试 convert.py 的转换逻辑."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hoyo_story import convert
from hoyo_story.convert import convert_jsonl_to_txt, convert_quests


def _make_quest_jsonl_line(
    title: str = "测试任务",
    description: str = "这是任务描述",
    chapter: str = "第一章",
    subquests: list[dict] | None = None,
) -> str:
    """Build a synthetic JSONL line matching the post-replace_hashes quest format."""
    quest: dict = {
        "HGCJLMOIAFL": {"OPKOJIEHJAE": title, "JAJHEIKBFAF": "ChapterTitle"},
        "PIPCMJHBHAH": {"OPKOJIEHJAE": description, "JAJHEIKBFAF": "MainQuestDesp"},
        "JBANEJCMNHJ": {"OPKOJIEHJAE": chapter, "JAJHEIKBFAF": "ChapterNum"},
        "IKECHKLEFFK": subquests or [],
    }
    return json.dumps(quest, ensure_ascii=False)


def _make_quest_jsonl_line_v70(
    title: str = "测试任务",
    description: str = "这是任务描述",
    chapter: str = "第一章",
    subquests: list[dict] | None = None,
) -> str:
    """Build a synthetic JSONL line matching the v7.0 post-replace_hashes quest format."""
    quest: dict = {
        "ALOHJMPDFKI": {"BNJEGIAOKGM": title, "JOBGILDNLEL": "ChapterTitle"},
        "CBLIMBBBKNK": {"BNJEGIAOKGM": description, "JOBGILDNLEL": "MainQuestDesp"},
        "NNPJABOAJPL": {"BNJEGIAOKGM": chapter, "JOBGILDNLEL": "ChapterNum"},
        "EBNBLBEIFFJ": subquests or [],
    }
    return json.dumps(quest, ensure_ascii=False)


def _make_subquest(
    title: str, items: list[dict] | None = None
) -> dict:
    return {
        "CGJPNLJCKKB": {"OPKOJIEHJAE": title, "JAJHEIKBFAF": "SubQuestTitle"},
        "DLLOBLBEBPM": items or [],
    }


def _make_dialog_item(
    speaker: str, dialogs: list[str]
) -> dict:
    return {
        "KDDMHACHOGH": {"OPKOJIEHJAE": speaker, "JAJHEIKBFAF": "SpeakerKnown"},
        "JOIPGFEDKFO": [
            {
                "LEMPMANEBOB": {
                    "OPKOJIEHJAE": d,
                    "JAJHEIKBFAF": "DialogNormal",
                }
            }
            for d in dialogs
        ],
    }


def _make_subquest_v70(
    title: str, items: list[dict] | None = None
) -> dict:
    return {
        "OGEGCCLHIHP": {"BNJEGIAOKGM": title, "JOBGILDNLEL": "SubQuestTitle"},
        "PEAKPGNONFA": items or [],
    }


def _make_dialog_item_v70(
    speaker: str, dialogs: list[str]
) -> dict:
    return {
        "IILBCFJNPGA": {"BNJEGIAOKGM": speaker, "JOBGILDNLEL": "SpeakerKnown"},
        "OFKGPGLHIDJ": [
            {
                "JGPDCLOJKLC": {
                    "BNJEGIAOKGM": d,
                    "JOBGILDNLEL": "DialogNormal",
                }
            }
            for d in dialogs
        ],
    }


class TestConvert:
    """convert_jsonl_to_txt 的测试."""

    def test_single_quest_basic(self, tmp_path: Path) -> None:
        """基本 quest 转换：标题 + 子任务 + 对话."""
        jsonl = tmp_path / "quest_CHS.jsonl"
        jsonl.write_text(
            _make_quest_jsonl_line(
                title="测试任务",
                description="这是描述",
                chapter="第一章",
                subquests=[
                    _make_subquest(
                        "与NPC交谈",
                        items=[
                            _make_dialog_item("派蒙", ["你好！", "再见！"]),
                        ],
                    ),
                ],
            )
            + "\n",
            encoding="utf-8",
        )

        out = tmp_path / "output"
        files = convert_jsonl_to_txt(str(jsonl), str(out))

        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# 测试任务" in content
        assert "*这是描述*" in content
        assert "> 第一章" in content
        assert "### 与NPC交谈" in content
        assert "**派蒙**：你好！" in content
        assert "**派蒙**：再见！" in content

    def test_multiple_subquests(self, tmp_path: Path) -> None:
        """多个子任务的 quest."""
        jsonl = tmp_path / "quest.jsonl"
        jsonl.write_text(
            _make_quest_jsonl_line(
                title="大型任务",
                subquests=[
                    _make_subquest("第一部分", [
                        _make_dialog_item("A", ["台词1"]),
                    ]),
                    _make_subquest("第二部分", [
                        _make_dialog_item("B", ["台词2"]),
                    ]),
                ],
            )
            + "\n",
            encoding="utf-8",
        )

        files = convert_jsonl_to_txt(str(jsonl), str(tmp_path / "out"))
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "### 第一部分" in content
        assert "### 第二部分" in content
        assert "**A**：台词1" in content
        assert "**B**：台词2" in content

    def test_empty_quest(self, tmp_path: Path) -> None:
        """空子任务列表 — 只有 title 无子任务内容时显示 (empty quest)."""
        jsonl = tmp_path / "quest.jsonl"
        # Only title, no description/chapter — so line count stays at 2
        quest = {
            "HGCJLMOIAFL": {"OPKOJIEHJAE": "空任务", "JAJHEIKBFAF": "ChapterTitle"},
            "IKECHKLEFFK": [],
        }
        jsonl.write_text(
            json.dumps(quest, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        files = convert_jsonl_to_txt(str(jsonl), str(tmp_path / "out"))
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "(empty quest)" in content

    def test_empty_subquest_skipped(self, tmp_path: Path) -> None:
        """items 为空的子任务被跳过."""
        jsonl = tmp_path / "quest.jsonl"
        jsonl.write_text(
            _make_quest_jsonl_line(
                title="任务",
                subquests=[
                    _make_subquest("空子任务", items=[]),
                    _make_subquest("有内容的", [
                        _make_dialog_item("NPC", ["说点什么"]),
                    ]),
                ],
            )
            + "\n",
            encoding="utf-8",
        )

        files = convert_jsonl_to_txt(str(jsonl), str(tmp_path / "out"))
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "空子任务" not in content  # skipped because no items
        assert "### 有内容的" in content

    def test_speakerless_dialog(self, tmp_path: Path) -> None:
        """无说话人的旁白."""
        jsonl = tmp_path / "quest.jsonl"
        quest = {
            "IKECHKLEFFK": [
                {
                    "CGJPNLJCKKB": {"OPKOJIEHJAE": "舞台指示", "JAJHEIKBFAF": "SubQuestTitle"},
                    "DLLOBLBEBPM": [
                        {
                            "KDDMHACHOGH": {"OPKOJIEHJAE": "", "JAJHEIKBFAF": ""},
                            "JOIPGFEDKFO": [
                                {"LEMPMANEBOB": {"OPKOJIEHJAE": "（远处传来钟声）"}}
                            ],
                        },
                    ],
                },
            ],
        }
        jsonl.write_text(json.dumps(quest, ensure_ascii=False) + "\n", encoding="utf-8")

        files = convert_jsonl_to_txt(str(jsonl), str(tmp_path / "out"))
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "（远处传来钟声）" in content


class TestConvertV70:
    """v7.0 数据格式的 quest 转换."""

    def _write_quest(self, tmp_path: Path, line: str) -> Path:
        jsonl = tmp_path / "quest_v70.jsonl"
        jsonl.write_text(line + "\n", encoding="utf-8")
        return jsonl

    def test_single_quest_basic(self, tmp_path: Path) -> None:
        jsonl = self._write_quest(
            tmp_path,
            _make_quest_jsonl_line_v70(
                title="测试任务",
                description="这是描述",
                chapter="第一章",
                subquests=[
                    _make_subquest_v70(
                        "与NPC交谈",
                        items=[
                            _make_dialog_item_v70("派蒙", ["你好！", "再见！"]),
                        ],
                    ),
                ],
            ),
        )
        out = tmp_path / "output"
        files = convert_quests(str(jsonl), str(out))

        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# 测试任务" in content
        assert "*这是描述*" in content
        assert "> 第一章" in content
        assert "### 与NPC交谈" in content
        assert "**派蒙**：你好！" in content
        assert "**派蒙**：再见！" in content

    def test_auto_detect_v70(self, tmp_path: Path) -> None:
        """不传 data_version 时自动探测 7.0."""
        jsonl = self._write_quest(
            tmp_path,
            _make_quest_jsonl_line_v70(
                title="自动探测",
                subquests=[
                    _make_subquest_v70("子任务", [
                        _make_dialog_item_v70("A", ["台词"]),
                    ]),
                ],
            ),
        )
        files = convert_quests(str(jsonl), str(tmp_path / "out"))
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# 自动探测" in content
        assert "**A**：台词" in content

    def test_explicit_data_version(self, tmp_path: Path) -> None:
        """显式传 data_version='7.0'."""
        jsonl = self._write_quest(
            tmp_path,
            _make_quest_jsonl_line_v70(
                title="显式版本",
                subquests=[
                    _make_subquest_v70("子任务", [
                        _make_dialog_item_v70("B", ["台词2"]),
                    ]),
                ],
            ),
        )
        files = convert_quests(str(jsonl), str(tmp_path / "out"), data_version="7.0")
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "**B**：台词2" in content

    def test_unknown_version_raises(self, tmp_path: Path) -> None:
        jsonl = self._write_quest(
            tmp_path,
            _make_quest_jsonl_line_v70(subquests=[]),
        )
        with pytest.raises(ValueError, match="Unknown genshin data version"):
            convert_quests(str(jsonl), str(tmp_path / "out"), data_version="9.9")

    def test_empty_subquest_skipped(self, tmp_path: Path) -> None:
        jsonl = self._write_quest(
            tmp_path,
            _make_quest_jsonl_line_v70(
                title="任务",
                subquests=[
                    _make_subquest_v70("空子任务", items=[]),
                    _make_subquest_v70("有内容的", [
                        _make_dialog_item_v70("NPC", ["说点什么"]),
                    ]),
                ],
            ),
        )
        files = convert_quests(str(jsonl), str(tmp_path / "out"))
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "空子任务" not in content
        assert "### 有内容的" in content


class TestConvertTalksV70:
    """v7.0 Talk 格式转换(新混淆 key + 明文 key + Group 跳过)."""

    def _write_talks(self, tmp_path: Path, lines: list[str]) -> Path:
        jsonl = tmp_path / "talks_v70.jsonl"
        jsonl.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return jsonl

    def test_new_obfuscated_format(self, tmp_path: Path) -> None:
        """7.0 新混淆 key 格式 (PFALHAKIILD)."""
        talk = {
            "PFALHAKIILD": [
                {
                    "LFGCLNLPAPB": {"_id": "7540", "_type": "TALK_ROLE_NPC", "_roleId": 0},
                    "OACNIBLFFDI": "你好，旅行者！",
                },
                {
                    "LFGCLNLPAPB": {"_id": "", "_type": "TALK_ROLE_PLAYER", "_roleId": 0},
                    "OACNIBLFFDI": "再见！",
                },
            ],
            "IOKNFDJFGDH": 7767403,
            "_talk_type": "Npc",
            "_talk_file": "0fa78cac.json",
        }
        jsonl = self._write_talks(tmp_path, [json.dumps(talk, ensure_ascii=False)])
        files = convert.convert_talks(str(jsonl), str(tmp_path / "out"))
        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# Npc Talk 7767403" in content
        assert "你好，旅行者！" in content
        assert "**旅行者**：再见！" in content

    def test_activity_format(self, tmp_path: Path) -> None:
        """7.0 Activity 新对话格式 (GDDPNNHLGBL)."""
        talk = {
            "GDDPNNHLGBL": [
                {
                    "EENIFNIGHCH": {"_id": "31073", "_roleId": 0, "_type": "TALK_ROLE_NPC"},
                    "DMIFDJDEFAL": "和明妮玩得开心吗？差不多可以回去了？",
                },
            ],
            "LDLMECNIJFC": 7567205,
            "_talk_type": "Activity",
            "_talk_file": "017176ca.json",
        }
        jsonl = self._write_talks(tmp_path, [json.dumps(talk, ensure_ascii=False)])
        files = convert.convert_talks(str(jsonl), str(tmp_path / "out"))
        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# Activity Talk 7567205" in content
        assert "和明妮玩得开心吗？差不多可以回去了？" in content

    def test_plain_key_format(self, tmp_path: Path) -> None:
        """7.0 明文 key 格式 (dialogList / talkRole / talkContentTextMapHash)."""
        talk = {
            "dialogList": [
                {
                    "talkRole": {"type": "TALK_ROLE_PLAYER", "id": ""},
                    "talkContentTextMapHash": "（除此之外没有发现什么特别之处…）",
                },
            ],
            "talkId": 330,
            "type": "Npc",
            "_talk_type": "Npc",
            "_talk_file": "plain.json",
        }
        jsonl = self._write_talks(tmp_path, [json.dumps(talk, ensure_ascii=False)])
        files = convert.convert_talks(str(jsonl), str(tmp_path / "out"))
        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "# Npc Talk 330" in content
        assert "（除此之外没有发现什么特别之处…）" in content

    def test_old_format_still_works(self, tmp_path: Path) -> None:
        """6.6 Type A 格式在 7.0 数据中仍可用."""
        talk = {
            "GALIDJOEHOC": [
                {
                    "PIBKEGJOJHN": {"_id": "1", "_type": "TALK_ROLE_NPC", "_roleId": 0},
                    "AIGJBMCHCJG": "旧格式对话",
                },
            ],
            "AADKDKPMGNO": 100,
            "HAHEIAHBPEJ": "NPC",
            "_talk_type": "Npc",
            "_talk_file": "old.json",
        }
        jsonl = self._write_talks(tmp_path, [json.dumps(talk, ensure_ascii=False)])
        files = convert.convert_talks(str(jsonl), str(tmp_path / "out"))
        assert len(files) == 1
        content = Path(files[0]).read_text(encoding="utf-8")
        assert "旧格式对话" in content

    def test_group_files_skipped(self, tmp_path: Path) -> None:
        """Group 类文件(无对话,仅条件)被跳过."""
        talk = {
            "OJACLOOEAMG": [{"EDIMJFOBEKG": "QuestDialogue/WQ/x", "AEOMIJCCDNB": "TALK_ACTIVITY"}],
            "_talk_type": "NpcGroup",
            "_talk_file": "group.json",
        }
        jsonl = self._write_talks(tmp_path, [json.dumps(talk, ensure_ascii=False)])
        files = convert.convert_talks(str(jsonl), str(tmp_path / "out"))
        assert files == []

    def test_unknown_format_skipped(self, tmp_path: Path) -> None:
        """未知格式(无任何已知 list key)被跳过."""
        talk = {"SOMETHING": [], "_talk_type": "Npc", "_talk_file": "x.json"}
        jsonl = self._write_talks(tmp_path, [json.dumps(talk, ensure_ascii=False)])
        files = convert.convert_talks(str(jsonl), str(tmp_path / "out"))
        assert files == []


class TestCleanVariables:
    """clean_variables() 的测试桩."""

    def test_not_implemented_yet(self) -> None:
        with pytest.raises(NotImplementedError):
            convert.clean_variables("test")
