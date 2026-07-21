"""Verify the release workflow triggers after a version-bump PR merges."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RELEASE_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"


class ReleaseWorkflowTests(unittest.TestCase):
    def test_main_push_triggers_the_pinned_release_workflow(self) -> None:
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
        trigger_block = workflow.split("\non:\n", maxsplit=1)[1].split("\nconcurrency:\n", maxsplit=1)[0]

        self.assertRegex(trigger_block, r"(?m)^  push:\n    branches: \[main\]$")
        self.assertIn("  workflow_dispatch:\n", trigger_block)
        self.assertEqual(
            1,
            len(
                re.findall(
                    r"(?m)^    uses: WeZZard/workflows/\.github/workflows/release-plugin\.yml@v1\.0\.0$",
                    workflow,
                )
            ),
        )


if __name__ == "__main__":
    unittest.main()
