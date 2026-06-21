from __future__ import annotations
import asyncio
import json
import sys
from typing import Optional
import typer
from fusefable.config import load_config, save_config, default_config_path, Config
from fusefable.core import fuse
from fusefable.wizard import run_wizard

# Windows console บางเครื่อง codepage ไม่ใช่ UTF-8 → พิมพ์ภาษาไทยแล้ว crash
# บังคับ stdout/stderr เป็น UTF-8 เพื่อให้ help/ผลลัพธ์ภาษาไทยไม่พัง
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

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
    compress: Optional[bool] = typer.Option(None, "--compress/--no-compress",
        help="บีบ prompt ก่อนส่งเพื่อลด token (default ตาม config)"),
    ensemble: Optional[bool] = typer.Option(None, "--ensemble/--judge",
        help="รวมคำตอบหลายตัวเป็นหนึ่ง (ensemble) แทนเลือกตัวเดียว (judge)"),
    use_cache: Optional[bool] = typer.Option(None, "--cache/--no-cache",
        help="ใช้ cache คำตอบ (default ตาม config)"),
    json_out: bool = typer.Option(False, "--json", help="output เป็น JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v",
        help="แสดง cost / metadata (default = คำตอบอย่างเดียว)"),
    quiet: bool = typer.Option(False, "--quiet", "-q",
        help="(legacy) เหมือน default — พิมพ์เฉพาะคำตอบ"),
):
    """ถามคำถาม -> ได้คำตอบที่ดีที่สุดจากการฟิวชั่น."""
    cfg = _load_or_die()
    q = _resolve_question(question)
    model_list = [m.strip() for m in models.split(",")] if models else None

    try:
        result = asyncio.run(fuse(cfg, q, models=model_list, cheap=cheap,
                                  compress=compress, ensemble=ensemble,
                                  use_cache=use_cache))
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    comp = result.compression

    if json_out:
        out = {
            "answer": result.text,
            "chosen_model": result.chosen_model,
            "reason": result.reason,
            "cost_usd": result.cost_usd,
            "candidates": [{"model": c.model, "text": c.text}
                           for c in result.all_completions],
        }
        if comp is not None:
            out["compression"] = {
                "original_chars": comp.original_chars,
                "final_chars": comp.final_chars,
                "saved_pct": round(comp.saved_pct, 1),
                "method": comp.method,
            }
        out["cached"] = result.cached
        if result.budget_warning:
            out["budget_warning"] = result.budget_warning
        typer.echo(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if show_all:
        if result.budget_warning:
            typer.echo(f"⚠️  {result.budget_warning}", err=True)
        for c in result.all_completions:
            typer.echo(f"\n--- {c.model} ---\n{c.text}")
        typer.echo(f"\n=== Judge reason ===\n{result.reason}")
        typer.echo(f"\n=== Answer ===\n{result.text}")
        if comp is not None:
            typer.echo(f"\n[compressed: {comp.original_chars}→{comp.final_chars} chars, "
                       f"~{comp.saved_pct:.0f}% saved via {comp.method}]")
        cost_note = "cached, $0" if result.cached else f"${result.cost_usd:.4f}"
        typer.echo(f"[estimated cost: {cost_note}]")
        return

    if verbose:
        if result.budget_warning:
            typer.echo(f"⚠️  {result.budget_warning}", err=True)
        label = ("ensemble" if result.chosen_model == "ensemble"
                 else f"from {result.chosen_model}")
        typer.echo(f"=== Answer ({label}) ===")
        typer.echo(result.text)
        if comp is not None:
            typer.echo(f"\n[compressed: {comp.original_chars}→{comp.final_chars} chars, "
                       f"~{comp.saved_pct:.0f}% saved via {comp.method}]")
        cost_note = "cached, $0" if result.cached else f"${result.cost_usd:.4f}"
        typer.echo(f"[estimated cost: {cost_note}]")
        return

    # default — ผู้ใช้เห็นแค่คำตอบสุดท้าย (Fuse กรองทุกอย่างเบื้องหลังแล้ว)
    typer.echo(result.text)


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


@app.command()
def gui():
    """เปิดหน้าต่างโปรแกรม (desktop window) แบบ Cursor/VS Code."""
    from fusefable.desktop import run_app
    run_app()   # โหลด config ถ้ามี ไม่งั้นเปิดหน้าตั้งค่าในตัวโปรแกรม


if __name__ == "__main__":
    app()
