# Accidental maintenance-skill publication is a patch

## Applies when

Cupertino Taste accidentally publishes contributor-only maintenance tooling as an installable plugin skill. Repository evidence may include the skill appearing under plugin-root `skills/`, generated marketplace or website content reflecting that placement, and documentation written around the mistaken package layout.

The correction moves `maintain-current-apple-guidance` into `.agents/skills/` while preserving the intended installable skill and its behavior.

## Expected classification

Classify this correction as `patch`.

The change fixes plugin packaging and restores the intended public contract. Do not classify the removal of this mistakenly packaged contributor tool as the removal of a supported user capability.

## Does not apply when

Classify the change as `major` when Cupertino Taste intentionally supported an installable skill for plugin users and then removes, renames, or incompatibly changes that skill.
