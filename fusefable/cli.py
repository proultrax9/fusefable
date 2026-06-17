from __future__ import annotations
import asyncio
import json
import sys
from typing import Optional
import typer
from fusefable.config import load_config, save_config, default_config_path, Config
from fusefable.core import fuse
from fusefable.wizard import run_wizard

app = typer.Typer(help="Fuse Fable - fuse multiple AI models, judge the best answer")


def _load_or_die() -> Config:
    try:
        return load_config(default_config_path())
    except FileNotFoundError:
        typer.echo("Not configured yet - run `fusefable config` first", err=True)
        raise typer.Exit(1)


def _resolve_question(question: Optional[str]) -> str:
    """รับคำถามจาก arg หรือ stdin (สำหรับ pipe/subagent)."""
    if question and question != "-":
        return question
    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            return data
    typer.echo("No question given (pass an argument or pipe via stdin)", err=True)
    raise typer.Exit(1)


@app.command()
def ask(
    question: Optional[str] = typer.Argument(None,
        help="คำถาม (เว้นว่าง = อ่านจาก stdin)"),
    show_all: bool = typer.Option(False, "--show-all", help="แสดงคำตอบทุกตัว"),
    models: Optional[str] = typer.Option(None, "--models",
        help="จำกัดเฉพาะโมเดลที่ระบุ คั่นด้วย comma"),
    cheap: bool = typer.Option(False, "--cheap", help="ใช้ cheap_models ใน config"),
    json_out: bool = typer.Option(False, "--json", help="output เป็น JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q",
        help="พิมพ์เฉพาะคำตอบ (เหมาะกับ pipe/subagent)"),
):
    """ถามคำถาม -> ได้คำตอบที่ดีที่สุดจากการฟิวชั่น."""
    cfg = _load_or_die()
    q = _resolve_question(question)
    model_list = [m.strip() for m in models.split(",")] if models else None

    try:
        result = asyncio.run(fuse(cfg, q, models=model_list, cheap=cheap))
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    if json_out:
        typer.echo(json.dumps({
            "answer": result.text,
            "chosen_model": result.chosen_model,
            "reason": result.reason,
            "cost_usd": result.cost_usd,
            "candidates": [{"model": c.model, "text": c.text}
                           for c in result.all_completions],
        }, ensure_ascii=False, indent=2))
        return

    if quiet:
        typer.echo(result.text)
        return

    if show_all:
        for c in result.all_completions:
            typer.echo(f"\n--- {c.model} ---\n{c.text}")
        typer.echo(f"\n=== Judge reason ===\n{result.reason}")
    typer.echo(f"\n=== Best answer (from {result.chosen_model}) ===")
    typer.echo(result.text)
    typer.echo(f"\n[estimated cost: ${result.cost_usd:.4f}]")


@app.command()
def config():
    """ตั้งค่า provider / API key / โมเดล (setup wizard)."""
    cfg = run_wizard()
    path = default_config_path()
    save_config(cfg, path)
    typer.echo(f"Saved to {path}")


@app.command()
def mcp():
    """รันเป็น MCP server (stdio) - เชื่อม Cursor / VS Code / Claude / agent อื่น."""
    from fusefable.mcp_server import run_mcp
    run_mcp()


if __name__ == "__main__":
    app()
