# Cupertino Taste

Cupertino Taste provides Claude Code design skills distilled from selected WWDC design sessions.

> Distilled by WeZZard in China, Assembled from WWDC.

## Included skill

`design-fluid-interface` designs, reviews, diagnoses, and implements user-driven interaction behavior. It is based on “Designing Fluid Interfaces,” WWDC 2018 session 803, with historical examples qualified by current Apple Human Interface Guidelines.

Use it for taps, presses, drags, swipes, scrolling, transitions, gesture conflicts, momentum, springs, cancellation, boundaries, feedback, and discoverability. A static screenshot receives an affordance review; claims about fluidity require a recording, runnable prototype, or real-device use.

Raw transcripts, videos, slides, screenshots, and downloaded Apple material are not included. The private research corpus lives outside this repository on DAS.

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
