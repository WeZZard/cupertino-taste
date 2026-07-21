"""Verify the boundary between published and repository-only skills."""

from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_SKILLS = {"design-fluid-interface"}
MAINTENANCE_SKILL = "maintain-current-apple-guidance"


class SkillScopeTests(unittest.TestCase):
    def test_plugin_publishes_only_the_intended_skills(self) -> None:
        published = {
            skill_file.parent.name
            for skill_file in (REPOSITORY_ROOT / "skills").glob("*/SKILL.md")
        }

        self.assertEqual(PUBLISHED_SKILLS, published)

    def test_maintenance_skill_is_a_repository_only_real_directory(self) -> None:
        maintenance_root = REPOSITORY_ROOT / ".agents" / "skills" / MAINTENANCE_SKILL

        self.assertTrue(maintenance_root.is_dir())
        self.assertFalse(maintenance_root.is_symlink())
        self.assertTrue((maintenance_root / "SKILL.md").is_file())
        self.assertFalse((REPOSITORY_ROOT / "skills" / MAINTENANCE_SKILL).exists())


if __name__ == "__main__":
    unittest.main()
