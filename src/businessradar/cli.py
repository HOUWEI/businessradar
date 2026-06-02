"""CLI entry point for BusinessRadar."""

from typing import Optional

import typer

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
) -> None:
    """从给定的 URL 提取招投标信息。"""
    typer.echo("Not implemented yet.")


if __name__ == "__main__":
    app()
