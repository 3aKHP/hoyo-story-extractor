"""JSONL → .txt 转换器。

支持的数据类型：
    quests  — CodexQuest 任务剧情 (convert_quests)
    talks   — BinOutput/Talk NPC 对话 (convert_talks)
    avatars — 角色资料/语音/故事 (convert_avatars)
    misc    — 物品/武器/圣遗物 (convert_misc)
"""

from __future__ import annotations

import json
from pathlib import Path

from hoyo_story.extract.base import (
    DIALOGS_KEY,
    ITEMS_KEY,
    SPEAKER_KEY,
    SUBQ_TITLE_KEY,
    SUBQUESTS_KEY,
    TEXT_KEY,
    TEXT_OBJ_KEY,
)

# ── v6.6 Talk field keys (must match genshin.py) ─────────────────────────

TALK_A_LIST = "GALIDJOEHOC"
TALK_A_SPEAKER = "PIBKEGJOJHN"
TALK_A_CONTENT = "AIGJBMCHCJG"
TALK_A_ROLE_NAME = "BMFGJJJPBBC"
TALK_A_ID = "NFIEHACCECI"
TALK_A_TALK_ID = "AADKDKPMGNO"
TALK_A_TYPE = "HAHEIAHBPEJ"

TALK_B_LIST = "IOEDPLCPFFB"
TALK_B_SPEAKER = "DGGDDIMMIDO"
TALK_B_CONTENT = "HJJLLECCCPI"
TALK_B_ID = "GMOMCKNPBGE"


def _escape_filename(name: str) -> str:
    name = str(name)
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()[:100]


def _get_text(obj: object, key: str = TEXT_KEY) -> str:
    if isinstance(obj, dict):
        val = obj.get(key, "")
        return str(val) if val else ""
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# Quests
# ═══════════════════════════════════════════════════════════════════════════

def convert_quests(jsonl_path: str, output_dir: str) -> list[str]:
    """将 quest JSONL 转换为按 quest 分文件的 .txt。"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    count = 0

    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                quest: dict = json.loads(line)
            except json.JSONDecodeError:
                continue

            count += 1
            lines: list[str] = []

            quest_title = ""
            top_texts: list[str] = []
            for _key, value in quest.items():
                if isinstance(value, dict):
                    txt = _get_text(value)
                    if txt:
                        top_texts.append(txt)

            if top_texts:
                quest_title = top_texts[0]
                lines.append(f"# {quest_title}")
                if len(top_texts) > 1:
                    lines.append(f"*{top_texts[1]}*")
                if len(top_texts) > 2:
                    lines.append(f"> {top_texts[2]}")

            lines.append("")

            subquests: list[dict] = quest.get(SUBQUESTS_KEY, [])
            for sq in subquests:
                sq_title = _get_text(sq.get(SUBQ_TITLE_KEY, {}))
                items: list[dict] = sq.get(ITEMS_KEY, [])

                if not items:
                    continue

                if sq_title:
                    lines.append(f"### {sq_title}")
                    lines.append("")

                for item in items:
                    speaker = _get_text(item.get(SPEAKER_KEY, {}))
                    dialogs: list[dict] = item.get(DIALOGS_KEY, [])

                    for d in dialogs:
                        txt = _get_text(d.get(TEXT_OBJ_KEY, {}))
                        if txt:
                            if speaker:
                                lines.append(f"**{speaker}**：{txt}")
                            else:
                                lines.append(txt)

                    if dialogs:
                        lines.append("")

                lines.append("")

            if len(lines) <= 2:
                lines.append("(empty quest)")

            content = "\n".join(lines)
            safe_name = _escape_filename(quest_title or f"quest_{count}")
            fpath = out_dir / f"{count:04d}_{safe_name}.txt"
            fpath.write_text(content, encoding="utf-8")
            written.append(str(fpath))

    return written


# Keep alias for backward compatibility
convert_jsonl_to_txt = convert_quests


# ═══════════════════════════════════════════════════════════════════════════
# Talks (v6.6 adapted)
# ═══════════════════════════════════════════════════════════════════════════

def _get_talk_speaker(item: dict) -> str:
    """Extract speaker name from a talk dialog item (post-replace_hashes)."""
    # Try Type A role dict
    for speaker_key in (TALK_A_SPEAKER, TALK_B_SPEAKER):
        role = item.get(speaker_key)
        if isinstance(role, dict):
            role_type = role.get("_type", "")
            if role_type == "TALK_ROLE_PLAYER":
                return "旅行者"
            # NPC — role name might be in the item as a replaced string
            break

    # Check if role name was replaced from hash → string
    role_name = item.get(TALK_A_ROLE_NAME)
    if isinstance(role_name, str) and role_name:
        return role_name

    return ""


def _get_talk_content(item: dict) -> str:
    """Extract dialogue content from a talk item (post-replace_hashes)."""
    for content_key in (TALK_A_CONTENT, TALK_B_CONTENT):
        val = item.get(content_key)
        if isinstance(val, str) and val:
            return val
    return ""


def convert_talks(jsonl_path: str, output_dir: str) -> list[str]:
    """将 talks JSONL 按 talk 类型分文件转换为 .txt。

    每行是一个已替换哈希的 talk，包含 _talk_type 和 _talk_file 元数据。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Group talks by type
    by_type: dict[str, list[dict]] = {}
    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                talk = json.loads(line)
            except json.JSONDecodeError:
                continue
            ttype = talk.get("_talk_type", "unknown")
            by_type.setdefault(ttype, []).append(talk)

    written: list[str] = []
    for ttype, talks in sorted(by_type.items()):
        type_dir = out_dir / ttype
        type_dir.mkdir(parents=True, exist_ok=True)

        for i, talk in enumerate(talks):
            # Detect dialog list key
            dialog_list: list[dict] = []
            if TALK_A_LIST in talk:
                dialog_list = talk[TALK_A_LIST]
            elif TALK_B_LIST in talk:
                dialog_list = talk[TALK_B_LIST]

            if not dialog_list:
                continue

            talk_id = talk.get(TALK_A_TALK_ID, talk.get("_talk_file", f"talk_{i}"))
            lines: list[str] = [
                f"# {ttype} Talk {talk_id}",
                "",
            ]

            for item in dialog_list:
                speaker = _get_talk_speaker(item)
                content = _get_talk_content(item)

                if content:
                    if speaker:
                        lines.append(f"**{speaker}**：{content}")
                    else:
                        lines.append(content)

            if len(lines) <= 2:
                continue

            content = "\n".join(lines)
            safe_id = _escape_filename(str(talk_id))
            fpath = type_dir / f"{i:05d}_{safe_id}.txt"
            fpath.write_text(content, encoding="utf-8")
            written.append(str(fpath))

    return written


# ═══════════════════════════════════════════════════════════════════════════
# Avatars
# ═══════════════════════════════════════════════════════════════════════════

def convert_avatars(jsonl_path: str, output_dir: str) -> list[str]:
    """将 avatars JSONL 按角色分文件转换为 .txt。"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []

    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                avatar = json.loads(line)
            except json.JSONDecodeError:
                continue

            name = avatar.get("name", "unknown")
            if not name:
                continue

            lines: list[str] = [f"# {name}", ""]

            # Basic info
            desc = avatar.get("desc", "")
            if desc:
                lines.append(desc)
                lines.append("")

            # Structured fields
            for field_label, field_key in [
                ("神之眼", "element"),
                ("命之座", "constellation"),
                ("生日", "birthday"),
                ("称号", "title"),
                ("所属", "native"),
            ]:
                val = avatar.get(field_key, "")
                if val:
                    lines.append(f"- **{field_label}**: {val}")

            info_fields = ("element", "constellation", "birthday", "title", "native")
            if any(avatar.get(k) for k in info_fields):
                lines.append("")

            # Voice lines
            sayings: list[dict] = avatar.get("sayings", [])
            if sayings:
                lines.append("## 语音")
                lines.append("")
                for s in sayings:
                    title = s.get("title", "")
                    content = s.get("content", "")
                    if title and content:
                        lines.append(f"**{title}**：{content}")
                        lines.append("")
                    elif content:
                        lines.append(content)
                        lines.append("")

            # Stories
            stories: list[dict] = avatar.get("stories", [])
            if stories:
                lines.append("## 角色故事")
                lines.append("")
                for s in stories:
                    title = s.get("title", "")
                    content = s.get("content", "")
                    if title:
                        lines.append(f"### {title}")
                    if content:
                        lines.append(content.replace("\\n", "\n"))
                    lines.append("")

            content = "\n".join(lines)
            safe_name = _escape_filename(name)
            fpath = out_dir / f"{safe_name}.txt"
            fpath.write_text(content, encoding="utf-8")
            written.append(str(fpath))

    return written


# ═══════════════════════════════════════════════════════════════════════════
# Misc (materials, weapons, relics)
# ═══════════════════════════════════════════════════════════════════════════

def convert_misc(jsonl_path: str, output_dir: str) -> list[str]:
    """将 misc JSONL 转换为按条目分文件的 .txt。"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    count = 0

    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            count += 1
            name = item.get("name", f"item_{count}")
            lines: list[str] = [f"# {name}", ""]

            desc = item.get("desc", "")
            if desc:
                lines.append(desc)
                lines.append("")

            # Skill info (weapons)
            skill_name = item.get("skillName", "")
            skill_desc = item.get("skillDesc", "")
            if skill_name or skill_desc:
                lines.append("## 技能")
                if skill_name:
                    lines.append(f"**{skill_name}**")
                if skill_desc:
                    lines.append(skill_desc)
                lines.append("")

            # Story (weapons, relics, wings)
            for field in sorted(item.keys()):
                if field.startswith("story"):
                    story = item[field]
                    if story:
                        lines.append(f"## 背景故事 {field.replace('story', '').strip('_')}")
                        lines.append(story)
                        lines.append("")

            content = "\n".join(lines)
            safe_name = _escape_filename(name)
            fpath = out_dir / f"{count:04d}_{safe_name}.txt"
            fpath.write_text(content, encoding="utf-8")
            written.append(str(fpath))

    return written


# ═══════════════════════════════════════════════════════════════════════════
# Starrail Quests
# ═══════════════════════════════════════════════════════════════════════════

def convert_starrail_quests(jsonl_path: str, output_dir: str) -> list[str]:
    """将星铁 mission JSONL 转换为按任务分文件的 .txt。"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    count = 0

    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry: dict = json.loads(line)
            except json.JSONDecodeError:
                continue

            count += 1
            mission = entry.get("mission", {})
            name = mission.get("name", f"mission_{count}")
            chapter = mission.get("chapter", {})

            lines: list[str] = [f"# {name}", ""]

            # Chapter info
            if chapter:
                chapter_name = chapter.get("ChapterName", "")
                stage_name = chapter.get("StageName", "")
                if chapter_name and stage_name:
                    lines.append(f"> {chapter_name} {stage_name}")
                elif chapter_name:
                    lines.append(f"> {chapter_name}")
                lines.append("")

            # Submissions
            submissions: list[dict] = entry.get("submissions", [])
            for sub in submissions:
                target = sub.get("target", "")
                desc = sub.get("desc", "")
                if target:
                    lines.append(f"### {target}")
                    lines.append("")
                if desc:
                    lines.append(desc)
                    lines.append("")

            if len(lines) <= 2:
                lines.append("(empty mission)")

            content = "\n".join(lines)
            safe_name = _escape_filename(name)
            fpath = out_dir / f"{count:04d}_{safe_name}.txt"
            fpath.write_text(content, encoding="utf-8")
            written.append(str(fpath))

    return written


# ═══════════════════════════════════════════════════════════════════════════

def clean_variables(text: str) -> str:
    """清洗文本中的游戏变量残留。"""
    raise NotImplementedError("clean_variables — 待实现")
