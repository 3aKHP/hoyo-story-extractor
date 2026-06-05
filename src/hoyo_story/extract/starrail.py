"""星穹铁道（TurnBasedGameData）提取器 — Phase 5 实现。

数据源：DimbreathBot/TurnBasedGameData
- TextMap：单表 TextMap{lang}.json + TextMapMain{lang}.json
- 哈希方案：stable hash（字符串 → 32-bit 哈希，用于部分 ExcelOutput 字段）
- 对话映射：TalkSentenceConfig.json（TalkSentenceID → 说话人/内容哈希）
- 任务数据：ExcelOutput/MainMission.json + SubMission.json + MissionChapterConfig.json
- 对话数据：Config/Level/ 下的 .json（含序列化 TaskList）
"""

from __future__ import annotations

import json
import os

from hoyo_story.extract.base import BaseExtractor


def get_stable_hash(s: str) -> int:
    """星铁 stable hash 算法 — 将字符串映射为 32-bit 哈希值。

    用于解析部分 ExcelOutput 字段（如 MissionChapterConfig 中的章节名），
    这些字段的值是字符串，其 stable hash 作为 TextMap 的 key。

    算法来自社区参考实现（mrzjy/StarrailDialog），已验证与 datamine 数据匹配。

    Args:
        s: 待哈希的字符串。

    Returns:
        32-bit 无符号整数哈希值。
    """
    hash1 = 5381
    hash2 = hash1

    i = 0
    while i < len(s) and s[i] != "\0":
        hash1 = ((hash1 << 5) + hash1) ^ ord(s[i])
        if i == len(s) - 1 or s[i + 1] == "\0":
            break
        hash2 = ((hash2 << 5) + hash2) ^ ord(s[i + 1])
        i += 2

    return (hash1 + (hash2 * 1566083941)) & 0xFFFFFFFF


class StarrailExtractor(BaseExtractor):
    """星穹铁道剧情文本提取器 — Phase 5 实现。

    与原神的关键差异：
    1. TextMap 使用单表（无 Medium 分拆），直接加载即可
    2. 部分 ExcelOutput 字段使用 stable hash 作为 TextMap key
    3. 对话通过 TalkSentenceConfig.json 的 ID → 哈希映射解析
    4. 任务数据在 ExcelOutput/ 而非 BinOutput/ 中
    """

    game_name = "starrail"
    text_map_paths = [
        "TextMap/TextMap{lang}.json",
        "TextMap/TextMapMain{lang}.json",
    ]
    quest_data_path = ""  # 不适用；星铁任务数据在 ExcelOutput/，完全覆盖 extract_quests

    # ── Talk sentence lookup ─────────────────────────────────────────────

    def _load_talk_sentence_map(self) -> dict[str, dict]:
        """加载 TalkSentenceConfig.json，建立 TalkSentenceID → 哈希信息映射。

        Returns:
            {TalkSentenceID 字符串: {"TextmapTalkSentenceName": {"Hash": int},
                                     "TalkSentenceText": {"Hash": int}}} 的字典。
        """
        path = os.path.join(
            self.raw_repo_path, "ExcelOutput", "TalkSentenceConfig.json"
        )
        if not os.path.exists(path):
            raise FileNotFoundError(f"TalkSentenceConfig not found: {path}")

        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        # TurnBasedGameData uses list format: [{"TalkSentenceID": int, ...}, ...]
        if isinstance(raw, list):
            return {str(item["TalkSentenceID"]): item for item in raw if "TalkSentenceID" in item}
        # Fallback to dict format (if ever encountered)
        return raw

    # ── Quests (missions) ────────────────────────────────────────────────

    def _unhash_excel_item(self, info: dict, text_map: dict[str, str]) -> dict:
        """将 ExcelOutput 字典中的 {"Hash": int} 替换为 TextMap 文本。

        遍历 info 的所有字段，将 {"Hash": int64} 结构替换为 TextMap 中的对应文本。
        保留其他字段不变。

        Args:
            info: 单个 ExcelOutput 条目（如 MainMission 中的一个 mission）。
            text_map: 已加载的 TextMap 字典。

        Returns:
            替换后的字典副本。
        """
        result: dict = {}
        for key, item in info.items():
            if isinstance(item, dict) and "Hash" in item:
                hash_val = item["Hash"]
                txt = text_map.get(str(hash_val), "")
                result[key] = txt if txt else item
            else:
                result[key] = item
        return result

    def extract_quests(self, output_path: str | None = None) -> str:
        """从 ExcelOutput 提取任务层级（missions + submissions）。

        数据源：
        - ExcelOutput/MainMission.json       → 主任务信息（列表格式）
        - ExcelOutput/SubMission.json        → 子任务信息（列表格式）
        - ExcelOutput/MissionChapterConfig.json → 章节名称（列表格式）
        - Config/Level/Mission/*/MissionInfo_*.json → 任务-子任务层级

        Args:
            output_path: JSONL 输出路径。

        Returns:
            JSONL 文件路径。
        """
        import glob

        text_map = self.load_text_map()
        repo = self.raw_repo_path

        # ── 1. Chapter config (list format, uses stable hash on string values) ─
        chapter_map: dict[str, dict] = {}
        chapter_file = os.path.join(repo, "ExcelOutput", "MissionChapterConfig.json")
        if os.path.exists(chapter_file):
            with open(chapter_file, encoding="utf-8") as f:
                raw_chapters = json.load(f)
            if isinstance(raw_chapters, list):
                for info in raw_chapters:
                    chapter_id = str(info.get("ID", ""))
                    if not chapter_id:
                        continue
                    chapter_entry: dict[str, str] = {}
                    for key in ("ChapterName", "StageName", "ChapterDesc"):
                        val = info.get(key)
                        if val and isinstance(val, str) and val:
                            hash_val = get_stable_hash(val)
                            txt = text_map.get(str(hash_val), "")
                            if txt:
                                chapter_entry[key] = txt
                    if chapter_entry:
                        chapter_map[chapter_id] = chapter_entry

        # ── 2. Main missions (list format, uses Hash dict) ────────────────────
        mission_map: dict[str, dict] = {}
        mission_file = os.path.join(repo, "ExcelOutput", "MainMission.json")
        if os.path.exists(mission_file):
            with open(mission_file, encoding="utf-8") as f:
                raw_missions = json.load(f)
            if isinstance(raw_missions, list):
                for info in raw_missions:
                    mission_id = str(info.get("MainMissionID", ""))
                    if not mission_id:
                        continue
                    mission_entry = self._unhash_excel_item(info, text_map)
                    mission_entry["id"] = mission_id
                    mission_map[mission_id] = mission_entry

        # ── 3. Sub missions (list format, uses Hash dict) ─────────────────────
        submission_map: dict[str, dict] = {}
        submission_file = os.path.join(repo, "ExcelOutput", "SubMission.json")
        if os.path.exists(submission_file):
            with open(submission_file, encoding="utf-8") as f:
                raw_submissions = json.load(f)
            if isinstance(raw_submissions, list):
                for info in raw_submissions:
                    sub_id = str(info.get("SubMissionID", ""))
                    if not sub_id:
                        continue
                    sub_entry = self._unhash_excel_item(info, text_map)
                    sub_entry["id"] = sub_id
                    submission_map[sub_id] = sub_entry

        # ── 4. Build hierarchy from Config/Level/Mission/ ─────────────────────
        mission_hierarchy: list[dict] = []
        mission_dir = os.path.join(repo, "Config", "Level", "Mission")
        if os.path.isdir(mission_dir):
            pattern = os.path.join(mission_dir, "*", "MissionInfo_*.json")
            for mission_info_file in glob.iglob(pattern):
                with open(mission_info_file, encoding="utf-8") as f:
                    info = json.load(f)

                main_id = str(info.get("MainMissionID", ""))
                if main_id not in mission_map:
                    continue

                mission = mission_map[main_id]
                name = mission.get("Name", "")
                if not name or name == "N/A":
                    continue

                # Collect submissions, deduplicate by text feature
                seen: dict[str, list[str]] = {}
                for sub in info.get("SubMissionList", []):
                    sub_id = str(sub.get("ID", ""))
                    if sub_id not in submission_map:
                        continue
                    submission = submission_map[sub_id]
                    target = str(submission.get("TargetText", ""))
                    desc = str(submission.get("DescrptionText", ""))
                    if not target or target == "N/A":
                        continue
                    feature = f"{target}|||{desc}"
                    seen.setdefault(feature, []).append(sub_id)

                submissions = []
                for feature, ids in seen.items():
                    target, desc = feature.split("|||", 1)
                    submissions.append({"ids": ids, "target": target, "desc": desc})

                chapter_id = str(mission.get("ChapterID", ""))
                result_entry: dict = {
                    "mission": {
                        "id": main_id,
                        "name": name,
                        "next_missions": mission.get("NextMainMissionList", []),
                        "next_track_mission": mission.get("NextTrackMainMission"),
                        "chapter_id": chapter_id,
                        "reward_id": mission.get("RewardID"),
                    },
                    "submissions": submissions,
                }
                if chapter_id and chapter_id in chapter_map:
                    result_entry["mission"]["chapter"] = chapter_map[chapter_id]

                mission_hierarchy.append(result_entry)

        if not mission_hierarchy:
            raise ValueError("No mission entries were extracted from available source files")

        # ── 5. Write JSONL ──────────────────────────────────────────────
        if output_path is None:
            output_path = os.path.join("build", f"quests_{self.lang}.jsonl")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as out:
            for entry in mission_hierarchy:
                out.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return output_path

    # ── Talks / Story ────────────────────────────────────────────────────

    def _get_speaker_content(
        self,
        sent_id: int | str,
        text_map: dict[str, str],
        talk_sentence_map: dict[str, dict],
    ) -> dict[str, str] | None:
        """通过 TalkSentenceID 解析说话人和对话内容。"""
        hash_info = talk_sentence_map.get(str(sent_id))
        if not hash_info:
            return None
        name_hash = hash_info.get("TextmapTalkSentenceName", {}).get("Hash")
        text_hash = hash_info.get("TalkSentenceText", {}).get("Hash")
        if name_hash is None or text_hash is None:
            return None
        speaker = text_map.get(str(name_hash), "")
        content = text_map.get(str(text_hash), "")
        if not content:
            return None
        return {"role": speaker, "content": content}

    def _parse_on_sequence(
        self,
        info: dict,
        text_map: dict[str, str],
        talk_sentence_map: dict[str, dict],
    ) -> list[list[dict]]:
        """解析单个 .json 中的 OnStartSequece / TaskList 对话序列。

        处理以下 $type：
        - RPG.GameCore.PlayAndWaitSimpleTalk → 普通对话
        - RPG.GameCore.PlayOptionTalk       → 玩家选项
        - RPG.GameCore.WaitCustomString     → 等待/触发对话
        - RPG.GameCore.TriggerCustomString  → 触发对话
        - RPG.GameCore.EndPerformance       → 结束标记

        Returns:
            对话 session 列表，每个 session 是 item 列表。
        """
        import re

        sessions: list[list[dict]] = []
        for sequence in info.get("OnStartSequece", []):
            session: list[dict] = []
            for element in sequence.get("TaskList", []):
                etype = element.get("$type", "")

                if etype == "RPG.GameCore.PlayAndWaitSimpleTalk":
                    sub_session = {"type": etype, "conversations": []}
                    for simple_talk in element.get("SimpleTalkList", []):
                        sent_id = simple_talk.get("TalkSentenceID")
                        sc = self._get_speaker_content(sent_id, text_map, talk_sentence_map)
                        if sc:
                            sub_session["conversations"].append({
                                "role": sc["role"],
                                "content": sc["content"],
                                "talk_sentence_id": sent_id,
                            })
                    if sub_session["conversations"]:
                        session.append(sub_session)

                elif etype == "RPG.GameCore.PlayOptionTalk":
                    sub_session = {"type": etype, "options": []}
                    for option in element.get("OptionList", []):
                        sent_id = option.get("TalkSentenceID")
                        sc = self._get_speaker_content(sent_id, text_map, talk_sentence_map)
                        if sc:
                            # Parse next TalkSentenceID from TriggerCustomString
                            next_id = None
                            trigger = option.get("TriggerCustomString", "")
                            if isinstance(trigger, dict):
                                trigger = trigger.get("Value", "")
                            if trigger:
                                m = re.search(r"(?:TalkSentence_)?(\d+)", str(trigger))
                                if m:
                                    next_id = int(m.group(1))
                            sub_session["options"].append({
                                "role": sc["role"],
                                "content": sc["content"],
                                "talk_sentence_id": sent_id,
                                "next_talk_sentence_id": next_id,
                            })
                    if sub_session["options"]:
                        session.append(sub_session)

                elif etype in (
                    "RPG.GameCore.WaitCustomString",
                    "RPG.GameCore.TriggerCustomString",
                ):
                    custom_string = element.get("CustomString", "")
                    if isinstance(custom_string, dict):
                        custom_string = custom_string.get("Value", "")
                    if custom_string:
                        m = re.search(r"(?:TalkSentence_)?(\d+)", str(custom_string))
                        if m:
                            sent_id = int(m.group(1))
                            sc = self._get_speaker_content(sent_id, text_map, talk_sentence_map)
                            if sc:
                                session.append({
                                    "type": etype,
                                    "role": sc["role"],
                                    "content": sc["content"],
                                    "talk_sentence_id": sent_id,
                                })

                elif etype == "RPG.GameCore.EndPerformance":
                    if session:
                        session.append({"type": etype})

            if session:
                sessions.append(session)

        return sessions

    def _merge_sessions(self, sessions: list[list[dict]]) -> list[list[dict]]:
        """合并对话 session，去除 WaitCustomString 与 PlayAndWaitSimpleTalk 的重复。"""
        merged: list[list[dict]] = []
        for session in sessions:
            merged_session: list[dict] = []
            for item in session:
                # Skip duplicate WaitCustomString that matches next PlayAndWaitSimpleTalk
                if (
                    merged_session
                    and merged_session[-1].get("type") == "RPG.GameCore.WaitCustomString"
                    and item.get("type") == "RPG.GameCore.PlayAndWaitSimpleTalk"
                    and merged_session[-1].get("talk_sentence_id")
                    == item["conversations"][0].get("talk_sentence_id")
                ):
                    del merged_session[-1]

                # TriggerCustomString → add next_id to previous item
                if (
                    item.get("type") == "RPG.GameCore.TriggerCustomString"
                    and merged_session
                ):
                    merged_session[-1]["next_talk_sentence_id"] = item.get(
                        "talk_sentence_id"
                    )
                    continue

                merged_session.append(item)

            if merged_session and merged_session[-1].get("type") == "RPG.GameCore.EndPerformance":
                merged.append(merged_session)

        return merged

    def extract_talks(self, output_path: str | None = None) -> str:
        """从 Config/Level/ 提取对话和剧情文本。

        数据源：
        - Config/Level/Mission/     → 任务对话
        - Config/Level/Story/       → 剧情对话
        - Config/Level/TrainVisitor/ → 列车访客对话
        - Config/Level/Activity/    → 活动对话
        - Config/Level/Message/     → 手机消息

        Args:
            output_path: JSONL 输出路径。

        Returns:
            JSONL 文件路径。
        """
        import glob

        text_map = self.load_text_map()
        talk_sentence_map = self._load_talk_sentence_map()
        repo = self.raw_repo_path

        if output_path is None:
            output_path = os.path.join("build", f"talks_{self.lang}.jsonl")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        count = 0
        with open(output_path, "w", encoding="utf-8") as out:
            for source_dir in (
                "Config/Level/Mission",
                "Config/Level/Story",
                "Config/Level/TrainVisitor",
                "Config/Level/Activity",
                "Config/Level/Message",
            ):
                full_dir = os.path.join(repo, source_dir)
                if not os.path.isdir(full_dir):
                    continue

                source_type = os.path.basename(source_dir)
                pattern = os.path.join(full_dir, "**", "*.json")
                for json_file in glob.iglob(pattern, recursive=True):
                    with open(json_file, encoding="utf-8") as f:
                        try:
                            info = json.load(f)
                        except json.JSONDecodeError:
                            continue

                    sessions = self._parse_on_sequence(info, text_map, talk_sentence_map)
                    sessions = self._merge_sessions(sessions)
                    if sessions:
                        entry = {
                            "_source_type": source_type,
                            "_source_file": os.path.basename(json_file),
                            "sessions": sessions,
                        }
                        out.write(json.dumps(entry, ensure_ascii=False) + "\n")
                        count += 1

        if count == 0:
            raise ValueError("No talk entries were extracted from available source files")

        return output_path

    # ── Avatars ──────────────────────────────────────────────────────────

    def extract_avatars(self, output_path: str | None = None) -> str:
        """从 ExcelOutput 提取角色基础信息。

        数据源：
        - ExcelOutput/AvatarConfig.json → 基础信息（名称、描述、属性、命途等）

        当前为简化实现，仅提取 AvatarConfig 中的基础字段。
        语音、故事、技能等需后续从更多 ExcelOutput 文件合并。

        Args:
            output_path: JSONL 输出路径。

        Returns:
            JSONL 文件路径。
        """
        text_map = self.load_text_map()
        repo = self.raw_repo_path

        avatar_path = os.path.join(repo, "ExcelOutput", "AvatarConfig.json")
        if not os.path.exists(avatar_path):
            raise FileNotFoundError(f"Avatar data file not found: {avatar_path}")

        with open(avatar_path, encoding="utf-8") as f:
            raw_avatars = json.load(f)

        avatars: list[dict] = []
        if isinstance(raw_avatars, list):
            for info in raw_avatars:
                if not isinstance(info, dict):
                    continue
                avatar_id = str(info.get("AvatarID", ""))
                if not avatar_id:
                    continue
                entry = self._unhash_excel_item(info, text_map)
                entry["id"] = avatar_id
                name = entry.get("AvatarName", "")
                if not name or name == "N/A":
                    continue
                entry["name"] = name
                avatars.append(entry)
        else:
            # Fallback for dict format (if ever encountered)
            for avatar_id, info in raw_avatars.items():
                if not isinstance(info, dict):
                    continue
                entry = self._unhash_excel_item(info, text_map)
                entry["id"] = str(avatar_id)
                name = entry.get("AvatarName", "")
                if not name or name == "N/A":
                    continue
                entry["name"] = name
                avatars.append(entry)

        if not avatars:
            raise ValueError(f"No avatar entries were extracted from: {avatar_path}")

        if output_path is None:
            output_path = os.path.join("build", f"avatars_{self.lang}.jsonl")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as out:
            for avatar in avatars:
                out.write(json.dumps(avatar, ensure_ascii=False) + "\n")

        return output_path

    # ── Misc ─────────────────────────────────────────────────────────────

    def extract_misc(self, output_dir: str | None = None) -> dict[str, str]:
        """提取物品、书籍、光锥、遗器、玩家名片等杂项文本。

        数据源：
        - ExcelOutput/ItemConfig.json          → 通用物品
        - ExcelOutput/ItemConfigAvatar.json      → 角色相关物品
        - ExcelOutput/ItemConfigBook.json        → 书籍
        - ExcelOutput/ItemConfigEquipment.json   → 光锥
        - ExcelOutput/ItemConfigRelic.json       → 遗器
        - ExcelOutput/ItemPlayerCard.json        → 玩家名片

        Args:
            output_dir: 输出目录。

        Returns:
            {类别: JSONL 文件路径} 的映射。
        """
        text_map = self.load_text_map()
        repo = self.raw_repo_path

        if output_dir is None:
            output_dir = os.path.join("build", f"misc_{self.lang}")
        os.makedirs(output_dir, exist_ok=True)

        result: dict[str, str] = {}

        item_files = {
            "items": "ItemConfig.json",
            "avatars": "ItemConfigAvatar.json",
            "books": "ItemConfigBook.json",
            "equipment": "ItemConfigEquipment.json",
            "relics": "ItemConfigRelic.json",
            "player_cards": "ItemPlayerCard.json",
        }

        for category, filename in item_files.items():
            path = os.path.join(repo, "ExcelOutput", filename)
            if not os.path.exists(path):
                continue

            with open(path, encoding="utf-8") as f:
                try:
                    raw_data = json.load(f)
                except json.JSONDecodeError:
                    continue

            items: list[dict] = []
            if isinstance(raw_data, list):
                for info in raw_data:
                    if not isinstance(info, dict):
                        continue
                    item_id = str(info.get("ID", ""))
                    if not item_id:
                        continue
                    entry = self._unhash_excel_item(info, text_map)
                    entry["id"] = item_id
                    name = entry.get("ItemName", "")
                    if not name or "test" in str(name).lower():
                        continue
                    entry["name"] = name
                    # Try common desc fields
                    for desc_key in ("ItemDesc", "ItemBGDesc", "Desc", "Description"):
                        desc = entry.get(desc_key, "")
                        if desc:
                            entry["desc"] = desc
                            break
                    items.append(entry)
            else:
                for item_id, info in raw_data.items():
                    if not isinstance(info, dict):
                        continue
                    entry = self._unhash_excel_item(info, text_map)
                    entry["id"] = str(item_id)
                    name = entry.get("ItemName", "")
                    if not name or "test" in str(name).lower():
                        continue
                    entry["name"] = name
                    for desc_key in ("ItemDesc", "ItemBGDesc", "Desc", "Description"):
                        desc = entry.get(desc_key, "")
                        if desc:
                            entry["desc"] = desc
                            break
                    items.append(entry)

            if items:
                out_path = os.path.join(output_dir, f"{category}_{self.lang}.jsonl")
                with open(out_path, "w", encoding="utf-8") as f:
                    for item in items:
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")
                result[category] = out_path

        if not result:
            raise ValueError("No misc entries were extracted from available source files")

        return result
