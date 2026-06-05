"""Raw data 获取层 — 统一的 sparse checkout 接口。

通过环境变量注入 raw data 仓库地址，代码本身不硬编码任何 URL。
使用 subprocess 调用 git（比 gitpython 更可靠地处理 sparse checkout）。
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# ── Default sparse checkout paths per game ──────────────────────────────

GENSHIN_PATHS: list[str] = [
    "/TextMap/TextMapCHS.json",
    "/TextMap/TextMap_MediumCHS.json",
    "/TextMap/TextMapJP.json",
    "/TextMap/TextMap_MediumJP.json",
    "/TextMap/TextMapEN.json",
    "/TextMap/TextMap_MediumEN.json",
    "/BinOutput/CodexQuest/",
    "/BinOutput/Talk/",
    "/ExcelBinOutput/AvatarExcelConfigData.json",
    "/ExcelBinOutput/FetterInfoExcelConfigData.json",
    "/ExcelBinOutput/FettersExcelConfigData.json",
    "/ExcelBinOutput/FetterStoryExcelConfigData.json",
    "/ExcelBinOutput/DialogExcelConfigData.json",
    "/ExcelBinOutput/NpcExcelConfigData.json",
    "/ExcelBinOutput/MaterialExcelConfigData.json",
    "/ExcelBinOutput/WeaponExcelConfigData.json",
    "/ExcelBinOutput/ReliquaryExcelConfigData.json",
    "/ExcelBinOutput/ReliquarySetExcelConfigData.json",
    "/ExcelBinOutput/EquipAffixExcelConfigData.json",
    "/Readable/CHS/",
    "/Readable/EN/",
    "/Readable/JP/",
]

STARRAIL_PATHS: list[str] = [
    # TextMap (all supported languages)
    "/TextMap/TextMapCHS.json",
    "/TextMap/TextMapMainCHS.json",
    "/TextMap/TextMapJP.json",
    "/TextMap/TextMapMainJP.json",
    "/TextMap/TextMapEN.json",
    "/TextMap/TextMapMainEN.json",
    "/TextMap/TextMapKR.json",
    "/TextMap/TextMapMainKR.json",
    # Mission hierarchy
    "/ExcelOutput/MainMission.json",
    "/ExcelOutput/SubMission.json",
    "/ExcelOutput/MissionChapterConfig.json",
    # Talk sentence lookup
    "/ExcelOutput/TalkSentenceConfig.json",
    # Avatar / character data
    "/ExcelOutput/AvatarConfig.json",
    "/ExcelOutput/AvatarSkillTreeConfig.json",
    "/ExcelOutput/AvatarPromotionConfig.json",
    "/ExcelOutput/AvatarPlayerTitleConfig.json",
    # Item / misc
    "/ExcelOutput/ItemConfig.json",
    "/ExcelOutput/ItemConfigAvatar.json",
    "/ExcelOutput/ItemConfigBook.json",
    "/ExcelOutput/ItemConfigRelic.json",
    "/ExcelOutput/ItemConfigEquipment.json",
    "/ExcelOutput/ItemPlayerCard.json",
    # Level configs (dialogue / story / activity)
    "/Config/Level/Mission/",
    "/Config/Level/Story/",
    "/Config/Level/TrainVisitor/",
    "/Config/Level/Activity/",
    # Phone messages
    "/Config/Level/Message/",
]

ZZZ_PATHS: list[str] = []  # 待调研

GAME_PATHS: dict[str, list[str]] = {
    "genshin": GENSHIN_PATHS,
    "starrail": STARRAIL_PATHS,
    "zzz": ZZZ_PATHS,
}

GAME_ENV: dict[str, str] = {
    "genshin": "GENSHIN_RAW_REPO",
    "starrail": "STARRAIL_RAW_REPO",
    "zzz": "ZZZ_RAW_REPO",
}


def get_repo_url(game: str) -> str:
    """从环境变量读取指定游戏的 raw data 仓库地址。

    Args:
        game: 游戏标识符（"genshin" / "starrail" / "zzz"）。

    Returns:
        仓库 HTTPS URL。

    Raises:
        ValueError: game 无效或环境变量未设置。
    """
    if game not in GAME_ENV:
        raise ValueError(f"未知游戏: {game}，支持: {list(GAME_ENV)}")
    env_name = GAME_ENV[game]
    url = os.environ.get(env_name, "")
    if not url:
        raise ValueError(
            f"环境变量 {env_name} 未设置，无法获取 {game} raw data 仓库地址"
        )
    return url


def _run_git(args: Sequence[str], cwd: str | None = None) -> None:
    """Run a git command, raising RuntimeError on failure."""
    cmd = ["git"] + list(args)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}):\n"
            f"stderr: {result.stderr.strip()}"
        )


def fetch_raw(
    game: str,
    target_dir: str,
    *,
    paths: list[str] | None = None,
    proxy: str | None = None,
) -> None:
    """Sparse checkout 指定游戏的 raw data 仓库到本地目录。

    Args:
        game: 游戏标识符（"genshin" / "starrail" / "zzz"）。
        target_dir: clone 目标路径（目录必须不存在或为空）。
        paths: sparse checkout 路径列表。None 时使用游戏默认最小集。
        proxy: 可选 HTTP(S) 代理地址（如 "http://127.0.0.1:7897"）。

    Raises:
        ValueError: game 参数无效或对应环境变量未设置。
        RuntimeError: git 命令执行失败。
    """
    url = get_repo_url(game)
    if paths is None:
        paths = GAME_PATHS.get(game, [])
    if not paths:
        raise ValueError(f"游戏 {game} 没有配置 sparse checkout 路径")

    # Build git clone command with optional proxy
    clone_cmd = [
        "clone",
        "--depth=1",
        "--filter=blob:none",
        "--sparse",
    ]
    if proxy:
        clone_cmd += ["-c", f"http.proxy={proxy}", "-c", f"https.proxy={proxy}"]

    clone_cmd += [url, target_dir]

    _run_git(clone_cmd)

    # Set sparse checkout paths
    _run_git(["sparse-checkout", "set", "--no-cone", *paths], cwd=target_dir)


def main() -> None:
    """CLI entry point for fetch — minimal arg parsing without typer for now."""
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <game> <target_dir>")
        print(f"  Supported games: {list(GAME_ENV)}")
        print(f"  Set {', '.join(GAME_ENV.values())} environment variables for repo URLs")
        sys.exit(1)

    game = sys.argv[1]
    target_dir = sys.argv[2]

    try:
        fetch_raw(game, target_dir)
        print(f"✓ Sparse checkout complete: {target_dir}")
    except (ValueError, RuntimeError) as e:
        print(f"✗ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
