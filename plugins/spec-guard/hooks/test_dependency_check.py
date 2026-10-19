"""dependency-check: the pure parts of the dependency audit (manifests, names, the Plan section). No network, no git."""
import unittest

from dependency_check import (classify, external_conditions, is_listed, new_names, npm_deps, pyproject_deps,
                              requirement_deps, normalize_python)


class ManifestTest(unittest.TestCase):
    def test_npm_reads_all_four_dependency_kinds(self):
        text = ('{"dependencies": {"zod": "^3"}, "devDependencies": {"vitest": "1"}, '
                '"peerDependencies": {"react": "*"}, "optionalDependencies": {"@scope/x": "1"}, "scripts": {"a": "b"}}')
        self.assertEqual(npm_deps(text), {"zod", "vitest", "react", "@scope/x"})

    def test_npm_unreadable_is_none(self):
        self.assertIsNone(npm_deps("{not json"))
        self.assertIsNone(npm_deps("[]"))

    def test_requirements_take_the_name_only(self):
        text = "# comment\n\nRequests[socks]>=2 ; python_version>'3'\nhttpx==0.27\n-r base.txt\n-e .\nflask\n"
        self.assertEqual(requirement_deps(text), {"requests", "httpx", "flask"})

    def test_pyproject_project_dependencies_and_groups(self):
        text = ('[project]\nname = "x"\ndependencies = [\n  "Requests>=2",\n  "pydantic",\n]\n'
                '[project.optional-dependencies]\ndev = ["pytest>=8", "ruff"]\n')
        deps, understood = pyproject_deps(text)
        self.assertTrue(understood)
        self.assertEqual(deps, {"requests", "pydantic", "pytest", "ruff"})

    def test_pyproject_poetry_tables(self):
        text = ('[tool.poetry.dependencies]\npython = "^3.11"\nHTTPX = "^0.27"\n'
                '[tool.poetry.group.dev.dependencies]\npytest = "*"\n[tool.ruff]\nline-length = 100\n')
        deps, understood = pyproject_deps(text)
        self.assertTrue(understood)
        self.assertEqual(deps, {"httpx", "pytest"})

    def test_pyproject_unknown_shape_is_not_understood(self):
        deps, understood = pyproject_deps('[tool.pdm.dev-dependencies]\ntest = ["pytest"]\n')
        self.assertFalse(understood)
        deps, understood = pyproject_deps('[project]\nname = "x"\n')
        self.assertTrue(understood)
        self.assertEqual(deps, set())

    def test_new_names_ignore_version_changes(self):
        self.assertEqual(new_names({"zod", "dayjs"}, {"zod"}), {"dayjs"})
        self.assertEqual(new_names({"zod"}, {"zod"}), set())


class NameTest(unittest.TestCase):
    def test_pep503(self):
        self.assertEqual(normalize_python("Foo_Bar.baz"), "foo-bar-baz")
        self.assertEqual(normalize_python("foo--bar"), "foo-bar")

    def test_whole_word_match(self):
        section = "需要的外部条件：\n- zod-form（表单）\n- `dayjs`@1，用于日期。\n- @scope/x\n- Requests"
        self.assertFalse(is_listed("zod", section, "npm"))
        self.assertTrue(is_listed("zod-form", section, "npm"))
        self.assertTrue(is_listed("dayjs", section, "npm"))
        self.assertTrue(is_listed("@scope/x", section, "npm"))
        self.assertFalse(is_listed("x", section, "npm"))
        self.assertTrue(is_listed("requests", section, "python"))
        self.assertFalse(is_listed("requests", section, "npm"))  # npm names compare exactly


class SectionTest(unittest.TestCase):
    def test_heading_until_next_heading(self):
        plan = "# Plan\n\n## 需要的外部条件\n\n- zod\n\n### 细节\n\n- dayjs\n\n## Task List\n\n- react\n"
        section = external_conditions(plan)
        self.assertIn("zod", section)
        self.assertIn("dayjs", section)
        self.assertNotIn("react", section)

    def test_line_form_takes_the_following_list(self):
        plan = "需要的外部条件：\n- zod\n  - 说明\n- dayjs\n\n其他段落里的 react\n"
        section = external_conditions(plan)
        self.assertIn("dayjs", section)
        self.assertNotIn("react", section)

    def test_english_heading_and_absent(self):
        self.assertIn("zod", external_conditions("## Required external conditions\n\n- zod\n"))
        self.assertIsNone(external_conditions("## Task List\n\n- zod\n"))
        self.assertIsNone(external_conditions("```\n需要的外部条件：无\n```\n"))


class ClassifyTest(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(classify("apps/web/package.json"), "npm")
        self.assertEqual(classify("requirements-dev.txt"), "requirements")
        self.assertEqual(classify("pyproject.toml"), "pyproject")
        for lock in ("package-lock.json", "a/pnpm-lock.yaml", "yarn.lock", "bun.lockb", "poetry.lock", "uv.lock",
                     "Pipfile.lock"):
            self.assertEqual(classify(lock), "lock", lock)
        for other in ("go.mod", "Cargo.toml", "Gemfile", "composer.json", "Pipfile", "setup.py", "setup.cfg"):
            self.assertEqual(classify(other), "other", other)
        self.assertIsNone(classify("node_modules/zod/package.json"))
        self.assertIsNone(classify("README.md"))


if __name__ == "__main__":
    unittest.main()
