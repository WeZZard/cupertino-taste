# Current Apple guidance

Last checked: 2026-07-18.

Use this reference to qualify the 2018 session. Recheck current Apple documentation before prescribing APIs, platform behavior, or numeric values because these sources change.

## What remains current

- Acknowledge gestures promptly and provide feedback that helps people predict the result.
- Let people cancel motion and avoid making them wait for an animation to finish.
- Preserve context with consistent placement and natural transitions.
- Make custom gestures necessary, discoverable, and straightforward.
- Prefer established system interactions and components when they solve the problem.
- Make motion purposeful, brief, and subordinate to the task.
- Prototype early and test actual use, not only static appearance.

Primary sources:

- [Human Interface Guidelines: Motion](https://developer.apple.com/design/human-interface-guidelines/motion)
- [Human Interface Guidelines: Gestures](https://developer.apple.com/design/human-interface-guidelines/gestures)
- [Human Interface Guidelines: Feedback](https://developer.apple.com/design/human-interface-guidelines/feedback)
- [Human Interface Guidelines: Design principles](https://developer.apple.com/design/human-interface-guidelines/design-principles)

## Modern qualifications

### “Instant” means immediate acknowledgment

Network, storage, computation, and gesture ambiguity can delay completion. Respond as promptly as possible, show that the input was received, and expose progress or provisional state when useful. Do not promise that every operation finishes instantly.

### One-to-one tracking belongs to direct manipulation

Finger-to-content coupling is appropriate for a direct drag. It does not describe keyboard navigation, pointer input, tvOS focus, VoiceOver, Switch Control, or indirect visionOS gestures. Preserve a clear causal relationship using the conventions of each input.

### Simultaneous gesture recognition is conditional

Do not start from the 2018 session's parallel-recognition recommendation as a universal rule. Current gesture guidance treats simultaneous recognition as a specialized choice. Use recognizer dependencies and platform defaults unless overlapping recognition produces a demonstrably better interaction.

### Amplification and bounce need a job

Large output from small input can reduce effort, but frequent interactions should not demand attention through extra motion. Use overshoot only to preserve directional energy, communicate a boundary, or teach an interaction. Keep feedback precise and restrained.

### Historical constants are not platform rules

Do not prescribe the session's swipe threshold, damping percentages, 3D Touch pressure behavior, frame-rate examples, or old API names without confirming the current framework and supported OS versions.

## Accessibility gate

Apply this gate to every design, review, and implementation:

- Motion must not be the only carrier of essential information.
- Important gesture actions need another operable route.
- Frequent actions should use simple gestures.
- Support relevant keyboard, pointer, focus, voice, switch, and assistive input.
- Use comfortably sized and spaced controls. Consult the current HIG for platform-specific measurements rather than copying them into code blindly.
- Test the system Reduce Motion setting through the real interaction.

Sources:

- [Human Interface Guidelines: Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)
- [Reduced Motion evaluation criteria](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/reduced-motion-evaluation-criteria)

## Reduce Motion behavior

Do not simply delete all meaningful transition feedback. Preserve state and hierarchy with a lower-motion treatment. Depending on context, that may mean tighter springs, gesture-coupled movement, a dissolve, a highlight fade, or a color change.

Review each use of:

- zooming and scaling,
- spinning and multi-axis movement,
- parallax, blur, depth-of-field, and other depth simulation,
- peripheral or full-screen movement,
- ongoing or auto-advancing decorative motion,
- repeated oscillation or pronounced bounce.

Use the platform preference exposed by the current framework:

- [SwiftUI `accessibilityReduceMotion`](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion)
- [UIKit `isReduceMotionEnabled`](https://developer.apple.com/documentation/uikit/uiaccessibility/isreducemotionenabled)
- [AppKit `accessibilityDisplayShouldReduceMotion`](https://developer.apple.com/documentation/appkit/nsworkspace/accessibilitydisplayshouldreducemotion)

Confirm availability and observation behavior in the current SDK before implementation.

## Platform cautions

- **macOS:** preserve keyboard and pointer conventions; direct-touch rules do not transfer literally.
- **tvOS:** focus and remote input make selection feedback more important than contact tracking.
- **visionOS:** distinguish indirect and direct gestures. Minimize unnecessary peripheral motion, large opaque moving objects, rotating worlds, head-anchored content, and sustained oscillation. Keep a stationary frame of reference when possible.
- **watchOS:** respect compact targets, device haptics, and framework-controlled animation behavior.
- **Cross-platform products:** share the behavioral intent, not necessarily the recognizer or motion implementation.

Current platform behavior and accessibility guidance take priority over the historical session whenever they differ.
