"""
migrate_data.py — 기존 JSON/HTML 데이터를 Supabase로 일괄 import

실행 전 준비:
  pip install supabase python-dotenv

실행:
  python migrate_data.py

주의: 이미 데이터가 있는 테이블에 재실행 시 upsert이므로 중복 없이 덮어씀
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    sys.exit("ERROR: .env 파일에 SUPABASE_URL, SUPABASE_SECRET_KEY가 설정되지 않았습니다.")

from supabase import create_client

client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

BASE_DIR = Path(__file__).parent


# ────────────────────────────────────────────────
# 헬퍼
# ────────────────────────────────────────────────

def upsert(table: str, rows: list, conflict_col: str = None):
    if not rows:
        print(f"  [{table}] 데이터 없음, 건너뜀")
        return
    resp = client.table(table).upsert(rows).execute()
    print(f"  [{table}] {len(rows)}건 upsert 완료")


def parse_pnl_str(s: str) -> Optional[int]:
    """'+81만' / '-109만' / '+1,867만' / '+0.7만' → 정수(원) 변환"""
    if s is None:
        return None
    s = s.replace(",", "").replace("+", "").strip()
    if "만" in s:
        v = float(s.replace("만", ""))
        return int(v * 10_000)
    try:
        return int(float(s))
    except ValueError:
        return None


# ────────────────────────────────────────────────
# 1. portfolio.json → holdings, cash, realized_gains, trade_log
# ────────────────────────────────────────────────

def migrate_portfolio_json():
    path = BASE_DIR / "portfolio.json"
    if not path.exists():
        print("  [portfolio.json] 파일 없음, 건너뜀")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # --- holdings ---
    holdings_rows = []
    for account, stocks in data.get("holdings", {}).items():
        for s in stocks:
            holdings_rows.append({
                "id":            s["id"],
                "account":       account,
                "ticker":        s.get("ticker", ""),
                "naver":         s.get("naver", s.get("ticker", "")),
                "name":          s["name"],
                "qty":           s["qty"],
                "avg":           s["avg"],
                "current_price": s.get("current_price"),
                "prev_price":    s.get("prev_price"),
            })
    upsert("holdings", holdings_rows)

    # --- cash ---
    cash_rows = [
        {"account": acc, "amount": amt}
        for acc, amt in data.get("cash", {}).items()
    ]
    upsert("cash", cash_rows)

    # --- realized_gains (종목별) ---
    rg = data.get("realized_gains", {})
    rg_rows = [
        {"name": s["name"], "pnl": s["pnl"], "type": s["type"]}
        for s in rg.get("stocks", [])
    ]
    # SERIAL PK이므로 delete-then-insert 방식 사용
    if rg_rows:
        client.table("realized_gains").delete().neq("id", 0).execute()
        client.table("realized_gains").insert(rg_rows).execute()
        print(f"  [realized_gains] {len(rg_rows)}건 insert 완료")

    # --- realized_gains_monthly ---
    rgm_rows = [
        {"month": m["name"], "pnl": m["pnl"]}
        for m in rg.get("monthly", [])
    ]
    upsert("realized_gains_monthly", rgm_rows)

    # --- trade_log (portfolio.json 구조 데이터: 04/14~05/15) ---
    tl_rows = []
    for t in data.get("trade_log", []):
        tl_rows.append({
            "date":     t["date"],           # "2026-05-15"
            "stock_id": t["id"],
            "name":     t["name"],
            "type":     t["type"],
            "qty":      t.get("qty"),
            "price":    t.get("price"),
            "pnl":      t.get("pnl"),
            "memo":     t.get("memo", ""),
        })
    # SERIAL PK이므로 insert (중복 방지를 위해 기존 데이터 먼저 삭제)
    if tl_rows:
        client.table("trade_log").delete().neq("id", 0).execute()
        client.table("trade_log").insert(tl_rows).execute()
        print(f"  [trade_log] portfolio.json {len(tl_rows)}건 insert 완료")


# ────────────────────────────────────────────────
# 2. HTML TRADE_LOG 구형 데이터 (01/29 ~ 04/13)
#    portfolio.json에 없는 이전 거래 기록
# ────────────────────────────────────────────────

HISTORICAL_TRADES = [
    # ── 4월 ──
    {"date": "2026-04-13", "stock_id": "ISC", "name": "ISC",            "type": "buy",  "qty": 10,  "price": 220500,   "pnl": None,       "memo": "HBM 소켓 수요 증가 추매"},
    {"date": "2026-04-16", "stock_id": "APR", "name": "에이피알",         "type": "buy",  "qty": 3,   "price": 405000,   "pnl": None,       "memo": "20일선 지지 확인 추매"},
    {"date": "2026-04-10", "stock_id": "ISC", "name": "ISC",            "type": "sell", "qty": 10,  "price": None,     "pnl": 380000,     "memo": "분할 익절"},
    {"date": "2026-04-10", "stock_id": "APR", "name": "에이피알",         "type": "sell", "qty": 12,  "price": None,     "pnl": 810000,     "memo": "분할 익절"},
    {"date": "2026-04-02", "stock_id": "ISC", "name": "ISC",            "type": "sell", "qty": 5,   "price": 244500,   "pnl": 340000,     "memo": "전쟁 불안 회피"},
    {"date": "2026-04-02", "stock_id": "SKH", "name": "SK하이닉스",       "type": "sell", "qty": 10,  "price": 860000,   "pnl": 1440000,    "memo": "전쟁 불안 회피"},
    {"date": "2026-04-02", "stock_id": "APR", "name": "에이피알",         "type": "sell", "qty": 15,  "price": 344000,   "pnl": 800000,     "memo": "전쟁 불안 회피"},
    {"date": "2026-04-02", "stock_id": "HWA", "name": "한화에어로스페이스", "type": "sell", "qty": 2,   "price": 1439000,  "pnl": 430000,     "memo": "전쟁 불안 회피"},
    # ── 3월 ──
    {"date": "2026-03-19", "stock_id": "POI", "name": "펄어비스",         "type": "loss", "qty": 83,  "price": 47550,    "pnl": -1090000,   "memo": ""},
    {"date": "2026-03-12", "stock_id": "HWS", "name": "한화솔루션",        "type": "loss", "qty": 26,  "price": None,     "pnl": 7000,       "memo": ""},
    {"date": "2026-03-11", "stock_id": "HWS", "name": "한화솔루션",        "type": "loss", "qty": 25,  "price": None,     "pnl": 12000,      "memo": ""},
    {"date": "2026-03-06", "stock_id": "HWS", "name": "한화솔루션",        "type": "loss", "qty": 16,  "price": None,     "pnl": -60000,     "memo": "손절"},
    {"date": "2026-03-11", "stock_id": "SKH", "name": "SK하이닉스",       "type": "sell", "qty": 8,   "price": 960000,   "pnl": 2330000,    "memo": ""},
    {"date": "2026-03-06", "stock_id": "DSE", "name": "두산에너빌리티",     "type": "sell", "qty": 15,  "price": 92500,    "pnl": 70000,      "memo": "현대차증권"},
    # ── 2월 ──
    {"date": "2026-02-27", "stock_id": "MAV", "name": "미래에셋벤처투자",   "type": "loss", "qty": 150, "price": 21600,    "pnl": -520000,    "memo": "손절"},
    {"date": "2026-02-25", "stock_id": "MAV", "name": "미래에셋벤처투자",   "type": "loss", "qty": 150, "price": 22200,    "pnl": -440000,    "memo": "손절"},
    {"date": "2026-02-27", "stock_id": "HMB", "name": "현대모비스",        "type": "sell", "qty": 69,  "price": 517000,   "pnl": 18670000,   "memo": "현대차증권"},
    {"date": "2026-02-25", "stock_id": "NVR", "name": "네이버",            "type": "sell", "qty": 5,   "price": 252500,   "pnl": 50000,      "memo": ""},
    {"date": "2026-02-20", "stock_id": "SKH", "name": "SK하이닉스",       "type": "sell", "qty": 15,  "price": 949000,   "pnl": 7780000,    "memo": ""},
    # ── 1월 ──
    {"date": "2026-01-29", "stock_id": "APR", "name": "에이피알",         "type": "sell", "qty": 13,  "price": 270000,   "pnl": 550000,     "memo": ""},
]


def migrate_historical_trades():
    if not HISTORICAL_TRADES:
        return
    # trade_log 테이블에 추가 insert (migrate_portfolio_json 이후 호출)
    client.table("trade_log").insert(HISTORICAL_TRADES).execute()
    print(f"  [trade_log] 구형 데이터 {len(HISTORICAL_TRADES)}건 insert 완료")


# ────────────────────────────────────────────────
# 3. portfolio_history — HISTORY 배열 + portfolio_history.json 통합
#    HISTORY 배열: total 단위 = 만원 → ×10,000 → 원으로 변환
#    portfolio_history.json: total 단위 = 원 (그대로 사용)
# ────────────────────────────────────────────────

# HTML tk_portfolio.html 내 HISTORY[] 배열에서 추출 (2026년 데이터)
HISTORY_FROM_HTML = [
    {"date": "2026-03-05", "total": 7200,  "cash_pct": 28.0,  "pnl": {"SKH": 30,   "HWA": 8,    "TWI": -2,   "ISC": 5,    "APR": 12,   "DSE": -5.4, "MIA": 0.1,  "TIG": 0}},
    {"date": "2026-03-11", "total": 7800,  "cash_pct": 27.0,  "pnl": {"SKH": 44,   "HWA": 12,   "TWI": -3,   "ISC": 10,   "APR": 18,   "DSE": -3.4, "MIA": -2.7, "TIG": 0}},
    {"date": "2026-03-18", "total": 8721,  "cash_pct": 26.0,  "pnl": {"SKH": 58,   "HWA": 14,   "TWI": -6,   "ISC": 30,   "APR": 25,   "DSE": 1.0,  "MIA": -1.3, "TIG": 0}},
    {"date": "2026-03-20", "total": 8630,  "cash_pct": 24.0,  "pnl": {"SKH": 52,   "HWA": 7,    "TWI": -7,   "ISC": 37,   "APR": 26,   "DSE": -0.4, "MIA": -4.8, "TIG": 0}},
    {"date": "2026-03-25", "total": 8688,  "cash_pct": 20.0,  "pnl": {"SKH": 43,   "HWA": 14,   "TWI": -13,  "ISC": 43,   "APR": 14,   "DSE": 2.7,  "MIA": -6.8, "TIG": 0}},
    {"date": "2026-04-03", "total": 9180,  "cash_pct": 29.0,  "pnl": {"SKH": 25,   "HWA": 2,    "TWI": -26,  "ISC": 10,   "APR": 16,   "DSE": -3.4, "MIA": -9.6, "TIG": 0}},
    {"date": "2026-04-06", "total": 9330,  "cash_pct": 31.0,  "pnl": {"SKH": 22,   "HWA": 2,    "TWI": -26,  "ISC": 10,   "APR": 16,   "DSE": -2.9, "MIA": -8.9, "TIG": 0}},
    {"date": "2026-04-24", "total": 9436,  "cash_pct": 24.5,  "pnl": {"SKH": 51.9, "HWA": 19.8, "TWI": -3.2, "ISC": 6.5,  "APR": 31.5, "DSE": 26.1, "MIA": -7.1, "TIG": 0.7}},
    {"date": "2026-04-28", "total": 9708,  "cash_pct": 18.2,  "pnl": {"SKH": 61.9, "HWA": 14.4, "TWI": -4.0, "ISC": 8.8,  "APR": 19.5, "DSE": 27.3, "MIA": -4.7, "TIG": -5.4,  "ABL": 0.3}},
    {"date": "2026-04-30", "total": 9547,  "cash_pct": 19.7,  "pnl": {"SKH": 60.9, "HWA": 14.8, "TWI": -4.4, "ISC": 12.2, "APR": 9.9,  "DSE": 27.5, "MIA": -6.6, "TIG": -8.4,  "ABL": -0.6}},
    {"date": "2026-05-06", "total": 10224, "cash_pct": 36.5,  "pnl": {"SKH": 97.6, "HWA": 17.7, "TWI": -1.1, "ISC": 15.8, "APR": 8.5,  "DSE": 26.9, "MIA": 17.0, "TIG": -10.5, "ABL": -8.2}},
    {"date": "2026-05-07", "total": 10301, "cash_pct": 36.0,  "pnl": {"SKH": 106.0,"HWA": 6.5,  "TWI": -5.4, "ISC": 14.2, "APR": 10.0, "DSE": 26.4, "MIA": 16.5, "TIG": -7.9,  "ABL": -6.8}},
    {"date": "2026-05-08", "total": 10353, "cash_pct": 19.8,  "pnl": {"SKH": 109.9,"HWA": 7.0,  "TWI": -5.5, "ISC": 14.5, "APR": 10.6, "DSE": 29.5, "MIA": 10.4, "TIG": -7.3,  "ABL": -6.2}},
    {"date": "2026-05-12", "total": 10870, "cash_pct": 20.5,  "pnl": {"SKH": 97.3, "HWA": 5.4,  "TWI": -8.9, "ISC": 10.8, "APR": 3.5,  "DSE": 20.2, "MIA": 2.1,  "TIG": -14.2, "ABL": -11.3}},
    {"date": "2026-05-14", "total": 10833, "cash_pct": 12.0,  "pnl": {"SKH": 95.6, "HWA": 6.4,  "TWI": -12.6,"ISC": 12.4, "APR": 8.6,  "DSE": 16.9, "MIA": 0.7,  "TIG": 22.8,  "ABL": -10.1}},
    {"date": "2026-05-15", "total": 9820,  "cash_pct": 2.5,   "pnl": {"SKH": 56.5, "HWA": 0.2,  "TWI": -19.9,"ISC": 3.1,  "APR": 2.8,  "DSE": 10.5, "MIA": -4.1, "TIG": 24.4,  "ABL": -14.9}},
]


def migrate_portfolio_history():
    rows = {}

    # HTML HISTORY (만원 → 원 변환)
    for h in HISTORY_FROM_HTML:
        rows[h["date"]] = {
            "date":      h["date"],
            "total":     h["total"] * 10_000,
            "cash_pct":  h["cash_pct"],
            "pnl":       h["pnl"],
        }

    # data/portfolio_history.json (원 단위, cash_pct/pnl 없음)
    ph_path = BASE_DIR / "data" / "portfolio_history.json"
    if ph_path.exists():
        with open(ph_path, encoding="utf-8") as f:
            ph_data = json.load(f)
        for item in ph_data:
            date_str = item["date"]
            if date_str in rows:
                # 같은 날짜가 있으면 total만 더 정확한 값으로 덮어씀
                rows[date_str]["total"] = item["total"]
            else:
                rows[date_str] = {
                    "date":     date_str,
                    "total":    item["total"],
                    "cash_pct": None,
                    "pnl":      None,
                }

    upsert("portfolio_history", list(rows.values()))


# ────────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────────

def main():
    print("=== TK Portfolio → Supabase 마이그레이션 시작 ===\n")

    print("[1/4] portfolio.json (holdings, cash, realized_gains, trade_log)")
    migrate_portfolio_json()

    print("\n[2/4] 구형 매매 일지 (HTML TRADE_LOG 01/29~04/13)")
    migrate_historical_trades()

    print("\n[3/4] 포트폴리오 히스토리 (HISTORY 배열 + portfolio_history.json)")
    migrate_portfolio_history()

    print("\n=== 마이그레이션 완료 ===")
    print("Supabase Dashboard에서 각 테이블 데이터를 확인하세요.")
    print(f"  → {SUPABASE_URL.rstrip('/')}/project/default/editor")


if __name__ == "__main__":
    main()
