# Claude Code instructions

Follow `AGENTS.md` as the authoritative repository contract. Work from one task
in `TASKS.md` at a time, preserve the narrow commit-aware testing scope, and run
the validation commands before declaring completion.

Before implementation, inspect the relevant ADR and add a regression test.
Never add hidden network calls, required model credentials, broad orchestration,
or LLM-as-a-judge logic to core. End each session with the handoff format in
`docs/agent/SESSION_CHECKLIST.md`.
