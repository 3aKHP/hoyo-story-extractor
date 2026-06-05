"""CLI — typer-based command-line interface.

Commands:
    fetch    — sparse checkout raw data
    extract  — run game-specific extraction (quests/talks/avatars/misc/all)
    convert  — JSONL → .txt conversion
    pipeline — run extract → convert in sequence
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import typer

from hoyo_story import __version__
from hoyo_story.convert import (
    convert_avatars,
    convert_misc,
    convert_quests,
    convert_talks,
)
from hoyo_story.fetch import fetch_raw, get_repo_url

app = typer.Typer(
    name="hoyo-extract",
    help="HoYoverse story text extraction pipeline",
    no_args_is_help=True,
)

IMPLEMENTED_GAMES = {"genshin", "starrail"}


def _run_cli(action: Callable[[], None]) -> None:
    try:
        action()
    except (FileNotFoundError, NotImplementedError, RuntimeError, ValueError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


def _version_callback(value: bool) -> None:
    if value:
        print(f"hoyo-story-extractor v{__version__}")
        raise typer.Exit()


@app.callback()
def common(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    pass


@app.command()
def fetch(
    game: Annotated[str, typer.Argument(help="Game identifier: genshin")],
    target_dir: Annotated[str, typer.Argument(help="Clone destination directory")],
    proxy: Annotated[
        str | None,
        typer.Option("--proxy", help="HTTP(S) proxy (e.g. http://127.0.0.1:7897)"),
    ] = None,
) -> None:
    """Sparse checkout a game's raw data repository."""
    _ensure_implemented_game(game)

    def action() -> None:
        url = get_repo_url(game)
        typer.echo(f"Fetching {game} from {url}")
        fetch_raw(game, target_dir, proxy=proxy)
        typer.echo(f"✓ Done: {target_dir}")

    _run_cli(action)


@app.command()
def extract(
    game: Annotated[str, typer.Argument(help="Game identifier: genshin")],
    repo: Annotated[str, typer.Argument(help="Path to raw data repository")],
    lang: Annotated[str, typer.Option("--lang", "-l", help="Language code")] = "CHS",
    output: Annotated[
        str | None, typer.Option("--output", "-o", help="Output path / directory")
    ] = None,
    kind: Annotated[
        str, typer.Option("--type", "-t", help="Data type: quests, talks, avatars, misc, all")
    ] = "quests",
) -> None:
    """Extract text from raw data into JSONL files."""
    def action() -> None:
        extractor = _get_extractor(game, repo, lang)

        handlers = {
            "quests": lambda: _extract_one(extractor.extract_quests, output),
            "talks": lambda: _extract_one(extractor.extract_talks, output),
            "avatars": lambda: _extract_one(extractor.extract_avatars, output),
            "misc": lambda: _handle_misc(extractor, output),
        }

        if kind == "all":
            for k, handler in handlers.items():
                typer.echo(f"  [{k}]...")
                handler()
            typer.echo("✓ All types extracted")
        elif kind in handlers:
            handlers[kind]()
        else:
            raise typer.BadParameter(
                f"Unknown type: {kind}. Use: quests, talks, avatars, misc, all"
            )

    _run_cli(action)


def _extract_one(method, output):
    result = method(output)
    typer.echo(f"  ✓ {result}")


def _handle_misc(extractor, output_dir):
    results = extractor.extract_misc(output_dir)
    for category, path in results.items():
        typer.echo(f"  ✓ [{category}] {path}")


@app.command()
def convert(
    input_path: Annotated[str, typer.Argument(help="JSONL file or directory to convert")],
    output_dir: Annotated[str, typer.Argument(help="Output directory for .txt files")],
    kind: Annotated[
        str, typer.Option("--type", "-t", help="Data type: quests, talks, avatars, misc")
    ] = "quests",
) -> None:
    """Convert JSONL files into per-item .txt files."""
    converters = {
        "quests": convert_quests,
        "talks": convert_talks,
        "avatars": convert_avatars,
        "misc": convert_misc,
    }

    if kind not in converters:
        raise typer.BadParameter(f"Unknown type: {kind}")

    def action() -> None:
        files = converters[kind](input_path, output_dir)
        typer.echo(f"✓ Converted {len(files)} files → {output_dir}")

    _run_cli(action)


@app.command()
def pipeline(
    game: Annotated[str, typer.Argument(help="Game identifier: genshin")],
    repo: Annotated[
        str,
        typer.Argument(help="Path to raw data repository"),
    ],
    output_dir: Annotated[str, typer.Argument(help="Output directory for .txt files")],
    lang: Annotated[str, typer.Option("--lang", "-l", help="Language code")] = "CHS",
    kind: Annotated[
        str, typer.Option("--type", "-t", help="Data type: quests, talks, avatars, misc, all")
    ] = "quests",
) -> None:
    """Run extract → convert in one command."""
    def action() -> None:
        extractor = _get_extractor(game, repo, lang)

        # Select game-specific converters
        _convert_quests = convert_quests
        _convert_talks = convert_talks
        _convert_avatars = convert_avatars
        if game == "starrail":
            from hoyo_story.convert import (
                convert_starrail_quests,
                convert_starrail_talks,
            )

            _convert_quests = convert_starrail_quests
            _convert_talks = convert_starrail_talks

        pipelines = {
            "quests": (extractor.extract_quests, _convert_quests),
            "talks": (extractor.extract_talks, _convert_talks),
            "avatars": (extractor.extract_avatars, _convert_avatars),
        }

        if kind == "all":
            for k, (extract_fn, convert_fn) in pipelines.items():
                typer.echo(f"[{k}] Extracting...")
                jl = extract_fn()
                typer.echo(f"[{k}] Converting...")
                out = f"{output_dir}/{k}"
                n = len(convert_fn(jl, out))
                typer.echo(f"  ✓ {n} files → {out}")

            typer.echo("[misc] Extracting...")
            results = extractor.extract_misc(f"{output_dir}/misc_jsonl")
            for category, jp in results.items():
                typer.echo(f"[misc/{category}] Converting...")
                n = len(convert_misc(jp, f"{output_dir}/misc/{category}"))
                typer.echo(f"  ✓ {n} files → {output_dir}/misc/{category}")
            typer.echo("✓ All done")
        elif kind in pipelines:
            extract_fn, convert_fn = pipelines[kind]
            typer.echo(f"[1/2] Extracting {kind}...")
            jl = extract_fn()
            typer.echo("[2/2] Converting...")
            n = len(convert_fn(jl, output_dir))
            typer.echo(f"✓ {n} files → {output_dir}")
        elif kind == "misc":
            typer.echo("[1/2] Extracting misc...")
            results = extractor.extract_misc(f"{output_dir}/jsonl")
            for category, jp in results.items():
                typer.echo(f"[2/2] Converting {category}...")
                n = len(convert_misc(jp, f"{output_dir}/{category}"))
                typer.echo(f"  ✓ {n} files → {output_dir}/{category}")
        else:
            raise typer.BadParameter(f"Unknown type: {kind}")

    _run_cli(action)


def _ensure_implemented_game(game: str) -> None:
    if game not in IMPLEMENTED_GAMES:
        raise typer.BadParameter(
            f"{game} is planned but not implemented yet. Supported now: genshin"
        )


def _get_extractor(game: str, repo: str, lang: str):
    _ensure_implemented_game(game)
    if game == "genshin":
        from hoyo_story.extract.genshin import GenshinExtractor

        return GenshinExtractor(repo, lang)
    if game == "starrail":
        from hoyo_story.extract.starrail import StarrailExtractor

        return StarrailExtractor(repo, lang)
    raise typer.BadParameter(f"Unknown game: {game}. Supported: genshin, starrail")


if __name__ == "__main__":
    app()
