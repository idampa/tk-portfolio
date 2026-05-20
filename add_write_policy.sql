-- ============================================================
-- 오늘 기록 저장 버튼이 작동하려면 이 SQL을 Supabase에서 실행하세요.
-- Supabase Dashboard > SQL Editor에 붙여넣고 실행
-- ============================================================

-- portfolio_history: 브라우저에서 오늘 기록 upsert 허용
CREATE POLICY "anon_upsert_portfolio_history"
  ON portfolio_history FOR ALL TO anon USING (true) WITH CHECK (true);
