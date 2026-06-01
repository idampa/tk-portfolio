# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp>=1.0",
#   "supabase>=2.0",
#   "python-dotenv>=1.0",
# ]
# ///
"""
TK Portfolio MCP Server
Claude가 포트폴리오 DB에 직접 접근하는 MCP 서버

실행: uv run /Users/BigChoi/Desktop/tk-portfolio/mcp_server.py
"""

import os
import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client
from mcp.server.fastmcp import FastMCP

# ── 환경변수: 스크립트와 같은 디렉토리의 .env 로드 ──
load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

mcp = FastMCP("tk-portfolio")


# ════════════════════════════════════════════════
# Tool 1: get_portfolio — 전체 포트폴리오 조회
# ════════════════════════════════════════════════

@mcp.tool()
def get_portfolio(account: Optional[str] = None) -> str:
    """
    전체 포트폴리오 조회 (보유 종목 + 예수금 + 총평가금액).
    account: 'kiwoom' | 'toss' — 생략 시 전체 조회.
    """
    try:
        q = sb.from_("holdings").select("*")
        if account:
            q = q.eq("account", account)
        holdings = q.execute().data

        cash_res = sb.from_("cash").select("*").execute().data
        cash = {c["account"]: c["amount"] for c in cash_res}

        eval_total = sum(cash.values())
        lines = []

        for acc in ["kiwoom", "toss"]:
            acc_h = [h for h in holdings if h["account"] == acc]
            if not acc_h:
                continue
            lines.append(f"\n[{acc.upper()} | 예수금 {cash.get(acc, 0):,}원]")
            for h in acc_h:
                cur = h["current_price"] or h["avg"]
                val = cur * h["qty"]
                pnl = val - h["avg"] * h["qty"]
                pct = (cur - h["avg"]) / h["avg"] * 100 if h["avg"] else 0
                eval_total += val
                arrow = "▲" if pnl >= 0 else "▼"
                lines.append(
                    f"  {arrow} {h['name']} ({h['id']}) | "
                    f"{h['qty']}주 | 평단 {h['avg']:,} | 현재 {cur:,} | "
                    f"{pct:+.1f}% | 손익 {pnl:+,}원"
                )

        cash_total = sum(cash.values())
        cash_pct = cash_total / eval_total * 100 if eval_total else 0
        header = [
            "──── 포트폴리오 현황 ────",
            f"총평가금액  {eval_total:,}원",
            f"현금        {cash_total:,}원  (비중 {cash_pct:.1f}%)",
            f"  키움 {cash.get('kiwoom', 0):,}원  |  토스 {cash.get('toss', 0):,}원",
        ]
        return "\n".join(header + lines)
    except Exception as e:
        return f"오류: {e}"


# ════════════════════════════════════════════════
# Tool 2: get_trade_log — 매매 일지 조회
# ════════════════════════════════════════════════

@mcp.tool()
def get_trade_log(
    stock_id: Optional[str] = None,
    trade_type: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    매매 일지 조회 (날짜 내림차순).
    stock_id: 'SKH' 등 종목 ID — 생략 시 전체.
    trade_type: 'buy' | 'sell' | 'loss' — 생략 시 전체.
    limit: 최대 반환 건수 (기본 20).
    """
    try:
        q = (
            sb.from_("trade_log")
            .select("*")
            .order("date", desc=True)
            .order("id", desc=True)
            .limit(limit)
        )
        if stock_id:
            q = q.eq("stock_id", stock_id)
        if trade_type:
            q = q.eq("type", trade_type)

        trades = q.execute().data
        if not trades:
            return "매매 기록이 없습니다."

        LABEL = {"buy": "📈 매수", "sell": "📉 매도", "loss": "🔴 손절"}
        lines = [f"매매 일지 — {len(trades)}건"]
        for t in trades:
            price_str = f"{t['price']:,}원" if t.get("price") else "-"
            pnl_str   = f"  →  {t['pnl']:+,}원" if t.get("pnl") is not None else ""
            memo_str  = f"  [{t['memo']}]" if t.get("memo") else ""
            label     = LABEL.get(t["type"], t["type"])
            lines.append(
                f"{t['date']}  {label}  {t['name']}  "
                f"{t.get('qty', '-')}주 @ {price_str}{pnl_str}{memo_str}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"오류: {e}"


# ════════════════════════════════════════════════
# Tool 3: add_trade — 매수/매도 기록 추가
# ════════════════════════════════════════════════

@mcp.tool()
def add_trade(
    stock_id: str,
    name: str,
    trade_type: str,
    qty: int,
    price: int,
    account: str,
    memo: str = "",
) -> str:
    """
    매수/매도 기록을 추가하고 holdings를 자동 업데이트한다.
    trade_type: 'buy' | 'sell' | 'loss'
    account:    'kiwoom' | 'toss'
    매수 시 — qty·평단 재계산. 신규 종목이면 holdings에 자동 생성.
    매도/손절 시 — qty 차감, 전량이면 holdings에서 제거. pnl 자동 계산.
    """
    try:
        today = datetime.date.today().isoformat()

        # 기존 holdings 조회 (pnl 계산 + qty 업데이트용)
        existing = sb.from_("holdings").select("*").eq("id", stock_id).execute().data
        holding  = existing[0] if existing else None

        # sell/loss 시 pnl 자동 계산
        pnl = None
        if trade_type in ("sell", "loss") and holding:
            pnl = (price - holding["avg"]) * qty

        # ① trade_log INSERT
        sb.from_("trade_log").insert({
            "date":     today,
            "stock_id": stock_id,
            "name":     name,
            "type":     trade_type,
            "qty":      qty,
            "price":    price,
            "pnl":      pnl,
            "memo":     memo,
        }).execute()

        # ② holdings UPSERT
        if trade_type == "buy":
            if holding:
                new_qty = holding["qty"] + qty
                new_avg = (holding["avg"] * holding["qty"] + price * qty) // new_qty
                sb.from_("holdings").update({
                    "qty":           new_qty,
                    "avg":           new_avg,
                    "current_price": price,
                }).eq("id", stock_id).execute()
                holding_msg = (
                    f"holdings 업데이트 — "
                    f"{holding['qty']}주 → {new_qty}주 | "
                    f"평단 {holding['avg']:,} → {new_avg:,}원"
                )
            else:
                sb.from_("holdings").insert({
                    "id":            stock_id,
                    "account":       account,
                    "ticker":        stock_id,
                    "naver":         stock_id,
                    "name":          name,
                    "qty":           qty,
                    "avg":           price,
                    "current_price": price,
                    "prev_price":    price,
                }).execute()
                holding_msg = f"새 종목 등록 — {name} {qty}주 @ {price:,}원"

        else:  # sell / loss
            if holding:
                new_qty = holding["qty"] - qty
                if new_qty <= 0:
                    sb.from_("holdings").delete().eq("id", stock_id).execute()
                    holding_msg = f"전량 매도 — holdings에서 {name} 제거"
                else:
                    sb.from_("holdings").update({"qty": new_qty}).eq("id", stock_id).execute()
                    holding_msg = f"holdings 업데이트 — {holding['qty']}주 → {new_qty}주"
            else:
                holding_msg = "⚠ holdings에 해당 종목 없음 (trade_log만 기록됨)"

        pnl_str = f" | 실현손익 {pnl:+,}원" if pnl is not None else ""
        return (
            f"✅ 거래 기록 완료\n"
            f"{today}  {trade_type.upper()}  {name}  {qty}주 @ {price:,}원{pnl_str}\n"
            f"{holding_msg}"
        )
    except Exception as e:
        return f"오류: {e}"


# ════════════════════════════════════════════════
# Tool 4: get_summary — 수익률 종합 요약
# ════════════════════════════════════════════════

@mcp.tool()
def get_summary() -> str:
    """
    포트폴리오 종합 수익률 요약.
    미실현손익 / 확정손익 / 합산 / 종목별 기여도 순위 / 최근 7일 추세.
    """
    try:
        holdings  = sb.from_("holdings").select("*").execute().data
        cash_res  = sb.from_("cash").select("*").execute().data
        rg_stocks = sb.from_("realized_gains").select("*").execute().data
        rg_monthly = sb.from_("realized_gains_monthly").select("*").execute().data
        history   = (
            sb.from_("portfolio_history")
            .select("date,total")
            .order("date", desc=True)
            .limit(7)
            .execute()
            .data
        )

        cash_total = sum(c["amount"] for c in cash_res)
        eval_total = cash_total
        cost_total = cash_total
        stock_pnl  = []

        for h in holdings:
            cur  = h["current_price"] or h["avg"]
            val  = cur * h["qty"]
            cost = h["avg"] * h["qty"]
            pnl  = val - cost
            pct  = (cur - h["avg"]) / h["avg"] * 100 if h["avg"] else 0
            eval_total += val
            cost_total += cost
            stock_pnl.append({"name": h["name"], "pnl": pnl, "pct": pct})

        stock_pnl.sort(key=lambda x: x["pnl"], reverse=True)

        total_unrealized  = sum(s["pnl"] for s in stock_pnl)
        total_realized    = sum(r["pnl"] for r in rg_stocks)
        invested          = cost_total - cash_total  # 실제 투자원금
        return_pct        = total_unrealized / invested * 100 if invested else 0

        MONTH_ORDER = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]
        rg_monthly_sorted = sorted(
            rg_monthly,
            key=lambda x: MONTH_ORDER.index(x["month"]) if x["month"] in MONTH_ORDER else 99,
        )

        lines = [
            "══════ 포트폴리오 종합 요약 ══════",
            f"총평가금액   {eval_total:,}원",
            f"미실현손익   {total_unrealized:+,}원  ({return_pct:+.2f}%)",
            f"확정손익     {total_realized:+,}원",
            f"합산손익     {total_unrealized + total_realized:+,}원",
            "",
            "── 종목별 미실현손익 (수익 순) ──",
        ]
        for s in stock_pnl:
            arrow = "▲" if s["pnl"] >= 0 else "▼"
            lines.append(
                f"  {arrow} {s['name']:<14}  {s['pnl']:>+13,}원  ({s['pct']:+.1f}%)"
            )

        lines += ["", "── 월별 확정손익 ──"]
        for m in rg_monthly_sorted:
            arrow = "▲" if m["pnl"] >= 0 else "▼"
            lines.append(f"  {arrow} {m['month']:>4}  {m['pnl']:>+13,}원")

        if history:
            hist_asc = sorted(history, key=lambda x: x["date"])
            lines += ["", "── 최근 포트폴리오 추세 ──"]
            for i, h in enumerate(hist_asc):
                diff_str = ""
                if i > 0:
                    diff = h["total"] - hist_asc[i - 1]["total"]
                    diff_str = f"  ({diff:+,}원)"
                lines.append(f"  {h['date']}  {h['total']:,}원{diff_str}")

        return "\n".join(lines)
    except Exception as e:
        return f"오류: {e}"


if __name__ == "__main__":
    mcp.run()
