# Cupertino Taste

Cupertino Taste provides Claude Code design skills distilled from selected WWDC design sessions.

> Distilled by WeZZard in China, Assembled from WWDC.

## Included skill

`design-fluid-interface` designs, reviews, diagnoses, and implements user-driven interaction behavior. It is based on “Designing Fluid Interfaces,” WWDC 2018 session 803, with historical examples qualified by current Apple Human Interface Guidelines.

Use it for taps, presses, drags, swipes, scrolling, transitions, gesture conflicts, momentum, springs, cancellation, boundaries, feedback, and discoverability. A static screenshot receives an affordance review; claims about fluidity require a recording, runnable prototype, or real-device use.

Raw transcripts, videos, slides, screenshots, and downloaded Apple material are not included. The private research corpus lives outside this repository on DAS.

## Current Apple guidance maintenance

`maintain-current-apple-guidance` is a repository-only Codex skill for contributors. It lives under `.agents/skills/`, so plugin installations do not include it. The skill reviews a prepared report of normalized Apple guidance and returns a schema-defined decision. It never activates implicitly, fetches sources, edits files, or chooses a date.

The maintenance routine makes acquisition, source validation, normalization, hashing, comparison, receipt validation, and date updates deterministic. Codex supplies the semantic judgment only for changed normalized content. Its result must follow a JSON Schema and match the exact report and source hashes, but model inference is not bit-for-bit deterministic.

Run one of these four commands from the repository root:

1. Fetch, normalize, compare, and write a private report:

   ```bash
   ./.agents/skills/maintain-current-apple-guidance/scripts/check-current-apple-guidance
   ```

2. Review a changed report through the explicit skill:

   ```bash
   ./.agents/skills/maintain-current-apple-guidance/scripts/review-current-apple-guidance --report /absolute/path/to/report.json
   ```

3. Accept a validated report and advance the baseline and `Last checked` date:

   ```bash
   ./.agents/skills/maintain-current-apple-guidance/scripts/accept-current-apple-guidance --report /absolute/path/to/report.json
   ```

4. Run the composed check, conditional review, and acceptance routine:

   ```bash
   ./.agents/skills/maintain-current-apple-guidance/scripts/run-current-apple-guidance-routine
   ```

The scripts archive responses, normalized snapshots, reports, Codex events, and receipts outside Git. When DAS is mounted, the default private archive is `/Volumes/DAS/3.Resources/Documentations/WWDC/cupertino-taste/current-apple-guidance`. Set `CUPERTINO_TASTE_GUIDANCE_ARCHIVE` to override it. Without DAS, the scripts use the platform cache directory.

The composed command skips Codex when normalized content is unchanged. Byte-level representation changes that normalize to the accepted content also skip Codex. An intentional source-manifest change produces a changed evidence set and requires review.

Expected routine outcomes use stable exit codes:

| Code | Meaning |
| ---: | --- |
| `0` | Sources are current, or review, acceptance, or the composed routine completed successfully. |
| `10` | The check found changed normalized content or a changed source manifest. Review is required. |
| `20` | A source fetch failed. |
| `21` | A fetched source failed its identity or format contract. |
| `22` | An input, manifest, baseline, option, or routine state is invalid. |
| `23` | A report, snapshot, structured review, receipt, or target state failed validation. |
| `24` | Codex is unavailable, failed, timed out, or returned a nonzero status. |

The repository does not schedule this routine through CI or `launchd`. Contributors run it explicitly when they want to verify current guidance.

## Local development

Load the plugin from the repository root:

```bash
claude --plugin-dir /Users/wezzard/Artifacts/Repositories/com.github/WeZZard/cupertino-taste
```

Validate its plugin structure:

```bash
claude plugin validate --strict /Users/wezzard/Artifacts/Repositories/com.github/WeZZard/cupertino-taste
```

The plugin can also be installed from the WeZZard marketplace after its tagged release is registered there.

## Sources

The skill publishes original synthesis and links to the canonical [WWDC 2018 session](https://developer.apple.com/videos/play/wwdc2018/803/) and current Apple design guidance. It does not distribute Apple transcripts or media.

## Independence

Cupertino Taste is an independent project. It has not been authorized, sponsored, or otherwise approved by Apple Inc. Apple and WWDC are trademarks of Apple Inc.

## License

The MIT license applies only to original material in this repository. It does not grant rights to Apple content or third-party source material.
