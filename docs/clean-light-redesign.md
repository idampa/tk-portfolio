# Clean Light redesign

The original application is preserved on branch `backup/pre-clean-light-2026-10-11`
and tag `backup-pre-clean-light-2026-10-11` (base commit 316345b).
These are source backups, not a Supabase database snapshot. The existing JSON export
contains prices, cash, holdings and history; it is not a complete database export.

The redesign keeps existing Supabase operations and calculation functions. Shared
presentation lives in assets/clean-light.css and assets/clean-light.js. The home
chart uses existing HISTORY records, including the original fallback records when
the server history is unavailable, labeled accordingly. No sample balances were
introduced. Historical research and investment conditions are marked as records.

Responsive modes: below 768px single column and five bottom navigation items;
768–1179px compact sidebar and holdings/detail split; 1180px+ full sidebar,
chart/table main column and signals/schedule secondary column. Layout follows
available viewport width including tablet split screen. Settings remain accessible
from the header on mobile. A saved dark theme is optional on the main dashboard.

Release review: verify the redesign branch before merging into main. The deployed
site is not changed until release. To restore the old UI, revert the redesign
commit; keep database records intact. Do not force-reset main to the backup.

Validation: Chromium at 390×844, 834×1194 and 1440×1000; all six main
sections had no document horizontal overflow and no uncaught JavaScript errors.
Mobile research pages checked as well. Verified buy/sell dialog opening, holdings
expansion and selection, research search empty state, and light/dark switching.
Browser checks blocked non-GET/HEAD network requests: no financial records were
written during validation. Actual device Safari and transaction persistence have
not been tested in this change.
