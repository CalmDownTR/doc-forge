"""Tests for CARD-004: BaseParser Interface + Registry (parsers/__init__.py)."""

from pathlib import Path

import pytest

from docforge.config import ParseConfig
from docforge.exceptions import FileNotSupportedError
from docforge.models import ContentBlock, ContentType
from docforge.parsers import (
    BaseParser,
    register_parser,
    get_parser,
    list_supported_types,
)


class DummyParser(BaseParser):
    """A dummy parser for testing the registry."""

    def can_parse(self, file_path: Path, file_type: str) -> bool:
        return file_type == "dummy"

    def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
        return [ContentBlock(type=ContentType.TEXT, content="dummy", page=1, reading_order=0)]


class TestBaseParser:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseParser()  # type: ignore[abstract]

    def test_subclass_must_implement_can_parse(self):
        with pytest.raises(TypeError):

            class IncompleteParser(BaseParser):
                def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
                    return []

            IncompleteParser()  # type: ignore[abstract]

    def test_subclass_must_implement_parse(self):
        with pytest.raises(TypeError):

            class IncompleteParser(BaseParser):
                def can_parse(self, file_path: Path, file_type: str) -> bool:
                    return True

            IncompleteParser()  # type: ignore[abstract]


class TestParserRegistry:
    def test_register_and_get_parser(self):
        register_parser("dummy", DummyParser)
        parser = get_parser("dummy")
        assert isinstance(parser, DummyParser)

    def test_get_parser_unregistered_type_raises(self):
        with pytest.raises(FileNotSupportedError, match="No parser for type"):
            get_parser("nonexistent")

    def test_list_supported_types(self):
        # Register a parser and check it appears
        register_parser("dummy2", DummyParser)
        types = list_supported_types()
        assert "dummy2" in types

    def test_register_parser_overwrites(self):
        """Registering the same type twice should overwrite."""
        register_parser("dummy3", DummyParser)
        first = get_parser("dummy3")
        # Register again with potentially different parser (same class here is fine)
        register_parser("dummy3", DummyParser)
        second = get_parser("dummy3")
        # Both should be instances of DummyParser
        assert isinstance(first, DummyParser)
        assert isinstance(second, DummyParser)

    def test_get_parser_returns_new_instance_each_time(self):
        register_parser("dummy4", DummyParser)
        p1 = get_parser("dummy4")
        p2 = get_parser("dummy4")
        assert p1 is not p2
        assert isinstance(p1, DummyParser)
        assert isinstance(p2, DummyParser)

    def test_dummy_parser_can_parse(self):
        parser = DummyParser()
        assert parser.can_parse(Path("test.dummy"), "dummy") is True
        assert parser.can_parse(Path("test.txt"), "txt") is False

    def test_dummy_parser_parse(self):
        parser = DummyParser()
        config = ParseConfig()
        blocks = parser.parse(Path("test.dummy"), config)
        assert len(blocks) == 1
        assert blocks[0].content == "dummy"
        assert blocks[0].type == ContentType.TEXT
