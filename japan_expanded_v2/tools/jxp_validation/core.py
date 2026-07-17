"""Shared validation context, diagnostics, and release metadata checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

from .clausewitz import (
    ClausewitzParseError,
    Document,
    Entry,
    Scalar,
    find_assignments,
    first_scalar,
    parse_file,
)


TARGET_VERSION = "0.28.1"
SCRIPT_DIRECTORIES = ("common", "decisions", "events", "history", "missions")


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    message: str
    source: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"code": self.code, "message": self.message}
        if self.source is not None:
            result["source"] = self.source
        if self.line is not None:
            result["line"] = self.line
        return result


@dataclass(slots=True)
class CheckResult:
    name: str
    summary: str = ""
    issues: list[Issue] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metrics: dict[str, object] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.issues

    def add(
        self,
        code: str,
        message: str,
        source: str | None = None,
        line: int | None = None,
    ) -> None:
        self.issues.append(Issue(code, message, source, line))

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "passed": self.passed,
            "summary": self.summary,
            "issues": [issue.to_dict() for issue in self.issues],
            "notes": list(self.notes),
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True, slots=True)
class AssignmentOccurrence:
    source: Path
    path: tuple[str, ...]
    entry: Entry

    @property
    def value(self) -> str:
        assert isinstance(self.entry.value, Scalar)
        return self.entry.value.text


class ValidationContext:
    def __init__(self, mod_root: Path):
        self.mod_root = mod_root.resolve()
        self._documents: dict[Path, Document] = {}
        self.parse_errors: dict[Path, str] = {}

    def relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.mod_root).as_posix()
        except ValueError:
            return path.as_posix()

    def document(self, path: Path) -> Document | None:
        path = path.resolve()
        if path in self._documents:
            return self._documents[path]
        if path in self.parse_errors:
            return None
        try:
            document = parse_file(path)
        except (OSError, ClausewitzParseError) as exc:
            self.parse_errors[path] = str(exc)
            return None
        self._documents[path] = document
        return document

    def script_files(self) -> tuple[Path, ...]:
        files: set[Path] = set()
        for directory in SCRIPT_DIRECTORIES:
            root = self.mod_root / directory
            if root.exists():
                files.update(path.resolve() for path in root.rglob("*.txt") if path.is_file())
        return tuple(sorted(files, key=lambda path: self.relative(path).casefold()))

    def preload_scripts(self) -> tuple[Path, ...]:
        files = self.script_files()
        for path in files:
            self.document(path)
        return files

    def documents_for(self, files: Iterable[Path]) -> Iterator[Document]:
        for path in files:
            document = self.document(path)
            if document is not None:
                yield document

    def assignment_occurrences(
        self,
        key: str,
        value: str | None = None,
        files: Iterable[Path] | None = None,
    ) -> tuple[AssignmentOccurrence, ...]:
        selected = self.script_files() if files is None else tuple(files)
        found: list[AssignmentOccurrence] = []
        for document in self.documents_for(selected):
            for path, entry in find_assignments(document.root, key, value):
                found.append(AssignmentOccurrence(document.source, path, entry))
        return tuple(found)


def check_metadata(context: ValidationContext, expected_version: str) -> CheckResult:
    result = CheckResult("Release metadata")
    descriptor = context.mod_root / "descriptor.mod"
    if not descriptor.is_file():
        result.add("metadata.descriptor_missing", "descriptor.mod is missing", "descriptor.mod")
        result.summary = f"expected release {expected_version}"
        return result

    document = context.document(descriptor)
    if document is None:
        result.add(
            "metadata.descriptor_parse",
            context.parse_errors.get(descriptor.resolve(), "could not parse descriptor.mod"),
            "descriptor.mod",
        )
        result.summary = f"expected release {expected_version}"
        return result

    version = first_scalar(document.root, "version")
    if version != expected_version:
        result.add(
            "metadata.version",
            f"descriptor version is {version!r}; expected {expected_version!r}",
            "descriptor.mod",
        )
    result.metrics["expected_version"] = expected_version
    result.metrics["descriptor_version"] = version
    result.summary = f"descriptor version {version or '<missing>'}; target {expected_version}"
    return result


def check_script_parsing(context: ValidationContext) -> CheckResult:
    result = CheckResult("Clausewitz parsing")
    files = context.preload_scripts()
    for path, message in sorted(
        context.parse_errors.items(), key=lambda item: context.relative(item[0]).casefold()
    ):
        if path in files:
            result.add("script.parse", message, context.relative(path))
    parsed = len(files) - sum(1 for path in files if path in context.parse_errors)
    result.metrics.update({"files": len(files), "parsed": parsed})
    result.summary = f"parsed {parsed}/{len(files)} gameplay script files"
    return result
