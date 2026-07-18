# Cupertino Taste

Cupertino Taste will provide Claude Code design skills distilled from selected WWDC design sessions.

> Distilled by WeZZard in China, Assembled from WWDC.

## Status

The repository currently contains the plugin and release scaffold. Its first planned skill is `design-fluid-interface`, based on “Designing Fluid Interfaces,” WWDC 2018 session 803.

Raw transcripts, videos, slides, screenshots, and downloaded Apple material are not included. The private research corpus lives outside this repository on DAS.

## Local development

Load the scaffold from the repository root:

```bash
claude --plugin-dir /Users/wezzard/Artifacts/Repositories/com.github/WeZZard/cupertino-taste
```

Validate its plugin structure:

```bash
claude plugin validate --strict /Users/wezzard/Artifacts/Repositories/com.github/WeZZard/cupertino-taste
```

Marketplace installation will become available after the first skill passes its evaluations and receives a tagged release.

## Independence

Cupertino Taste is an independent project. It has not been authorized, sponsored, or otherwise approved by Apple Inc. Apple and WWDC are trademarks of Apple Inc.

## License

The MIT license applies only to original material in this repository. It does not grant rights to Apple content or third-party source material.
