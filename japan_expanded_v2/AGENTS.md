# JXP Agent Entry Point

Before editing this mod:

1. Read `dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md` as the canonical project state and TODO source.
2. Read `../skills/eu4-modding/SKILL.md` from a repository checkout, or fall back to
   `C:/Users/Fiber Memory/.codex/skills/eu4-modding/SKILL.md` in the original local environment,
   plus the relevant phase reports.
3. Treat `../japan_expanded_v2_map` as a mandatory compatibility target for every gameplay change.
4. Do not launch EU4 or its launcher without explicit user permission.
5. Claim an existing ledger TODO before substantial work. The lead agent, not parallel subagents, updates the ledger.
6. Before handoff, run both the main validator and the companion `tools/validate_all.ps1`, then update the ledger evidence and journal in the same slice.

Do not create a second current-status or TODO document. Historical phase reports are append-only evidence; current truth belongs only in the shared ledger.
