# JXP Companion Map Agent Entry Point

Before editing this companion mod:

1. Read `../japan_expanded_v2/dev_logs/JXP_SHARED_DEVELOPMENT_LEDGER.md` as the canonical shared project state and TODO source.
2. Read `dev_logs/BASELINE_LOCK.txt` and `tools/jxp_map_validation/main_compatibility_contract.json` before touching map, history, tags, missions, or cross-mod interfaces.
3. Read `../skills/eu4-modding/SKILL.md` from a repository checkout, or fall back to
   `C:/Users/Fiber Memory/.codex/skills/eu4-modding/SKILL.md` in the original local environment.
4. Do not launch EU4 or its launcher without explicit user permission.
5. Preserve the new-campaign requirement, pinned vanilla baseline, province IDs, semantic geography flags, and parent/companion ownership split.
6. The lead agent, not parallel subagents, updates the shared ledger. Before handoff, run `tools/validate_all.ps1` without `-SkipMainModValidation` and record the evidence there.

Do not maintain a separate current TODO in this mod. Map reports remain historical evidence; current truth belongs only in the shared ledger.
