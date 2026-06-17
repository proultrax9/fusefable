from __future__ import annotations
import asyncio
import httpx
import typer
from fusefable.config import load_config, save_config, default_config_path, Config
from fusefable.routing import build_routes, build_judge_provider
from fusefable.fusion import run_fusion
from fusefable.wizard import run_wizard

app = typer.Typer(help="Fuse Fable — ฟิวชั่นหลาย AI เลือกคำตอบดีสุด")


def _load_or_die() -> Config:
    try:
        return load_config(default_config_path())
    except FileNotFoundError:
        typer.echo("ยังไม่ได้ตั้งค่า — รัน `fusefable config` ก่อน", err=True)
        raise typer.Exit(1)


async def _run(cfg: Config, question: str, show_all: bool):
    async with httpx.AsyncClient(timeout=None) as http:
        routes = build_routes(cfg, http)
        judge_prov = build_judge_provider(cfg, http)
        result = await run_fusion(routes, judge_prov, cfg.judge_model,
                                  question, cfg.timeout_seconds)
    if show_all:
        for c in result.all_completions:
            typer.echo(f"\n--- {c.model} ---\n{c.text}")
        typer.echo(f"\n=== Judge reason ===\n{result.reason}")
    typer.echo(f"\n=== คำตอบที่ดีที่สุด (จาก {result.chosen_model}) ===")
    typer.echo(result.text)
    typer.echo(f"\n[ประมาณค่าใช้จ่าย: ${result.cost_usd:.4f}]")


@app.command()
def ask(question: str, show_all: bool = typer.Option(False, "--show-all")):
    """ถามคำถาม → ได้คำตอบที่ดีที่สุดจากการฟิวชั่น."""
    cfg = _load_or_die()
    asyncio.run(_run(cfg, question, show_all))


@app.command()
def config():
    """ตั้งค่า provider / API key / โมเดล (setup wizard)."""
    cfg = run_wizard()
    path = default_config_path()
    save_config(cfg, path)
    typer.echo(f"บันทึกแล้วที่ {path}")


if __name__ == "__main__":
    app()
