# Cupertino Taste Repository Instructions

This repository distributes original design guidance and never stores raw Apple or WWDC material.

## Content boundaries

- Store raw WWDC metadata and transcripts under `/Volumes/DAS/3.Resources/Documentations/WWDC/cupertino-taste`.
- Do not commit transcripts, video, audio, slides, screenshots, downloaded session pages, or close transcript rewrites.
- Publish original synthesis, session metadata, and timestamped canonical source links.
- Treat current Apple Human Interface Guidelines as authoritative when historical guidance conflicts with present platform behavior.

## Plugin structure

- Put installable Claude Code skills at `skills/<skill-name>/SKILL.md`.
- Put repository-only Codex skills at `.agents/skills/<skill-name>/SKILL.md` as real directories, not symlinks into `skills/`.
- Keep supporting references, examples, and scripts inside the owning skill directory unless several skills share them.
- Reserve `design-fluid-interface` for guidance distilled from “Designing Fluid Interfaces,” WWDC 2018 session 803.
- Keep `maintain-current-apple-guidance` repository-only. It must never appear under the plugin's `skills/` directory.
- Store Claude Code project MCP configuration in `.mcp.json` if the project adds an MCP server later.

## Verification

- Run `claude plugin validate --strict .` before committing a plugin change.
- Test each skill through Claude Code with prompts that should invoke it and near-miss prompts that should not.
- Keep the worktree free of downloaded source material and generated evaluation results.
