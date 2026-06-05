"""公共提取逻辑 — 递归哈希替换、TextMap 合并、基础提取器。

各游戏特化模块（genshin.py / starrail.py / zzz.py）继承 BaseExtractor，
只需设置 game_name / text_map_paths / quest_data_path 三个类属性即可。
"""

from __future__ import annotations

import glob
import json
import os
from typing import Any

# ── Obfuscated key names in Genshin CodexQuest JSON ──────────────────────
# These are stable within a given game version but may change across versions.
# They are used by the convert step, not the extract step (extract uses
# recursive hash replacement only).
TEXT_KEY = "OPKOJIEHJAE"       # text hash ID field
SPEAKER_KEY = "KDDMHACHOGH"    # speaker name hash field
DIALOGS_KEY = "JOIPGFEDKFO"    # list of dialog entries in an item
TEXT_OBJ_KEY = "LEMPMANEBOB"   # text object within a dialog entry
SUBQUESTS_KEY = "IKECHKLEFFK"  # subquest list
ITEMS_KEY = "DLLOBLBEBPM"      # dialog items within a subquest
SUBQ_TITLE_KEY = "CGJPNLJCKKB" # subquest title object


def replace_hashes(obj: Any, text_map: dict[str, str]) -> Any:
    """递归遍历 JSON 树，将所有整数替换为 TextMap 中的对应文本。

    这是整个提取管道的核心工具函数。从 PoC 验证移植而来，
    已确认对原神 quest JSON 可正常工作。

    Args:
        obj: 待替换的 JSON 对象，dict / list / int / str 等任意嵌套结构。
        text_map: {哈希值字符串: 文本} 映射表。
            对于原神，此表由 TextMap + TextMap_Medium 合并而成。

    Returns:
        替换后的对象。整数若在 text_map 中有映射则替换为文本，
        未找到则保留原整数。bool 类型不会被替换（它虽是 int 子类但不是哈希）。
    """
    if isinstance(obj, dict):
        return {k: replace_hashes(v, text_map) for k, v in obj.items()}
    if isinstance(obj, list):
        return [replace_hashes(v, text_map) for v in obj]
    if isinstance(obj, int):
        if isinstance(obj, bool):
            return obj
        txt = text_map.get(str(obj), "")
        return txt if txt else obj
    return obj


def merge_text_maps(paths: list[str]) -> dict[str, str]:
    """加载并合并多个 TextMap JSON 文件为单一查找表。

    Args:
        paths: TextMap JSON 文件路径列表。

    Returns:
        {哈希值字符串: 文本} 的合并字典。后加载的会覆盖先加载的同名 key。
    """
    combined: dict[str, str] = {}
    for path in paths:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                combined.update(json.load(f))
    return combined


class BaseExtractor:
    """多游戏文本提取器基类。

    子类只需覆盖三个类属性即可获得完整的 extract_quests 功能：
        game_name: str       — 游戏标识符
        text_map_paths: list — TextMap 文件相对路径，可用 {lang} 占位符
        quest_data_path: str — quest JSON 数据目录在 raw repo 中的相对路径

    如有特殊需求（如星铁的 xxhash TextMap），覆盖 load_text_map() 即可。
    """

    game_name: str = ""
    text_map_paths: list[str] = []
    quest_data_path: str = ""

    def __init__(self, raw_repo_path: str, lang: str = "CHS") -> None:
        """初始化提取器。

        Args:
            raw_repo_path: sparse checkout 后的 raw data 本地路径。
            lang: 目标语言代码（CHS / JP / EN / KR ...）。
        """
        self.raw_repo_path = raw_repo_path
        self.lang = lang

    def load_text_map(self) -> dict[str, str]:
        """加载并合并当前语言的 TextMap 文件。

        使用 text_map_paths 中的路径模板，将 {lang} 替换为 self.lang，
        然后调用 merge_text_maps() 合并。

        Returns:
            {哈希值字符串: 文本} 的映射字典。
        """
        paths = [
            os.path.join(self.raw_repo_path, path.format(lang=self.lang))
            for path in self.text_map_paths
        ]
        missing = [path for path in paths if not os.path.exists(path)]
        if missing:
            raise FileNotFoundError(
                "Missing TextMap file(s) for "
                f"{self.game_name or self.__class__.__name__} lang={self.lang}: "
                + ", ".join(missing)
            )
        return merge_text_maps(paths)

    def extract_quests(self, output_path: str | None = None) -> str:
        """从 raw data 中提取所有 quest 对话，产出一个 JSONL 文件。

        默认实现：
        1. 加载 TextMap
        2. 遍历 quest_data_path 下所有 *.json 文件
        3. 对每个文件调用 replace_hashes() 递归替换所有整数哈希
        4. 将替换后的 quest dict 作为一行 JSON 写入 JSONL

        Args:
            output_path: JSONL 输出路径。默认为当前目录下 quest_{lang}.jsonl。

        Returns:
            输出的 JSONL 文件路径。
        """
        text_map = self.load_text_map()
        data_dir = os.path.join(self.raw_repo_path, self.quest_data_path)
        if not os.path.isdir(data_dir):
            raise FileNotFoundError(f"Quest data directory not found: {data_dir}")

        quest_files = sorted(glob.iglob(os.path.join(data_dir, "*.json")))
        if not quest_files:
            raise FileNotFoundError(f"No quest JSON files found in: {data_dir}")

        if output_path is None:
            output_path = os.path.join("build", f"quest_{self.lang}.jsonl")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        count = 0
        with open(output_path, "w", encoding="utf-8") as out:
            for file_path in quest_files:
                with open(file_path, encoding="utf-8") as fh:
                    try:
                        quest = json.load(fh)
                    except json.JSONDecodeError:
                        continue
                quest = replace_hashes(quest, text_map)
                if quest:
                    out.write(json.dumps(quest, ensure_ascii=False) + "\n")
                    count += 1

        if count == 0:
            raise ValueError(f"No valid quest JSON files were extracted from: {data_dir}")

        return output_path
