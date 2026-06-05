"""星穹铁道（TurnBasedGameData）提取器 — Phase 5。

数据源：DimbreathBot/TurnBasedGameData
- TextMap：单表 TextMap{lang}.json + TextMapMain{lang}.json
- Story 数据：Story/ 目录
- 哈希方案：xxhash
"""

from __future__ import annotations

from hoyo_story.extract.base import BaseExtractor


class StarrailExtractor(BaseExtractor):
    """星穹铁道剧情文本提取器 — Phase 5 实现。

    与原神的关键差异：
    1. TextMap 使用 xxhash 而非简单整数哈希
    2. 只有单表 TextMap（无 Medium 分拆）
    3. 故事数据在 Story/ 目录，结构可能更规整
    4. 参考实现：mrzjy/StarrailDialogue 的 util/common.py
    """

    game_name = "starrail"
    text_map_paths = [
        "TextMap/TextMap{lang}.json",
        "TextMap/TextMapMain{lang}.json",
    ]
    quest_data_path = "Story"

    def load_text_map(self) -> dict[str, str]:
        """加载 xxhash 格式的 TextMap。

        TurnBasedGameData 的 TextMap 使用 xxhash 作为 key，
        与原神的简单整数哈希不同。需要实现 xxhash 解析。
        """
        raise NotImplementedError("load_text_map — Phase 5 实现")

    def extract_quests(self) -> str:
        """从 Story/ 目录提取所有剧情对话。

        Story/ 目录的结构待调研（Phase 5），可能与原神的
        BinOutput/CodexQuest 结构不同。
        """
        raise NotImplementedError("extract_quests — Phase 5 实现")
