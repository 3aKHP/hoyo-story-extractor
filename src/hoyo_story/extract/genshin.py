"""原神（AnimeGameData）提取器 — v6.6 适配。

数据源：DimbreathBot/AnimeGameData (CNRELWin6.6.0)

提取类型：
    quests  — CodexQuest 任务剧情对话
    talks   — BinOutput/Talk 各类 NPC/物件对话
    avatars — ExcelBinOutput 角色资料/语音/故事
    misc    — ExcelBinOutput + Readable 物品/武器/圣遗物文本
"""

from __future__ import annotations

import json
import os

from hoyo_story.extract.base import BaseExtractor, replace_hashes

# ── v6.6 Talk field keys (Type A: Gadget, Npc, NpcOther, Quest, Activity, FreeGroup) ─
TALK_A_LIST = "GALIDJOEHOC"       # dialog list
TALK_A_SPEAKER = "PIBKEGJOJHN"    # speaker role dict {_id, _type}
TALK_A_CONTENT = "AIGJBMCHCJG"    # content TextMap hash (becomes str after replace)
TALK_A_ROLE_NAME = "BMFGJJJPBBC"  # role name TextMap hash (becomes str)
TALK_A_ID = "NFIEHACCECI"         # talk content ID (not a text hash)
TALK_A_TALK_ID = "AADKDKPMGNO"    # talkId
TALK_A_TYPE = "HAHEIAHBPEJ"       # talk type ("NPC", "GADGET", etc.)

# ── v6.6 Talk field keys (Type B: Blossom, Coop, Cutscene, Storyboard) ─
TALK_B_LIST = "IOEDPLCPFFB"       # dialog list
TALK_B_SPEAKER = "DGGDDIMMIDO"    # speaker role dict
TALK_B_CONTENT = "HJJLLECCCPI"    # content TextMap hash (becomes str)
TALK_B_ID = "GMOMCKNPBGE"         # talk content ID


class GenshinExtractor(BaseExtractor):
    """原神剧情文本提取器 — v6.6 适配。

    extract_quests() 从 BaseExtractor 继承默认实现。
    其余方法为本类特有。
    """

    game_name = "genshin"
    text_map_paths = [
        "TextMap/TextMap{lang}.json",
        "TextMap/TextMap_Medium{lang}.json",
    ]
    quest_data_path = "BinOutput/CodexQuest"

    # ── NPC name lookup ────────────────────────────────────────────────

    def _load_npc_names(self) -> dict[str, str]:
        """从 NpcExcelConfigData 加载 NPC ID → 名称映射。"""
        npc_path = os.path.join(
            self.raw_repo_path, "ExcelBinOutput", "NpcExcelConfigData.json"
        )
        if not os.path.exists(npc_path):
            return {}

        with open(npc_path, encoding="utf-8") as f:
            npc_list = json.load(f)

        text_map = self.load_text_map()
        result: dict[str, str] = {}
        for npc in npc_list:
            npc_id = str(npc["id"])
            name_hash = str(npc.get("nameTextMapHash", ""))
            result[npc_id] = text_map.get(name_hash, npc_id)
        return result

    # ── Talks ───────────────────────────────────────────────────────────

    def extract_talks(self, output_path: str | None = None) -> str:
        """从 BinOutput/Talk 的所有子目录提取对话。

        覆盖 15 个 Talk 子类型，使用 TextMap 递归替换所有整数哈希。
        产出 JSONL：每行一个 talk 文件的内容（已替换哈希）。

        Args:
            output_path: JSONL 输出路径。

        Returns:
            JSONL 文件路径。
        """
        text_map = self.load_text_map()
        talk_dir = os.path.join(self.raw_repo_path, "BinOutput", "Talk")
        if not os.path.isdir(talk_dir):
            raise FileNotFoundError(f"Talk data directory not found: {talk_dir}")

        if output_path is None:
            output_path = os.path.join("build", f"talks_{self.lang}.jsonl")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        count = 0
        with open(output_path, "w", encoding="utf-8") as out:
            for sub in sorted(os.listdir(talk_dir)):
                sub_path = os.path.join(talk_dir, sub)
                if not os.path.isdir(sub_path):
                    continue
                for file_name in sorted(os.listdir(sub_path)):
                    file_path = os.path.join(sub_path, file_name)
                    if not file_path.endswith(".json"):
                        continue
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            talk = json.load(f)
                    except (json.JSONDecodeError, OSError):
                        continue
                    talk = replace_hashes(talk, text_map)
                    if talk:
                        # Tag with source sub-type for downstream filtering
                        talk["_talk_type"] = sub
                        talk["_talk_file"] = file_name
                        out.write(json.dumps(talk, ensure_ascii=False) + "\n")
                        count += 1

        if count == 0:
            raise ValueError(f"No valid talk JSON files were extracted from: {talk_dir}")

        return output_path

    # ── Avatars ─────────────────────────────────────────────────────────

    def extract_avatars(self, output_path: str | None = None) -> str:
        """从 ExcelBinOutput 提取角色资料、语音、故事。

        数据源：
        - AvatarExcelConfigData.json     → 基础信息 (名称、描述、神之眼等)
        - FetterInfoExcelConfigData.json → 详细信息 (生日、命之座等)
        - FettersExcelConfigData.json    → 语音 (sayings)
        - FetterStoryExcelConfigData.json → 角色故事

        Args:
            output_path: JSONL 输出路径。

        Returns:
            JSONL 文件路径。
        """
        text_map = self.load_text_map()
        repo = self.raw_repo_path

        # ── 1. Avatar basic info ────────────────────────────────────
        id_to_avatar: dict[str, dict] = {}
        av_path = os.path.join(repo, "ExcelBinOutput", "AvatarExcelConfigData.json")
        if not os.path.exists(av_path):
            raise FileNotFoundError(f"Avatar data file not found: {av_path}")

        with open(av_path, encoding="utf-8") as f:
            for info in json.load(f):
                name = text_map.get(str(info.get("nameTextMapHash", "")), "")
                desc = text_map.get(str(info.get("descTextMapHash", "")), "")
                avatar_id = str(info.get("id", ""))
                if not name or not desc:
                    continue
                id_to_avatar[avatar_id] = {
                    "name": name,
                    "desc": desc,
                    "id": avatar_id,
                }
                # Copy other text fields
                for field, hash_val in info.items():
                    if "textmaphash" in field.lower() and field not in (
                        "nameTextMapHash",
                        "descTextMapHash",
                    ):
                        val = text_map.get(str(hash_val), "")
                        if val:
                            id_to_avatar[avatar_id][
                                field.replace("TextMapHash", "")
                            ] = val

        # ── 2. Fetter info (birthday, constellation, etc.) ──────────
        fetter_path = os.path.join(repo, "ExcelBinOutput", "FetterInfoExcelConfigData.json")
        if os.path.exists(fetter_path):
            with open(fetter_path, encoding="utf-8") as f:
                for info in json.load(f):
                    avatar_name = id_to_avatar.get(str(info.get("avatarId", "")), {}).get("name")
                    if not avatar_name:
                        continue
                    entry = id_to_avatar[str(info["avatarId"])]
                    for field, hash_val in info.items():
                        if "textmaphash" in field.lower() or "birth" in field.lower():
                            field_clean = field.replace("TextMapHash", "")
                            default = str(hash_val) if "birth" in field.lower() else ""
                            val = text_map.get(str(hash_val), default)
                            if val:
                                entry[field_clean] = val

        # ── 3. Voice lines (sayings) ────────────────────────────────
        fetters_path = os.path.join(repo, "ExcelBinOutput", "FettersExcelConfigData.json")
        if os.path.exists(fetters_path):
            with open(fetters_path, encoding="utf-8") as f:
                for info in json.load(f):
                    avatar_name = id_to_avatar.get(str(info.get("avatarId", "")), {}).get("name")
                    if not avatar_name:
                        continue
                    entry = id_to_avatar[str(info["avatarId"])]
                    entry.setdefault("sayings", []).append({
                        "title": text_map.get(str(info.get("voiceTitleTextMapHash", "")), ""),
                        "content": text_map.get(str(info.get("voiceFileTextTextMapHash", "")), ""),
                    })

        # ── 4. Character stories ────────────────────────────────────
        story_path = os.path.join(repo, "ExcelBinOutput", "FetterStoryExcelConfigData.json")
        if os.path.exists(story_path):
            with open(story_path, encoding="utf-8") as f:
                for info in json.load(f):
                    avatar_name = id_to_avatar.get(str(info.get("avatarId", "")), {}).get("name")
                    if not avatar_name:
                        continue
                    entry = id_to_avatar[str(info["avatarId"])]
                    entry.setdefault("stories", []).append({
                        "title": text_map.get(str(info.get("storyTitleTextMapHash", "")), ""),
                        "content": text_map.get(str(info.get("storyContextTextMapHash", "")), ""),
                    })

        # ── Write output ────────────────────────────────────────────
        if output_path is None:
            output_path = os.path.join("build", f"avatars_{self.lang}.jsonl")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        count = 0
        with open(output_path, "w", encoding="utf-8") as out:
            for avatar_data in id_to_avatar.values():
                out.write(json.dumps(avatar_data, ensure_ascii=False) + "\n")
                count += 1

        if count == 0:
            raise ValueError(f"No avatar entries were extracted from: {av_path}")

        return output_path

    # ── Misc (materials, weapons, relics) ──────────────────────────────

    def extract_misc(self, output_dir: str | None = None) -> dict[str, str]:
        """提取物品/武器/圣遗物的名称、描述、背景故事。

        数据源：
        - ExcelBinOutput/MaterialExcelConfigData.json
        - ExcelBinOutput/WeaponExcelConfigData.json
        - ExcelBinOutput/ReliquaryExcelConfigData.json
        - Readable/{lang}/*.txt  — 武器/圣遗物/风之翼背景故事

        Args:
            output_dir: 输出目录。

        Returns:
            {类别: JSONL 文件路径} 的映射。
        """
        text_map = self.load_text_map()
        repo = self.raw_repo_path
        source_files = {
            "materials": os.path.join(repo, "ExcelBinOutput", "MaterialExcelConfigData.json"),
            "weapons": os.path.join(repo, "ExcelBinOutput", "WeaponExcelConfigData.json"),
            "relics": os.path.join(repo, "ExcelBinOutput", "ReliquaryExcelConfigData.json"),
        }
        if not any(os.path.exists(path) for path in source_files.values()):
            raise FileNotFoundError(
                "No misc source files found. Expected at least one of: "
                + ", ".join(source_files.values())
            )

        if output_dir is None:
            output_dir = os.path.join("build", f"misc_{self.lang}")
        os.makedirs(output_dir, exist_ok=True)

        result: dict[str, str] = {}

        # ── Materials ───────────────────────────────────────────────
        mat_path = source_files["materials"]
        if os.path.exists(mat_path):
            materials = _extract_excel_sheet(
                mat_path, text_map, "nameTextMapHash", "descTextMapHash"
            )
            mat_out = os.path.join(output_dir, f"materials_{self.lang}.jsonl")
            _write_jsonl(materials, mat_out)
            result["materials"] = mat_out

        # ── Weapons ─────────────────────────────────────────────────
        wp_path = source_files["weapons"]
        if os.path.exists(wp_path):
            weapons = _extract_excel_sheet(wp_path, text_map, "nameTextMapHash", "descTextMapHash")
            # Enrich with Readable stories
            readable_dir = os.path.join(repo, "Readable", self.lang)
            if os.path.isdir(readable_dir):
                _enrich_weapons_with_stories(weapons, readable_dir, text_map, repo)
            wp_out = os.path.join(output_dir, f"weapons_{self.lang}.jsonl")
            _write_jsonl(weapons, wp_out)
            result["weapons"] = wp_out

        # ── Relics ──────────────────────────────────────────────────
        rel_path = source_files["relics"]
        if os.path.exists(rel_path):
            relics = _extract_excel_sheet(rel_path, text_map, "nameTextMapHash", "descTextMapHash")
            readable_dir = os.path.join(repo, "Readable", self.lang)
            if os.path.isdir(readable_dir):
                _enrich_relics_with_stories(relics, readable_dir)
            rel_out = os.path.join(output_dir, f"relics_{self.lang}.jsonl")
            _write_jsonl(relics, rel_out)
            result["relics"] = rel_out

        if not result:
            raise ValueError("No misc entries were extracted from available source files")

        return result


# ── Misc helpers ────────────────────────────────────────────────────────

def _extract_excel_sheet(
    path: str,
    text_map: dict[str, str],
    name_field: str,
    desc_field: str,
) -> list[dict]:
    """Extract named items from an ExcelBinOutput JSON file."""
    items: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for entry in json.load(f):
            name = text_map.get(str(entry.get(name_field, "")), "")
            if not name or "test" in str(name).lower():
                continue
            item: dict = {"id": entry.get("id", ""), "name": name}
            desc = text_map.get(str(entry.get(desc_field, "")), "")
            if desc:
                item["desc"] = desc
            for metadata_field in ("icon", "skillAffix"):
                if metadata_field in entry:
                    item[metadata_field] = entry[metadata_field]
            # Copy all fields whose name suggests text content
            for k, v in entry.items():
                if k in (name_field, desc_field, "id"):
                    continue
                if "textmaphash" in k.lower():
                    val = text_map.get(str(v), "")
                    if val:
                        item[k.replace("TextMapHash", "")] = val
            items.append(item)
    return items


def _enrich_weapons_with_stories(
    weapons: list[dict],
    readable_dir: str,
    text_map: dict[str, str],
    repo: str,
) -> None:
    """Add weapon stories from Readable/ and skill descriptions."""
    import re

    weapon_by_id = {str(w["id"]): w for w in weapons}

    # Load weapon story files
    for fname in os.listdir(readable_dir):
        m = re.match(r"^Weapon(\d+)(?:_(\d))?\.txt$", fname)
        if not m:
            continue
        weapon_id = m.group(1)
        idx = m.group(2)
        key = "story" if not idx else f"story_{idx}"
        if weapon_id in weapon_by_id:
            with open(os.path.join(readable_dir, fname), encoding="utf-8") as f:
                weapon_by_id[weapon_id][key] = f.read().strip()

    # Load skill descriptions via EquipAffix
    affix_path = os.path.join(repo, "ExcelBinOutput", "EquipAffixExcelConfigData.json")
    if not os.path.exists(affix_path):
        return

    with open(affix_path, encoding="utf-8") as f:
        affixes_by_skill: dict[int, list[dict]] = {}
        affixes_by_id: dict[int, dict] = {}
        for affix in json.load(f):
            affixes_by_id[affix["affixId"]] = affix
            affixes_by_skill.setdefault(affix["id"], []).append(affix)

    for w in weapons:
        skill_affix = w.get("skillAffix")
        if not skill_affix or not isinstance(skill_affix, list) or not skill_affix:
            continue
        skill_id = skill_affix[0]
        affixes = affixes_by_skill.get(skill_id, [])
        if not affixes:
            continue
        name_hash = str(affixes[0].get("nameTextMapHash", ""))
        w["skillName"] = text_map.get(name_hash, "")
        descs = []
        for a in affixes:
            desc_hash = str(a.get("descTextMapHash", ""))
            descs.append(text_map.get(desc_hash, ""))
        w["skillDesc"] = "\n".join(descs)
        w.pop("skillAffix", None)


def _enrich_relics_with_stories(relics: list[dict], readable_dir: str) -> None:
    """Add relic stories from Readable/."""
    import re

    # Build story lookup by icon suffix
    stories: dict[str, str] = {}
    for fname in os.listdir(readable_dir):
        m = re.match(r"^Relic([\d_]+)\.txt$", fname)
        if not m:
            continue
        with open(os.path.join(readable_dir, fname), encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            stories[m.group(1)] = content

    for r in relics:
        icon = r.get("icon", "")
        m = re.search(r"_(\d+_\d+)$", icon)
        if m and m.group(1) in stories:
            r["story"] = stories[m.group(1)]


def _write_jsonl(items: list[dict], path: str) -> None:
    """Write list of dicts as JSONL."""
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
