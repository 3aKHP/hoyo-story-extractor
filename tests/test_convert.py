"""测试 convert.py 的转换逻辑."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hoyo_story import convert
from hoyo_story.convert import convert_jsonl_to_txt


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


class TestCleanVariables:
    """clean_variables() 的测试桩."""

    def test_not_implemented_yet(self) -> None:
        with pytest.raises(NotImplementedError):
            convert.clean_variables("test")
