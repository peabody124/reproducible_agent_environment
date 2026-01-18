---
name: deslop
description: Use a subagent to review the code change and remove AI generated slop
---

Check the diff against main, and remove all AI generated slop introduced in the
outstanding code changes, most recent commit, or branch based on the user instructions.

This includes:
- Extra comments that a human wouldn't add or is inconsistent with the rest of the file
- Extra defensive checks or try/catch blocks that are abnormal for that area of the codebase (especially if called by trusted / validated codepaths)
- Casts to `Any` to get around type issues
- Any other style that is inconsistent with the file

Report at the end with only a 1-3 sentence summary of what you changed.
