# Skills

## `design-fluid-interface`

Designs, reviews, diagnoses, and implements user-driven interaction behavior using principles distilled from “Designing Fluid Interfaces,” WWDC 2018 session 803, qualified by current Apple guidance.

It covers response, interruption, direct manipulation, momentum, spatial continuity, gesture conflicts, springs, boundaries, feedback, discoverability, and behavioral prototyping. It does not replace a complete visual-design, accessibility, usability-research, or performance review.

## `maintain-current-apple-guidance`

Reviews a prepared set of normalized Apple guidance snapshots for contributors. The skill requires explicit invocation and returns a schema-defined, hash-bound decision. It does not activate for design work, fetch sources, edit files, or choose a check date.

The surrounding scripts keep acquisition, source validation, normalization, SHA-256 comparison, report and receipt validation, and date updates deterministic. Codex runs only when normalized content changes. Its semantic judgment is constrained by a JSON Schema and bound to the exact report and source hashes, but model inference is not bit-for-bit deterministic.

Run the four contributor commands from the repository root:

```bash
./skills/maintain-current-apple-guidance/scripts/check-current-apple-guidance
./skills/maintain-current-apple-guidance/scripts/review-current-apple-guidance --report /absolute/path/to/report.json
./skills/maintain-current-apple-guidance/scripts/accept-current-apple-guidance --report /absolute/path/to/report.json
./skills/maintain-current-apple-guidance/scripts/run-current-apple-guidance-routine
```

When DAS is mounted, every run defaults to the private archive at `/Volumes/DAS/3.Resources/Documentations/WWDC/cupertino-taste/current-apple-guidance`. Set `CUPERTINO_TASTE_GUIDANCE_ARCHIVE` to use another private location. The scripts use the platform cache directory when DAS is unavailable. No raw or normalized Apple source material belongs in Git.

The composed routine skips Codex for unchanged normalized content, including byte-level changes removed by normalization. A source-manifest change also requires review because it changes the evidence set. The repository installs no CI or `launchd` schedule for this contributor routine.

Expected outcomes use these stable exit codes:

| Code | Meaning |
| ---: | --- |
| `0` | Current or completed successfully. |
| `10` | Changed normalized content or source manifest; review is required. |
| `20` | Source fetch failed. |
| `21` | Source identity or format validation failed. |
| `22` | Input or routine state is invalid. |
| `23` | Report, review, receipt, snapshot, or target validation failed. |
| `24` | Codex invocation failed. |
