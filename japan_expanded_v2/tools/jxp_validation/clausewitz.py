"""Small, duplicate-preserving parser for EU4 Clausewitz text files.

The validator needs structure and source locations, but it must not normalize
away repeated keys such as ``tag``, ``modifier``, or ``if``.  This parser keeps
entries in source order and accepts the assignment/comparison operators used
by EU4 scripts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, TypeAlias


class ClausewitzParseError(ValueError):
    """Raised when a Clausewitz text document is structurally malformed."""


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    text: str
    line: int
    column: int
    quoted: bool = False


@dataclass(frozen=True, slots=True)
class Scalar:
    text: str
    line: int
    column: int
    quoted: bool = False


@dataclass(frozen=True, slots=True)
class Entry:
    key: str | None
    operator: str | None
    value: "Value"
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class Object:
    entries: tuple[Entry, ...]


Value: TypeAlias = Scalar | Object


@dataclass(frozen=True, slots=True)
class Document:
    source: Path
    root: Object


OPERATORS = {"=", "==", "!=", "<", ">", "<=", ">=", "?="}


def read_clausewitz_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return data.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise ClausewitzParseError(f"{path}: cannot decode as UTF-8 or cp1252") from exc


def _parse_error(source: Path, line: int, column: int, message: str) -> ClausewitzParseError:
    return ClausewitzParseError(f"{source}:{line}:{column}: {message}")


def tokenize(text: str, source: Path = Path("<memory>")) -> tuple[Token, ...]:
    tokens: list[Token] = []
    index = 0
    line = 1
    column = 1
    length = len(text)

    while index < length:
        char = text[index]

        if char in " \t\r":
            index += 1
            column += 1
            continue
        if char == "\n":
            index += 1
            line += 1
            column = 1
            continue
        if char == "#":
            while index < length and text[index] != "\n":
                index += 1
                column += 1
            continue
        if char in "{}":
            tokens.append(Token(char, char, line, column))
            index += 1
            column += 1
            continue
        if char in "=<>!?":
            start_line = line
            start_column = column
            if index + 1 < length and text[index : index + 2] in OPERATORS:
                operator = text[index : index + 2]
                index += 2
                column += 2
            elif char in "=<>" and char in OPERATORS:
                operator = char
                index += 1
                column += 1
            else:
                raise _parse_error(source, line, column, f"unexpected character {char!r}")
            tokens.append(Token("OP", operator, start_line, start_column))
            continue
        if char == '"':
            start_line = line
            start_column = column
            index += 1
            column += 1
            buffer: list[str] = []
            while index < length:
                char = text[index]
                if char == '"':
                    index += 1
                    column += 1
                    break
                if char == "\\" and index + 1 < length:
                    next_char = text[index + 1]
                    if next_char in {'"', "\\"}:
                        buffer.append(next_char)
                    else:
                        buffer.extend(("\\", next_char))
                    index += 2
                    column += 2
                    continue
                if char == "\n":
                    buffer.append(char)
                    index += 1
                    line += 1
                    column = 1
                    continue
                buffer.append(char)
                index += 1
                column += 1
            else:
                raise _parse_error(source, start_line, start_column, "unterminated quoted string")
            tokens.append(Token("SCALAR", "".join(buffer), start_line, start_column, quoted=True))
            continue

        start = index
        start_line = line
        start_column = column
        while index < length:
            char = text[index]
            if char.isspace() or char in '{}#"=<>!?':
                break
            index += 1
            column += 1
        if start == index:
            raise _parse_error(source, line, column, f"unexpected character {text[index]!r}")
        tokens.append(Token("SCALAR", text[start:index], start_line, start_column))

    return tuple(tokens)


class Parser:
    def __init__(self, tokens: tuple[Token, ...], source: Path):
        self.tokens = tokens
        self.source = source
        self.index = 0

    def peek(self) -> Token | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def pop(self) -> Token:
        token = self.peek()
        if token is None:
            if self.tokens:
                last = self.tokens[-1]
                raise _parse_error(self.source, last.line, last.column, "unexpected end of file")
            raise _parse_error(self.source, 1, 1, "unexpected end of file")
        self.index += 1
        return token

    def parse(self) -> Object:
        return self.parse_object(expect_close=False)

    def parse_object(self, expect_close: bool) -> Object:
        entries: list[Entry] = []
        while True:
            token = self.peek()
            if token is None:
                if expect_close:
                    if self.tokens:
                        last = self.tokens[-1]
                        raise _parse_error(self.source, last.line, last.column, "missing closing brace")
                    raise _parse_error(self.source, 1, 1, "missing closing brace")
                return Object(tuple(entries))
            if token.kind == "}":
                if not expect_close:
                    raise _parse_error(self.source, token.line, token.column, "unexpected closing brace")
                self.pop()
                return Object(tuple(entries))
            if token.kind in {"{", "OP"}:
                raise _parse_error(self.source, token.line, token.column, f"unexpected token {token.text!r}")

            key_token = self.pop()
            next_token = self.peek()
            if next_token is not None and next_token.kind == "OP":
                operator = self.pop().text
                value = self.parse_value()
                entries.append(
                    Entry(key_token.text, operator, value, key_token.line, key_token.column)
                )
            else:
                entries.append(
                    Entry(
                        None,
                        None,
                        Scalar(
                            key_token.text,
                            key_token.line,
                            key_token.column,
                            quoted=key_token.quoted,
                        ),
                        key_token.line,
                        key_token.column,
                    )
                )

    def parse_value(self) -> Value:
        token = self.pop()
        if token.kind == "{":
            return self.parse_object(expect_close=True)
        if token.kind == "SCALAR":
            return Scalar(token.text, token.line, token.column, quoted=token.quoted)
        raise _parse_error(self.source, token.line, token.column, f"invalid value {token.text!r}")


def parse_text(text: str, source: Path = Path("<memory>")) -> Document:
    return Document(source, Parser(tokenize(text, source), source).parse())


def parse_file(path: Path) -> Document:
    return parse_text(read_clausewitz_text(path), path)


def entries_named(obj: Object | None, key: str) -> tuple[Entry, ...]:
    if obj is None:
        return ()
    return tuple(entry for entry in obj.entries if entry.key == key)


def first_entry(obj: Object | None, key: str) -> Entry | None:
    values = entries_named(obj, key)
    return values[0] if values else None


def first_object(obj: Object | None, key: str) -> Object | None:
    entry = first_entry(obj, key)
    return entry.value if entry is not None and isinstance(entry.value, Object) else None


def first_scalar(obj: Object | None, key: str) -> str | None:
    entry = first_entry(obj, key)
    return entry.value.text if entry is not None and isinstance(entry.value, Scalar) else None


def bare_scalars(obj: Object | None) -> tuple[Scalar, ...]:
    if obj is None:
        return ()
    return tuple(
        entry.value
        for entry in obj.entries
        if entry.key is None and isinstance(entry.value, Scalar)
    )


def walk_entries(obj: Object, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Entry]]:
    for entry in obj.entries:
        yield path, entry
        if isinstance(entry.value, Object):
            component = entry.key if entry.key is not None else "{}"
            yield from walk_entries(entry.value, path + (component,))


def assignment_matches(entry: Entry, key: str, value: str | None = None) -> bool:
    if entry.key != key or not isinstance(entry.value, Scalar):
        return False
    return value is None or entry.value.text == value


def find_assignments(
    obj: Object,
    key: str,
    value: str | None = None,
) -> tuple[tuple[tuple[str, ...], Entry], ...]:
    return tuple(
        (path, entry)
        for path, entry in walk_entries(obj)
        if assignment_matches(entry, key, value)
    )


def find_objects(obj: Object, key: str) -> tuple[tuple[tuple[str, ...], Entry], ...]:
    return tuple(
        (path, entry)
        for path, entry in walk_entries(obj)
        if entry.key == key and isinstance(entry.value, Object)
    )
