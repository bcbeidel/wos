"""Tests for wos/skill_audit.py — skill size auditing."""

from __future__ import annotations

from pathlib import Path


class TestStripFrontmatter:
    def test_removes_yaml_frontmatter(self) -> None:
        from wos.skill_audit import strip_frontmatter

        text = "---\nname: Test\ndescription: A test\n---\n# Content\n"
        result = strip_frontmatter(text)
        assert result.startswith("# Content")

    def test_no_frontmatter_unchanged(self) -> None:
        from wos.skill_audit import strip_frontmatter

        text = "# Content\n\nSome text.\n"
        assert strip_frontmatter(text) == text

    def test_unclosed_frontmatter_unchanged(self) -> None:
        from wos.skill_audit import strip_frontmatter

        text = "---\nname: Test\n# Content\n"
        assert strip_frontmatter(text) == text


class TestCountInstructionLines:
    def test_counts_bullet_points(self) -> None:
        from wos.skill_audit import count_instruction_lines

        text = "- bullet one\n- bullet two\n- bullet three\n"
        assert count_instruction_lines(text) == 3

    def test_excludes_blank_lines(self) -> None:
        from wos.skill_audit import count_instruction_lines

        text = "- bullet one\n\n- bullet two\n"
        assert count_instruction_lines(text) == 2

    def test_excludes_headers(self) -> None:
        from wos.skill_audit import count_instruction_lines

        text = "# Header\n## Subheader\n- bullet\n"
        assert count_instruction_lines(text) == 1

    def test_excludes_code_fences(self) -> None:
        from wos.skill_audit import count_instruction_lines

        text = "```python\nprint('hello')\n```\n"
        assert count_instruction_lines(text) == 1

    def test_excludes_table_separators(self) -> None:
        from wos.skill_audit import count_instruction_lines

        text = "| Name | Value |\n|------|-------|\n| foo  | bar   |\n"
        assert count_instruction_lines(text) == 2

    def test_excludes_horizontal_rules(self) -> None:
        from wos.skill_audit import count_instruction_lines

        text = "- bullet one\n---\n- bullet two\n***\n- bullet three\n"
        assert count_instruction_lines(text) == 3

    def test_counts_prose(self) -> None:
        from wos.skill_audit import count_instruction_lines

        text = "This is a sentence.\nThis is another sentence.\n"
        assert count_instruction_lines(text) == 2

    def test_counts_numbered_steps(self) -> None:
        from wos.skill_audit import count_instruction_lines

        text = "1. Step one\n2. Step two\n3. Step three\n"
        assert count_instruction_lines(text) == 3

    def test_counts_table_data_rows(self) -> None:
        from wos.skill_audit import count_instruction_lines

        text = "| Name | Value |\n|------|-------|\n| foo  | bar   |\n| baz  | qux   |\n"
        assert count_instruction_lines(text) == 3

    def test_empty_text(self) -> None:
        from wos.skill_audit import count_instruction_lines

        assert count_instruction_lines("") == 0
