"""CLI entry point for BusinessRadar."""

import json
from typing import Optional

import typer

from businessradar.config import Config, load_config
from businessradar.page_fetcher import PageFetcher
from businessradar.trial_loop import TrialLoop

app = typer.Typer(
    name="businessradar",
    help="招投标信息智能提取工具 — LLM 驱动的自动脚本生成",
)


@app.command()
def extract(
    url: str = typer.Option(..., "--url", help="目标列表页 URL"),
    query: str = typer.Option(..., "--query", help="自然语言描述，如'昨天的信息化采购公告'"),
    model: Optional[str] = typer.Option(None, "--model", help="LLM 模型名称"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="LLM API key"),
    max_retries: Optional[int] = typer.Option(None, "--max-retries", help="试错上限"),
    max_pages: Optional[int] = typer.Option(None, "--max-pages", help="翻页上限"),
    config_path: Optional[str] = typer.Option(None, "--config-path", help="配置文件路径"),
) -> None:
    """从给定的 URL 提取招投标信息。"""
    config = load_config(
        cli_overrides={
            "llm_model": model,
            "api_key": api_key,
            "max_retries": max_retries,
            "max_pages": max_pages,
        },
        config_path=config_path,
    )

    fetcher = PageFetcher(config)
    loop = TrialLoop(
        config,
        progress_callback=_print_progress,
        human_input_callback=_human_input,
    )

    # 1. Fetch page HTML
    fetch_result = fetcher.fetch(url)

    # 2. Run trial loop: analyze → generate → run → evaluate (with retry)
    result = loop.execute(url, query, fetch_result)

    if result.success:
        typer.echo(json.dumps(result.data, ensure_ascii=False))
    else:
        typer.echo(f"Error: {result.error}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


def _print_progress(round_num: int, message: str) -> None:
    """Display trial loop progress to the terminal."""
    typer.echo(f"[第 {round_num} 轮] {message}", err=True)


def _human_input(issues: list[str]) -> str:
    """Prompt user for guidance when trial loop stagnates."""
    typer.echo("\n⚠️  试错循环停滞，需要你的指导：", err=True)
    for issue in issues:
        typer.echo(f"  - {issue}", err=True)
    return typer.prompt("请输入修改建议（直接回车跳过）")
