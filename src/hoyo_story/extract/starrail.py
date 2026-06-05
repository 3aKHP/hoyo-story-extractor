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
            return json.load(f)

    # ── Quests (missions) ────────────────────────────────────────────────

    def extract_quests(self, output_path: str | None = None) -> str:
        """从 ExcelOutput 提取任务层级（missions + submissions）。

        数据源：
        - ExcelOutput/MainMission.json       → 主任务信息
        - ExcelOutput/SubMission.json        → 子任务信息
        - ExcelOutput/MissionChapterConfig.json → 章节名称
        - Config/Level/Mission/*/MissionInfo_*.json → 任务-子任务层级

        Args:
            output_path: JSONL 输出路径。

        Returns:
            JSONL 文件路径。
        """
        import glob

        text_map = self.load_text_map()
        repo = self.raw_repo_path

        # ── 1. Chapter config (uses stable hash) ──────────────────────────
        chapter_map: dict[str, dict] = {}
        chapter_file = os.path.join(repo, "ExcelOutput", "MissionChapterConfig.json")
        if os.path.exists(chapter_file):
            with open(chapter_file, encoding="utf-8") as f:
                raw_chapters = json.load(f)
            for chapter_id, info in raw_chapters.items():
                chapter_entry: dict[str, str] = {}
                for key in ("ChapterName", "StageName", "ChapterDesc"):
                    val = info.get(key)
                    if val:
                        hash_val = get_stable_hash(str(val))
                        txt = text_map.get(str(hash_val), "")
                        if txt:
                            chapter_entry[key] = txt
                if chapter_entry:
                    chapter_map[chapter_id] = chapter_entry

        # ── 2. Main missions (uses Hash dict) ─────────────────────────────
        mission_map: dict[str, dict] = {}
        mission_file = os.path.join(repo, "ExcelOutput", "MainMission.json")
        if os.path.exists(mission_file):
            with open(mission_file, encoding="utf-8") as f:
                raw_missions = json.load(f)
            for mission_id, info in raw_missions.items():
                mission_entry: dict[str, object] = {"id": mission_id}
                for key, item in info.items():
                    if isinstance(item, dict) and "Hash" in item:
                        txt = text_map.get(str(item["Hash"]), "")
                        if txt:
                            mission_entry[key] = txt
                    elif key in (
                        "NextMainMissionList",
                        "ChapterID",
                        "RewardID",
                        "NextTrackMainMission",
                    ):
                        mission_entry[key] = item
                mission_map[mission_id] = mission_entry

        # ── 3. Sub missions (uses Hash dict) ──────────────────────────────
        submission_map: dict[str, dict] = {}
        submission_file = os.path.join(repo, "ExcelOutput", "SubMission.json")
        if os.path.exists(submission_file):
            with open(submission_file, encoding="utf-8") as f:
                raw_submissions = json.load(f)
            for sub_id, info in raw_submissions.items():
                sub_entry: dict[str, object] = {"id": sub_id}
                for key, item in info.items():
                    if isinstance(item, dict) and "Hash" in item:
                        txt = text_map.get(str(item["Hash"]), "")
                        if txt:
                            sub_entry[key] = txt
                    else:
                        sub_entry[key] = item
                submission_map[sub_id] = sub_entry

        # ── 4. Build hierarchy from Config/Level/Mission/ ─────────────────
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
                if not mission.get("Name"):
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
                        "name": mission.get("Name", ""),
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
        raise NotImplementedError("extract_talks — Phase 5 实现中（Commit 4）")

    # ── Avatars ──────────────────────────────────────────────────────────

    def extract_avatars(self, output_path: str | None = None) -> str:
        """从 ExcelOutput 提取角色资料、语音、故事。

        数据源：
        - ExcelOutput/AvatarConfig.json          → 基础信息
        - ExcelOutput/AvatarSkillTreeConfig.json → 技能树
        - ExcelOutput/AvatarPromotionConfig.json → 晋升信息
        - ExcelOutput/AvatarPlayerTitleConfig.json → 称号

        Args:
            output_path: JSONL 输出路径。

        Returns:
            JSONL 文件路径。
        """
        raise NotImplementedError("extract_avatars — Phase 5 实现中（Commit 5）")

    # ── Misc ─────────────────────────────────────────────────────────────

    def extract_misc(self, output_dir: str | None = None) -> dict[str, str]:
        """提取物品、书籍、光锥、遗器等杂项文本。

        数据源：
        - ExcelOutput/ItemConfig.json          → 通用物品
        - ExcelOutput/ItemConfigBook.json      → 书籍
        - ExcelOutput/ItemConfigEquipment.json → 光锥
        - ExcelOutput/ItemConfigRelic.json     → 遗器
        - ExcelOutput/ItemPlayerCard.json      → 玩家名片

        Args:
            output_dir: 输出目录。

        Returns:
            {类别: JSONL 文件路径} 的映射。
        """
        raise NotImplementedError("extract_misc — Phase 5 实现中（Commit 5）")
