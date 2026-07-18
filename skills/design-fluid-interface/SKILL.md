---
name: design-fluid-interface
description: Design, review, diagnose, or implement user-driven interface behavior—taps, presses, drags, swipes, scrolling, paging, transitions, gesture conflicts, momentum, springs, interruption, cancellation, boundaries, feedback, and discoverability—especially for Apple platforms. Use when an interaction feels laggy, stiff, abrupt, disconnected, hard to cancel, or hard to discover. Never invent numeric motion values. Do not use for static visual styling or decorative animation without an interaction problem.
---

# Design Fluid Interfaces

Shape interaction as a continuous exchange between a person and the interface. Optimize for control, continuity, and clear intent; motion is supporting evidence, not the goal.

## Non-negotiable constraints

- Never invent or suggest illustrative numbers for gesture distances, detent positions, commitment fractions, velocities, durations, spring parameters, deceleration rates, frame rates, or haptic thresholds. This prohibition includes approximate and “for example” values. If the project, a current system API, current documentation, or a measured prototype does not supply a value, use a named parameter such as `recognitionThreshold` and mark it **tune in prototype**. A design request with no numeric evidence must contain no numeric literals in behavioral recommendations or sample code.
- Never prescribe a historical API or value until current documentation and the supported OS range confirm it. State the behavior algorithmically when current API evidence is unavailable.
- Never translate Reduce Motion into an instant jump or a shorter duration by default. Reduce the kind and extent of spatial motion while preserving state, hierarchy, feedback, and control.
- Never claim an implementation cause from a reported symptom, screenshot, or recording alone. Label the cause as a hypothesis until code or instrumentation confirms it.

## Establish the task

Follow the user's verb:

- **Review or diagnose:** inspect the available artifact and return prioritized findings. Do not edit unless asked.
- **Design or refine:** produce an implementable interaction specification and prototype plan.
- **Implement or fix:** inspect the existing event and state paths, make the scoped change, and exercise the interaction through its runnable interface when available.

Establish the platform, framework, input methods, user goal, starting state, intermediate states, valid outcomes, cancellation paths, and available evidence. Infer these from the project before asking. If a missing choice would materially change the product behavior, state the missing fact and ask one focused question; otherwise proceed with an explicit assumption.

You must read [fluid-principles.md](references/fluid-principles.md) and [current-apple-guidance.md](references/current-apple-guidance.md) before making recommendations. Current Apple documentation overrides the 2018 examples.

## Calibrate the evidence

Fluidity has to survive use. Classify what the supplied artifact can prove:

| Evidence | What it can establish |
| --- | --- |
| Static image | Affordances, hierarchy, possible states, spatial cues |
| State sequence or written spec | Intended paths, endpoints, and omissions |
| Source code | Recognizers, timers, state transitions, parameters, accessibility branches |
| Screen recording | Visible continuity, pacing, and apparent feedback |
| Runnable prototype | Tracking, latency, interruption, reversal, cancellation, and endpoint behavior |
| Real device with a person | Perceived response, ergonomics, haptics, and actual input behavior |

Give the useful partial result the evidence supports. Do not withhold a behavioral correction merely because the root cause is unknown; specify the desired behavior and put cause-finding under **Runtime checks**. Distinguish a user-reported symptom from behavior you observed directly. Never turn either one into an implementation cause without source or runtime evidence; label a possible cause as a hypothesis and state how to confirm it. Never infer tracking quality, latency, interruptibility, gesture arbitration, haptics, or perceived smoothness from a screenshot. Put those claims under **Runtime checks** instead of issuing a complete verdict.

## Map the interaction before judging it

For each important action, trace this lifecycle:

1. **Cue:** How does a person know the action exists?
2. **Contact:** What acknowledges the initial input?
3. **Recognition:** What evidence separates this intent from competing intents?
4. **Tracking:** What changes continuously while input changes?
5. **Commitment:** When does the action become consequential?
6. **Release:** How do position, velocity, and input history affect the outcome?
7. **Settlement:** Where does the interface come to rest, and how does it communicate that state?
8. **Escape:** How can the person cancel, reverse, redirect, or interrupt at every stage?

Represent a nontrivial interaction as a compact state/transition table. Do not reduce it to a list of animation durations.

## Apply the fluidity lenses

Evaluate or design every traced path through these lenses:

### Response

- Acknowledge input at the earliest safe moment; completion may take longer.
- Search for avoidable waits in recognizer dependencies, timers, asynchronous work, and serialized animations.
- Keep feedback distinct from commitment: a control can react on contact while its action commits on release.

### Agency

- Permit cancellation before commitment and recovery after a changed mind.
- Let new input interrupt or retarget ongoing motion without a snap, reset, or dead interval.
- When several gestures are plausible, provide provisional feedback and resolve intent as evidence arrives. Do not enable simultaneous recognition by default; use it only when the platform and interaction benefit.

### Continuity

- Give every object a stable spatial model. Entry and exit paths should explain where it came from and where it went.
- Preserve the object's current presentation and velocity when control changes hands.
- Use soft boundary feedback and smooth handoffs so an edge cannot be mistaken for a frozen interface.
- Inspect the visual distance between frames as well as nominal frame rate.

### Intent

- During direct manipulation, preserve the contact offset and keep content coupled to input unless resistance communicates a boundary.
- Use the input history that matters — direction, velocity, acceleration, scale, rotation, or pressure where genuinely supported — instead of the final coordinate alone.
- For a throw toward several endpoints, project likely travel with a platform-familiar deceleration model, then choose a valid destination. Keep the result predictable and easy to reverse.
- Favor small, comfortable effort while keeping the resulting action proportional and understandable.

### Feedback and teaching

- Make feedback continuous, proportional, and predictive of the outcome.
- Teach in this order: familiar convention, visible affordance, behavior that demonstrates the same spatial rule, then a brief explanation for an action people repeat.
- Give important gesture-only actions an accessible visible alternative.
- Coordinate visuals, sound, and haptics as one behavior family when those channels exist; never make one sensory channel carry essential meaning alone. Add haptics only when supported, useful, and restrained — not as an automatic marker for every threshold or handoff.

### Character

- Choose behavior before decoration. Direct manipulation should remain influenceable while it moves.
- Start with restrained, non-overshooting motion. Add bounce only when momentum, boundary feedback, or teaching gives it a job.
- Keep motion qualities coherent across the product so learning transfers between interactions.
- Prefer system components and familiar platform behavior unless a custom interaction provides clear value.

### Comfort and reach

- Respect the system Reduce Motion preference and preserve meaning with a lower-motion alternative.
- Support the platform's relevant inputs, including keyboard, pointer, focus, assistive technologies, and indirect spatial input where applicable.
- Check target size, spacing, gesture complexity, and alternatives; this skill does not replace a complete accessibility review.

## Handle common interaction types

### Tap or press

Check immediate contact feedback, commitment on release, a forgiving activation region, move-out cancellation, move-back-in recovery, adequate target size, and keyboard or assistive activation where applicable.

### Drag, swipe, or scroll

Check a platform-appropriate recognition threshold, direction locking only when needed, preserved contact offset, continuous tracking, boundary response, release velocity, destination logic, and interruption during settling. Prefer system recognizers and scrolling behavior over hard-coded historical constants.

### Transition or spring

Check spatial origin and destination, mid-flight interruption, retargeting from the current state, response and damping as conceptual controls, purposeful overshoot, stable final state, and a Reduce Motion variant. Avoid inventing duration or spring values without running the interaction.

### Competing gestures

Map dependencies and failure requirements. Identify which common action pays each delay. Begin feedback as early as safely possible, resolve ambiguity from real movement, and cancel losing paths cleanly. Reject gesture combinations that make the primary action feel unresponsive without delivering commensurate value.

## Keep numeric guidance grounded

Do not invent recognition distances, detent positions, commitment fractions, durations, spring parameters, deceleration rates, frame-rate targets, or haptic thresholds. Use the project's existing values, a current system component, current platform documentation, or measurements from a runnable prototype. When none exists, name the value symbolically and describe how the team should tune and verify it.

Do not make “Reduce Motion” mean an instant jump or merely a faster animation by default. Faster large-scale motion can remain uncomfortable. Preserve essential state and hierarchy with a lower-motion transition such as a tightly damped gesture-coupled settle, dissolve, highlight, or other current platform treatment. Choose the alternative from the interaction's meaning and exercise it with the system preference enabled.

## Produce the requested result

### Review or diagnosis

Lead with the highest-impact behavioral issue. For each finding include:

- **Evidence:** what is observable in the artifact
- **Consequence:** how it affects control, comprehension, or comfort
- **Principle:** the relevant fluidity lens
- **Change:** a concrete behavioral correction
- **Verification:** the exact interaction to exercise afterward

Name whether the evidence was supplied, observed, or inferred. Separate confirmed findings, hypotheses, and **Runtime checks**. Include timestamped session links when they materially explain the recommendation, and current Apple links for present-day platform rules.

### Interaction design

Deliver:

1. Context and assumptions
2. State/transition table
3. Input recognition and conflict rules
4. Continuous feedback and spatial behavior
5. Cancellation, reversal, interruption, and boundary paths
6. Endpoint and motion-character rules
7. Discoverability and non-gesture alternatives
8. Reduce Motion and other input variants
9. Prototype scenarios with observable acceptance criteria

Prefer a small runnable prototype over extra static mockups when behavior is the unresolved question.

If the request supplies no implementation artifact or measured prototype, keep all motion and recognition parameters symbolic. Do not include numeric ranges, sample assignments, deployment targets, or API calls that were not verified against current documentation during this task.

### Implementation

- Follow the existing framework and architecture; use native behaviors first.
- Preserve interaction state and velocity through handoffs and retargeting.
- Keep historical values and APIs out of production guidance until current documentation and the supported OS range confirm them.
- Add focused state, endpoint, cancellation, and accessibility tests where the codebase supports them.
- Exercise contact, partial progress, release, cancel, reverse, mid-flight interruption, boundary, fast and slow input, and Reduce Motion through the real interface when possible.
- Report what was exercised and what still requires a real device or a person.

## Boundaries

This skill is not a complete typography, color, branding, visual-design, usability-research, accessibility, or performance-profiling method. Cover those areas only where they affect the interaction in scope, and name the remaining review explicitly.

Do not copy historical product behavior blindly. The 2018 session's 3D Touch examples, fixed swipe threshold, damping percentages, and API spellings are evidence of principles, not universal current prescriptions.

## Check the response before sending

- Remove every interaction number that did not come from the user's artifact, existing code, a current system component, current documentation checked during this task, or a measured prototype. Replace it with a named parameter and **tune in prototype**.
- For a design request without numeric evidence, scan prose and code for numeric literals and remove them from behavioral recommendations.
- Remove every API recommendation that current documentation checked during this task does not support. Describe the required behavior instead.
- Remove invented deployment targets, device assumptions, detent locations, and haptic behavior.
- Reject a Reduce Motion variant that merely jumps instantly, shortens the same large movement, or adds a made-up reduction percentage. Preserve meaning with less spatial motion.
- Make reported symptoms, observed evidence, hypotheses, and confirmed causes visibly distinct.
