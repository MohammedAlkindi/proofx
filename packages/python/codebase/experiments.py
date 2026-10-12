"""Versioned experiment registry and checksum-pinned reproduction commands."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import stat
import urllib.request
import zipfile
from importlib.resources import files
from pathlib import Path
from typing import TypedDict, cast

MAX_BYTES = 64 * 1024 * 1024


class Entry(TypedDict):
    id: str
    version: int
    question: str
    bundle_url: str
    sha256: str


def registry() -> list[Entry]:
    return cast(
        list[Entry],
        json.loads(
            files("codebase").joinpath("protocols/registry.json").read_text(encoding="utf-8")
        ),
    )


def unpack(data: bytes, expected_digest: str, output: Path) -> None:
    """Extract a pinned, bounded, flat archive into a new directory only."""
    if len(data) > MAX_BYTES or hashlib.sha256(data).hexdigest() != expected_digest:
        raise ValueError("bundle size or SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if not entries or len(entries) > 100 or sum(e.file_size for e in entries) > MAX_BYTES:
            raise ValueError("bundle exceeds extraction limits")
        seen: set[str] = set()
        for entry in entries:
            name = entry.filename
            if (
                not name
                or name.casefold() in seen
                or name in (".", "..")
                or name.rstrip(" .") != name
                or any(c in name for c in "/\\:")
                or entry.is_dir()
                or stat.S_ISLNK(entry.external_attr >> 16)
            ):
                raise ValueError("bundle must contain distinct flat regular files")
            seen.add(name.casefold())
        output.mkdir(parents=True, exist_ok=False)
        for entry in entries:
            # Source snapshots are data. Nothing from the archive is imported.
            (output / entry.filename).write_bytes(archive.read(entry))


def reproduce(
    experiment: str, output: Path, bundle: Path | None = None, *, verify_only: bool = False
) -> dict[str, object]:
    entry = next((item for item in registry() if item["id"] == experiment), None)
    if entry is None:
        raise ValueError("unknown experiment ID")
    if output.exists():
        raise FileExistsError(output)
    if bundle is None:
        with urllib.request.urlopen(entry["bundle_url"], timeout=60) as response:
            data = response.read(MAX_BYTES + 1)
    else:
        with bundle.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
    published = output / "published"
    unpack(data, entry["sha256"], published)
    if experiment == "GB-002":
        from codebase.study import run, verify

        verified = verify(published)
        scientific = ("protocol.json", "reference.json", "selections.jsonl", "analysis.json")
    else:
        from codebase.benchmark import BenchmarkConfig, run_benchmark, verify_bundle

        verified = verify_bundle(published)
        scientific = tuple(
            json.loads((published / "manifest.json").read_text(encoding="utf-8"))["artifacts"]
        )
    result: dict[str, object] = {
        "experiment": experiment,
        "version": entry["version"],
        "verified": verified,
    }
    if not verify_only:
        fresh = output / "reproduced"
        if experiment == "GB-002":
            run(fresh)
            verify(fresh)
        else:
            run_benchmark(BenchmarkConfig(), fresh)
            verify_bundle(fresh)
        mismatches = [
            name
            for name in scientific
            if (fresh / name).read_bytes() != (published / name).read_bytes()
        ]
        result["scientific_artifacts_match"] = not mismatches
        result["mismatches"] = mismatches
        result["environment_note"] = (
            "Compare both manifests for source and dependency differences; archived code was not executed."
        )
        (output / "reproduction.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        if mismatches:
            raise ValueError(f"reproduction differs: {', '.join(mismatches)}; both copies retained")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("list")
    for action in ("verify", "reproduce"):
        command = commands.add_parser(action)
        command.add_argument("experiment", choices=("GB-001", "GB-002"))
        command.add_argument("output", type=Path)
        command.add_argument(
            "--bundle", type=Path, help="local ZIP; must match the registry checksum"
        )
    args = parser.parse_args()
    try:
        result = (
            registry()
            if args.action == "list"
            else reproduce(
                args.experiment, args.output, args.bundle, verify_only=args.action == "verify"
            )
        )
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"proofx-experiments: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
