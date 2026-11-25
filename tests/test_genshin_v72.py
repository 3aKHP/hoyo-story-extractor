"""Synthetic coverage for the plaintext schema in Genshin 7.2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hoyo_story.convert import convert_avatars, convert_quests, convert_talks
from hoyo_story.extract.base import detect_quest_version, resolve_quest_keys
from hoyo_story.extract.genshin import GenshinExtractor


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.mark.parametrize("version", [None, "7.2"])
def test_plaintext_quest_titles_and_dialogue(tmp_path: Path, version: str | None) -> None:
    quest = {
        "chapterNum": {"textId": "第七章"},
        "chapterTitle": {"textId": "虚构章节"},
        "mainQuestDesp": {"textId": "虚构任务简介"},
        "mainQuestTitle": {"textId": "虚构任务标题"},
        "subQuests": [{
            "subQuestTitle": {"textId": "寻找朋友"},
            "items": [{
                "speakerText": {"textId": "测试角色"},
                "dialogs": [{"text": {"textId": "今天一起出发吧。"}}],
            }],
        }],
    }
    source = tmp_path / "quest.jsonl"
    source.write_text(json.dumps(quest, ensure_ascii=False) + "\n", encoding="utf-8")
    assert detect_quest_version(quest) == "7.2"
    assert resolve_quest_keys("7.2")["text"] == "textId"
    files = convert_quests(str(source), str(tmp_path / "out"), data_version=version)
    assert len(files) == 1
    body = Path(files[0]).read_text(encoding="utf-8")
    assert body.startswith("# 虚构任务标题\n")
    assert "*虚构任务简介*" in body
    assert "第七章" in body and "虚构章节" in body
    assert "### 寻找朋友" in body
    assert "**测试角色**：今天一起出发吧。" in body


def test_plaintext_talk_names_and_npc_lookup(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    _write(raw / "TextMap/TextMapCHS.json", {
        "90001": "村民", "90002": "来自 NPC 的内容。",
        "90003": "匿名的内容。", "90004": "自定义称呼",
        "90005": "覆盖称呼的内容。", "90006": "玩家选择。",
    })
    _write(raw / "TextMap/TextMap_MediumCHS.json", {})
    _write(raw / "ExcelBinOutput/NpcExcelConfigData.json", [
        {"id": 101, "nameTextMapHash": 90001},
        {"id": 999, "nameTextMapHash": 999999},
    ])
    _write(raw / "BinOutput/Talk/Npc/100.json", {"talkId": 100, "dialogList": [
        {"talkRole": {"type": "TALK_ROLE_NPC", "id": "101"},
         "talkContentTextMapHash": 90002},
        {"talkRole": {"type": "TALK_ROLE_NPC", "_id": "101"},
         "talkRoleNameTextMapHash": 90004, "talkContentTextMapHash": 90005},
        {"talkRole": {"type": "TALK_ROLE_NPC", "id": "999"},
         "talkContentTextMapHash": 90003},
        {"talkRole": {"type": "TALK_ROLE_PLAYER"}, "talkContentTextMapHash": 90006},
    ]})
    jp = GenshinExtractor(str(raw)).extract_talks(str(tmp_path / "talks.jsonl"))
    files = convert_talks(jp, str(tmp_path / "out"))
    body = Path(files[0]).read_text(encoding="utf-8")
    assert "**村民**：来自 NPC 的内容。" in body
    assert "**自定义称呼**：覆盖称呼的内容。" in body
    assert "匿名的内容。" in body
    assert "**999**" not in body
    assert "**旅行者**：玩家选择。" in body


@pytest.mark.parametrize(("list_key", "speaker_key", "content_key", "id_key"), [
    ("LOJEOMAPIIM", "HJIPOJOECIF", "CMKPOJOEHHA", "LBPGKDMGFBN"),
    ("KJNKFMPAGAA", "IFAOOKCBDGD", "EMKCOIBADBJ", "PBAEPDPNKEJ"),
    ("AAOAAFLLOJI", "HJLEMJIGNFE", "BDOKCLNNDGN", "FEOACBMDCKJ"),
])
def test_retained_talk_formats(
    tmp_path: Path, list_key: str, speaker_key: str, content_key: str, id_key: str,
) -> None:
    talk = {"_talk_type": "Npc", id_key: 123, list_key: [{
        speaker_key: {"type": "TALK_ROLE_PLAYER"}, content_key: "保留格式的对话。",
    }]}
    source = tmp_path / "talk.jsonl"
    source.write_text(json.dumps(talk, ensure_ascii=False) + "\n", encoding="utf-8")
    files = convert_talks(str(source), str(tmp_path / "out"))
    assert len(files) == 1
    assert "**旅行者**：保留格式的对话。" in Path(files[0]).read_text(encoding="utf-8")


def test_avatar_display_names_do_not_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "avatars.jsonl"
    entries = [
        {"id": "1", "name": "同名角色", "desc": "第一份档案。"},
        {"id": "2", "name": "同名角色", "desc": "第二份档案。"},
    ]
    source.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in entries),
                      encoding="utf-8")
    files = convert_avatars(str(source), str(tmp_path / "out"))
    assert len(files) == len(set(files)) == 2
    assert "第一份档案。" in Path(files[0]).read_text(encoding="utf-8")
    assert "第二份档案。" in Path(files[1]).read_text(encoding="utf-8")
