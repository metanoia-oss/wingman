"""Tests for the YAML writer utility."""

import tempfile
from pathlib import Path

import yaml

from wingman.config.yaml_writer import (
    _coerce_value,
    get_nested_value,
    read_yaml,
    set_nested_value,
    write_yaml,
)


class TestReadYaml:
    def test_nonexistent_file(self):
        result = read_yaml(Path("/nonexistent/path.yaml"))
        assert result == {}

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        assert read_yaml(f) == {}

    def test_valid_file(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text("key: value\nnested:\n  a: 1\n")
        result = read_yaml(f)
        assert result == {"key": "value", "nested": {"a": 1}}

    def test_malformed_yaml(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("key: [invalid yaml\n  - broken")
        result = read_yaml(f)
        assert result == {}

    def test_non_dict_yaml(self, tmp_path):
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n")
        result = read_yaml(f)
        assert result == {}


class TestWriteYaml:
    def test_write_creates_file(self, tmp_path):
        f = tmp_path / "output.yaml"
        write_yaml(f, {"key": "value"})
        assert f.exists()
        content = yaml.safe_load(f.read_text())
        assert content == {"key": "value"}

    def test_write_creates_parent_dirs(self, tmp_path):
        f = tmp_path / "nested" / "dir" / "config.yaml"
        write_yaml(f, {"a": 1})
        assert f.exists()

    def test_roundtrip(self, tmp_path):
        f = tmp_path / "roundtrip.yaml"
        data = {"bot": {"name": "Maximus"}, "openai": {"model": "gpt-4o"}}
        write_yaml(f, data)
        result = read_yaml(f)
        assert result == data


class TestSetNestedValue:
    def test_simple_key(self):
        data = {}
        set_nested_value(data, "key", "value")
        assert data == {"key": "value"}

    def test_dotted_key(self):
        data = {}
        set_nested_value(data, "openai.model", "gpt-4-turbo")
        assert data == {"openai": {"model": "gpt-4-turbo"}}

    def test_deep_nesting(self):
        data = {}
        set_nested_value(data, "a.b.c.d", "deep")
        assert data == {"a": {"b": {"c": {"d": "deep"}}}}

    def test_overwrite_existing(self):
        data = {"openai": {"model": "gpt-4o", "temperature": 0.8}}
        set_nested_value(data, "openai.model", "gpt-4-turbo")
        assert data["openai"]["model"] == "gpt-4-turbo"
        assert data["openai"]["temperature"] == 0.8

    def test_overwrite_non_dict(self):
        data = {"openai": "string_value"}
        set_nested_value(data, "openai.model", "gpt-4o")
        assert data == {"openai": {"model": "gpt-4o"}}


class TestGetNestedValue:
    def test_simple_key(self):
        data = {"key": "value"}
        assert get_nested_value(data, "key") == "value"

    def test_dotted_key(self):
        data = {"openai": {"model": "gpt-4o"}}
        assert get_nested_value(data, "openai.model") == "gpt-4o"

    def test_missing_key(self):
        data = {"openai": {"model": "gpt-4o"}}
        assert get_nested_value(data, "openai.missing") is None
        assert get_nested_value(data, "missing.key") is None

    def test_empty_data(self):
        assert get_nested_value({}, "key") is None


class TestCoerceValue:
    def test_bool_true(self):
        assert _coerce_value("true") is True
        assert _coerce_value("True") is True
        assert _coerce_value("yes") is True
        assert _coerce_value("Yes") is True

    def test_bool_false(self):
        assert _coerce_value("false") is False
        assert _coerce_value("False") is False
        assert _coerce_value("no") is False

    def test_integer(self):
        assert _coerce_value("42") == 42
        assert _coerce_value("0") == 0
        assert _coerce_value("-1") == -1

    def test_float(self):
        assert _coerce_value("3.14") == 3.14
        assert _coerce_value("0.8") == 0.8

    def test_string(self):
        assert _coerce_value("hello") == "hello"
        assert _coerce_value("gpt-4o") == "gpt-4o"
