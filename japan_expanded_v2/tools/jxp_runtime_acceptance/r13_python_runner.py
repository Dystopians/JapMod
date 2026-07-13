#!/usr/bin/env python3
"""Run the fixed R13 Python gate surface under ``python -I -S -B``.

The parent helper supplies canonical, sealed validator, dependency, and exact
file-capability paths. Standard-library paths remain first; only the
Git-verified validator roots and the isolated copy of the three approved
validation distributions are appended afterwards.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import runpy
import stat
import sys


_ROOT_ENV = (
    "JXP_R13_MAIN_TOOLS",
    "JXP_R13_MAP_TOOLS",
    "JXP_R13_DEPENDENCY_SITE",
    "JXP_R13_PYCACHE_ROOT",
    "JXP_R13_QUICK_VALIDATE",
    "JXP_R13_MISSION_OVERLAP_SCRIPT",
)
_ALLOWED_CODE = {
    "import sys,numpy,PIL,yaml; assert sys.version_info >= (3,10); "
    "nv=int(numpy.__version__.split(chr(46))[0]); "
    "pv=int(PIL.__version__.split(chr(46))[0]); "
    "yv=int(yaml.__version__.split(chr(46))[0]); "
    "assert 2 <= nv < 3; assert 10 <= pv < 13; assert 6 <= yv < 7",
    "import numpy,PIL,yaml; "
    "print(numpy.__version__+chr(32)+PIL.__version__+chr(32)+yaml.__version__)",
}


def _is_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    if os.name != "nt":
        return False
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _ordinary(path_text: str, *, directory: bool) -> Path:
    supplied = Path(os.path.abspath(path_text))
    resolved = supplied.resolve(strict=True)
    correct_type = resolved.is_dir() if directory else resolved.is_file()
    if supplied != resolved or not correct_type:
        raise RuntimeError(f"R13 isolated Python path is not canonical: {supplied}")
    cursor = supplied
    while cursor != cursor.parent:
        if _is_reparse(cursor):
            raise RuntimeError(f"R13 isolated Python path traverses reparse data: {cursor}")
        cursor = cursor.parent
    return resolved


def _relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _package_origin(name: str, root: Path) -> None:
    spec = importlib.util.find_spec(name)
    if spec is None:
        raise RuntimeError(f"R13 isolated Python package is unavailable: {name}")
    candidates: list[Path] = []
    if spec.origin not in (None, "built-in", "frozen"):
        candidates.append(Path(spec.origin).resolve(strict=True))
    if spec.submodule_search_locations is not None:
        candidates.extend(
            Path(item).resolve(strict=True) for item in spec.submodule_search_locations
        )
    if not candidates or any(not _relative_to(item, root) for item in candidates):
        raise RuntimeError(
            f"R13 isolated Python package escaped its approved root: {name}"
        )


def _configure_paths() -> tuple[Path, Path, Path, Path, Path]:
    if not (
        sys.flags.isolated
        and sys.flags.no_site
        and sys.flags.safe_path
        and sys.dont_write_bytecode
    ):
        raise RuntimeError("R13 Python runner requires -I -S -B")
    if any(not os.environ.get(key) for key in _ROOT_ENV):
        raise RuntimeError("R13 Python runner root environment is incomplete")
    main_tools = _ordinary(os.environ[_ROOT_ENV[0]], directory=True)
    map_tools = _ordinary(os.environ[_ROOT_ENV[1]], directory=True)
    dependency_site = _ordinary(os.environ[_ROOT_ENV[2]], directory=True)
    pycache_root = _ordinary(os.environ[_ROOT_ENV[3]], directory=True)
    quick_validate = _ordinary(os.environ[_ROOT_ENV[4]], directory=False)
    mission_overlap = _ordinary(os.environ[_ROOT_ENV[5]], directory=False)
    if sys.pycache_prefix is None or Path(sys.pycache_prefix).resolve() != pycache_root:
        raise RuntimeError("R13 Python runner has an unapproved pycache prefix")

    base = Path(sys.base_prefix).resolve(strict=True)
    for item in sys.path:
        if not item:
            raise RuntimeError("R13 isolated Python retained an empty import path")
        candidate = Path(item).resolve(strict=False)
        if not _relative_to(candidate, base) or "site-packages" in {
            part.casefold() for part in candidate.parts
        }:
            raise RuntimeError(
                f"R13 isolated Python inherited an unapproved import path: {item}"
            )
    sys.path.extend((str(main_tools), str(map_tools), str(dependency_site)))
    _package_origin("jxp_validation", main_tools)
    for package in ("numpy", "PIL", "yaml"):
        _package_origin(package, dependency_site)
    # The skill file is an execution capability, never an import root.
    return main_tools, map_tools, dependency_site, quick_validate, mission_overlap


def _run() -> None:
    (
        main_tools,
        map_tools,
        _dependency_site,
        quick_validate,
        mission_overlap,
    ) = _configure_paths()
    arguments = sys.argv[1:]
    if arguments == ["--version"]:
        print(f"Python {sys.version.split()[0]}")
        return
    if len(arguments) >= 2 and arguments[0] == "-c":
        source = arguments[1]
        if source not in _ALLOWED_CODE:
            raise RuntimeError("R13 Python runner rejected an unapproved -c program")
        sys.argv = ["-c", *arguments[2:]]
        namespace = {
            "__name__": "__main__",
            "__file__": "<string>",
            "__builtins__": __builtins__,
        }
        exec(compile(source, "<string>", "exec"), namespace, namespace)
        return
    if len(arguments) >= 2 and arguments[0] == "-m":
        module = arguments[1]
        if module != "unittest":
            raise RuntimeError(f"R13 Python runner rejected module: {module}")
        sys.argv = [module, *arguments[2:]]
        runpy.run_module(module, run_name="__main__", alter_sys=True)
        return
    if not arguments or arguments[0].startswith("-"):
        raise RuntimeError("R13 Python runner received unsupported arguments")
    script = _ordinary(arguments[0], directory=False)
    if not (
        _relative_to(script, main_tools)
        or _relative_to(script, map_tools)
        or script == quick_validate
        or script == mission_overlap
    ):
        raise RuntimeError(f"R13 Python runner rejected script: {script}")
    sys.argv = [str(script), *arguments[1:]]
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    _run()
