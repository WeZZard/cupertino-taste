# Fluid interface principles

This reference is an original working synthesis of [“Designing Fluid Interfaces,” WWDC 2018 session 803](https://developer.apple.com/videos/play/wwdc2018/803/). It separates reusable design reasoning from the products and APIs that demonstrated it in 2018.

## The working model

A fluid interface does not merely animate smoothly. It keeps the person, the input, and the represented object in one understandable causal chain. At any moment, the interface should make four things legible:

- what it heard,
- what it thinks the person intends,
- what can still change,
- and where the object can settle.

Use these principles as a connected system. Fast feedback without cancellation can feel trapping; spring motion without spatial consistency can feel decorative; momentum without predictable endpoints can feel uncontrolled.

## Diagnostic map

| Principle | Healthy behavior | Common failure signal | Session anchor |
| --- | --- | --- | --- |
| Immediate acknowledgment | Input changes visible state before expensive work completes | Dead tap, delayed highlight, timer-shaped pause | [Response, 05:33](https://developer.apple.com/videos/play/wwdc2018/803/?time=333) |
| Redirection | New input can alter a developing action | Must wait, finish, undo, then try again | [Interruption, 06:59](https://developer.apple.com/videos/play/wwdc2018/803/?time=419) |
| Motion-based recognition | Intent resolves from meaningful movement | Arbitrary timeout or late recognition | [Acceleration cue, 10:41](https://developer.apple.com/videos/play/wwdc2018/803/?time=641) |
| Spatial consistency | Objects travel through a stable conceptual space | Entry and exit imply different origins | [Spatial paths, 11:55](https://developer.apple.com/videos/play/wwdc2018/803/?time=715) |
| Predictive intermediate state | Partial progress previews the outcome | Gesture feels disconnected until release | [Directional hint, 13:33](https://developer.apple.com/videos/play/wwdc2018/803/?time=813) |
| Efficient effort | Small input can carry useful direction and energy | Repeated long swipes or excessive dragging | [Input amplification, 14:33](https://developer.apple.com/videos/play/wwdc2018/803/?time=873) |
| Soft boundaries | Resistance or deformation explains an edge | Hard stop resembles a freeze | [Rubber-banding, 17:01](https://developer.apple.com/videos/play/wwdc2018/803/?time=1021) |
| Smooth handoff | Tracking transfers without a discontinuity | One object stops before another starts | [Tracking handoff, 17:42](https://developer.apple.com/videos/play/wwdc2018/803/?time=1062) |
| Perceptual continuity | Adjacent frames preserve readable motion | Strobing despite an acceptable reported frame rate | [Frame content, 18:10](https://developer.apple.com/videos/play/wwdc2018/803/?time=1090) |
| Influenceable behavior | Motion can retarget while already running | Fixed animation owns the interface until completion | [Behavior, 20:53](https://developer.apple.com/videos/play/wwdc2018/803/?time=1253) |
| Believable dynamics | Movement borrows familiar expectations | Arbitrary easing or literal physics that fights the task | [Physical reference, 27:18](https://developer.apple.com/videos/play/wwdc2018/803/?time=1638) |
| Purposeful elasticity | Return and overshoot express state or input energy | Bounce added everywhere as style | [Spring character, 35:47](https://developer.apple.com/videos/play/wwdc2018/803/?time=2147) |
| Momentum-aware endpoints | Destination reflects position and motion history | A light flick snaps back to the nearest current point | [Projection, 43:52](https://developer.apple.com/videos/play/wwdc2018/803/?time=2632) |
| Forgiving commitment | Feedback begins early; consequence waits until intent is clear | Action commits on contact or cannot be canceled | [Tap lifecycle, 50:24](https://developer.apple.com/videos/play/wwdc2018/803/?time=3024) |
| Coupled manipulation | Directly handled content preserves contact offset | Object jumps to its center or trails the finger | [Drag lifecycle, 51:46](https://developer.apple.com/videos/play/wwdc2018/803/?time=3106) |
| Continuous feedback | Every meaningful change in input has a legible response | UI responds only after recognizer completion | [Gesture feedback, 53:47](https://developer.apple.com/videos/play/wwdc2018/803/?time=3227) |
| Discoverability | Cues and behavior reveal what can be manipulated | Important action exists only as a hidden gesture | [Teaching gestures, 57:48](https://developer.apple.com/videos/play/wwdc2018/803/?time=3468) |
| Behavioral prototyping | The design can be played, interrupted, and observed | Static screens stand in for unresolved behavior | [Interactive demos, 1:02:17](https://developer.apple.com/videos/play/wwdc2018/803/?time=3737) |

## Interaction mechanics

### Separate acknowledgment from commitment

An interface can show that it received input before deciding that the action should happen. A button may enter a pressed state on contact, leave that state when the pointer or finger exits, recover when it returns, and invoke its action only on a valid release. This pattern makes speed compatible with forgiveness.

### Recognize intent from evidence, not waiting alone

For ambiguous input, list the candidate intents and the signal that distinguishes them. Direction, distance, velocity change, acceleration, contact count, and platform focus state can be stronger evidence than a timer. Some delay is unavoidable — a single tap that must wait for a possible double tap is the session's example — so make the tradeoff explicit and protect the more frequent action.

### Preserve the causal chain during direct manipulation

When a person grabs an object away from its center, preserve that offset. Track continuously after recognition, retain enough motion history to infer release velocity, and make any resistance communicate a real boundary. If control passes from a gesture to settling behavior, begin from the currently presented position and velocity.

### Project before choosing an endpoint

Nearest-position logic discards the energy and direction of a throw. For a direct gesture with discrete endpoints:

1. Take the release value and velocity.
2. Estimate the natural stopping value under a familiar platform deceleration.
3. Filter to destinations that are valid in the current context.
4. Choose the destination that best matches the projected value and direction.
5. Retarget the behavior without resetting current motion.

Projection is a tool for direct motion, not a rule for keyboard, remote, focus, or assistive input.

### Tune behavior by meaning

Response describes how urgently an object moves toward its target. Damping describes how directly it settles. Begin restrained. Add overshoot only when the input brings momentum, the object is returning from a boundary, or the response teaches something useful. Apparent mass can differ by object, but related behaviors should still feel like members of the same family.

## Teaching order

Use the least instructional mechanism that works:

1. A familiar platform convention
2. A visible cue such as clipped continuation, a page indicator, a handle, or an elevated manipulable surface
3. A discrete action whose movement demonstrates the matching gesture path
4. A concise explanation for an action used often enough to remember

Never rely on a hidden gesture as the sole route to important functionality.

## Prototype scenarios

The minimum useful interaction prototype should let a tester:

- begin slowly and quickly,
- stop before recognition,
- cancel before commitment,
- reverse after partial progress,
- redirect toward another valid outcome,
- interrupt while the object is settling,
- cross and retreat from a boundary,
- repeat the action with a different input method,
- and run the lower-motion variant.

Observe the behavior rather than asking whether it “feels fluid.” Record where the interface failed to acknowledge input, changed spatial rules, discarded motion, blocked new input, or hid the available action.

## Historical implementation notes

Treat the following as 2018 examples, not defaults:

- pressure-sensitive 3D Touch demonstrations,
- a fixed swipe-recognition distance,
- specific damping percentages,
- and a period-specific scroll-deceleration API.

Use current platform APIs and defaults. Keep the principle only when it survives current guidance and the actual interaction.
