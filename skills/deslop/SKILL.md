---
name: deslop
description: >
  Clean up AI-generated slop from code changes. Use when the user says "deslop",
  "clean up code", "remove slop", "review for AI artifacts", "check for anti-patterns
  in diff", or before committing to ensure code quality. Also activates when reviewing
  staged changes or preparing a commit.
---

Review the diff against main and remove all AI-generated slop introduced in the
outstanding code changes, most recent commit, or branch based on user instructions.

Refer to the anti-patterns guide in `enforce-guidelines/references/anti-patterns.md`
for the full list of slop patterns to catch.

Common slop to remove:
- Extra comments that a human wouldn't add or that are inconsistent with the rest of the file
- Extra defensive checks or try/catch blocks that are abnormal for that area of the codebase (especially if called by trusted / validated codepaths)
- Casts to `Any` to get around type issues
- Placeholder patterns (TODOs without context, "Phase 1" comments, commented-out code)
- Over-engineering (abstractions for single-use code, unnecessary factories)
- Any other style that is inconsistent with the file

Report at the end with only a 1-3 sentence summary of what you changed.

## Going further: prevent over-engineering at write-time

deslop is a corrective pass — it scrubs slop out of changes already made. To stop
over-engineering before it is written, the third-party **ponytail** skills
(`https://github.com/DietrichGebert/ponytail`, MIT) are complementary:

- `ponytail` — a write-time mode that enforces minimal/YAGNI code (stdlib and
  native features before custom code, no unrequested abstractions).
- `ponytail-review` / `ponytail-audit` — report-only over-engineering passes on a
  diff or the whole repo. Narrower than deslop (complexity/LOC only, no type-evasion
  or DB-mutation checks) and they list findings rather than applying them.

To adopt: either copy the pertinent `skills/<name>/SKILL.md` folders from that repo
into your skills directory (no hooks needed — the skills work standalone), or
install the full plugin from the repo for the activation hooks and `/ponytail`
mode switching as well.

