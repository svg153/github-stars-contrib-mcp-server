# GitHub ↔ GSD tracker contract

- GitHub Issues own backlog state, priority, assignment and delivery status.
- `.planning/` owns requirements, dependency order, decisions, detailed tasks and verification contracts.
- Epic #16 owns v0.3.0. Phase issues: 01 #17, 02 #18, 03 #19, 04 #20, 05 #21, 06 #22, 07 #23. Create 08-13 just-in-time by copying the phase goal/requirements/dependencies from `ROADMAP.md`.
- Implementation uses isolated branches/PRs; do not push implementation directly to `main`.
- If a plan grows beyond four meaningful implementation tasks, split it before execution.
- A phase closes only after all tasks are done, focused/full validation is recorded, `SUMMARY.md` and `VERIFICATION.md` exist, requirements/state/roadmap are updated and implementation PRs are merged.
- Credential-based test skips are unavailable evidence, not passing integration evidence.
- Install/update the GSD runtime through its official distribution; never vendor the runtime into this repository.
