-- ============================================================
-- TK Portfolio — Supabase Schema
-- 실행 방법: Supabase Dashboard > SQL Editor에 붙여넣고 실행
-- ============================================================


-- ────────────────────────────────────────
-- 1. holdings — 현재 보유 종목
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS holdings (
  id             TEXT        PRIMARY KEY,           -- 'SKH', 'HWA' 등 내부 식별자
  account        TEXT        NOT NULL CHECK (account IN ('kiwoom', 'toss')),
  ticker         TEXT        NOT NULL,              -- '000660'
  naver          TEXT,                              -- 네이버 종목코드 (ticker와 같은 경우 많음)
  name           TEXT        NOT NULL,              -- 'SK하이닉스'
  qty            INTEGER     NOT NULL DEFAULT 0,
  avg            BIGINT      NOT NULL DEFAULT 0,    -- 평균단가 (원)
  current_price  BIGINT,                            -- 현재가 (원)
  prev_price     BIGINT,                            -- 전일가 (원)
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────
-- 2. cash — 계좌별 예수금
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cash (
  account    TEXT        PRIMARY KEY CHECK (account IN ('kiwoom', 'toss')),
  amount     BIGINT      NOT NULL DEFAULT 0,        -- 예수금 (원)
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────
-- 3. portfolio_history — 날짜별 포트폴리오 스냅샷
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS portfolio_history (
  date       DATE        PRIMARY KEY,
  total      BIGINT      NOT NULL,                  -- 총평가금액 (원)
  cash_pct   FLOAT,                                 -- 현금 비중 (%)
  pnl        JSONB,                                 -- 종목별 수익률 {"SKH": 30.5, "HWA": 8.2, ...}
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────
-- 4. trade_log — 매매 일지
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trade_log (
  id         SERIAL      PRIMARY KEY,
  date       DATE        NOT NULL,
  stock_id   TEXT        NOT NULL,                  -- 'SKH', 'APR' 등 (미보유 구종목 포함)
  name       TEXT        NOT NULL,
  type       TEXT        NOT NULL CHECK (type IN ('buy', 'sell', 'loss')),
  qty        INTEGER,
  price      BIGINT,                                -- 매매단가 (원)
  pnl        BIGINT,                               -- 실현손익 (원, 매도/손절 시)
  memo       TEXT        DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────
-- 5. realized_gains — 종목별 실현손익
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS realized_gains (
  id   SERIAL PRIMARY KEY,
  name TEXT   NOT NULL,
  pnl  BIGINT NOT NULL,                             -- 실현손익 (원)
  type TEXT   NOT NULL CHECK (type IN ('sell', 'loss'))
);

-- ────────────────────────────────────────
-- 6. realized_gains_monthly — 월별 실현손익 집계
-- ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS realized_gains_monthly (
  month TEXT   PRIMARY KEY,                         -- '1월', '2월', ...
  pnl   BIGINT NOT NULL                             -- 월 실현손익 (원)
);


-- ============================================================
-- updated_at 자동 갱신 트리거
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER holdings_updated_at
  BEFORE UPDATE ON holdings
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER cash_updated_at
  BEFORE UPDATE ON cash
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- RLS (Row Level Security)
-- anon(브라우저 publishable key) → SELECT 전용
-- service_role(Python secret key)  → 제한 없음 (RLS 우회)
-- ============================================================
ALTER TABLE holdings              ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_history     ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_log             ENABLE ROW LEVEL SECURITY;
ALTER TABLE realized_gains        ENABLE ROW LEVEL SECURITY;
ALTER TABLE realized_gains_monthly ENABLE ROW LEVEL SECURITY;

-- anon: SELECT 허용
CREATE POLICY "anon_select_holdings"
  ON holdings FOR SELECT TO anon USING (true);

CREATE POLICY "anon_select_cash"
  ON cash FOR SELECT TO anon USING (true);

CREATE POLICY "anon_select_portfolio_history"
  ON portfolio_history FOR SELECT TO anon USING (true);

-- 브라우저 저장 버튼(오늘 기록 저장)이 upsert 가능하도록 INSERT/UPDATE 허용
CREATE POLICY "anon_upsert_portfolio_history"
  ON portfolio_history FOR ALL TO anon USING (true) WITH CHECK (true);

CREATE POLICY "anon_select_trade_log"
  ON trade_log FOR SELECT TO anon USING (true);

CREATE POLICY "anon_select_realized_gains"
  ON realized_gains FOR SELECT TO anon USING (true);

CREATE POLICY "anon_select_realized_gains_monthly"
  ON realized_gains_monthly FOR SELECT TO anon USING (true);
