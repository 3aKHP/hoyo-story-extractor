"""绝区零（ZenlessData）提取器 — Phase 6。

数据源：git.mero.moe/dimbreath/ZenlessData（非 GitHub，Gitea 自托管）
- DMCA 风险更低（非美国管辖）
- 目录结构和 TextMap 格式待调研
"""

from __future__ import annotations

from hoyo_story.extract.base import BaseExtractor


class ZZZExtractor(BaseExtractor):
    """绝区零剧情文本提取器 — Phase 6 实现。

    特殊考虑：
    1. 数据源不在 GitHub 上（git.mero.moe），fetch 步骤需要适配
    2. 目录结构和 TextMap 格式尚未验证
    3. 社区暂无已知的提取工具可作为参考实现
    """

    game_name = "zzz"
    text_map_paths: list[str] = []  # 待调研
    quest_data_path: str = ""       # 待调研

    def load_text_map(self) -> dict[str, str]:
        """加载 TextMap — 格式待调研。"""
        raise NotImplementedError("load_text_map — Phase 6 实现")

    def extract_quests(self) -> str:
        """提取剧情对话 — 数据路径待调研。"""
        raise NotImplementedError("extract_quests — Phase 6 实现")
