#!/usr/bin/env python3
"""Render every Application the way Argo CD will, and enforce repo rules.

For each Application under clusters/<env>/ that uses a Helm chart from another repo, this
clones the chart at the exact pinned revision, resolves the $values files from this checkout,
and runs `helm template`. A broken values file, a missing chart tag or a schema violation fails
here, in the pull request, instead of as an Argo CD sync error in the cluster.

Run with: uv run --with pyyaml scripts/validate.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_REVISIONS = {"HEAD", "latest", ""}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], cwd: Path | None = None) -> str:
    done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        fail(f"{' '.join(cmd)}\n{done.stderr.strip()}")
    return done.stdout


def validate_application(path: Path, work: Path) -> int:
    rendered = 0
    for doc in yaml.safe_load_all(path.read_text()):
        if not doc or doc.get("kind") != "Application":
            continue
        name = doc["metadata"]["name"]
        sources = doc["spec"].get("sources") or [doc["spec"]["source"]]
        for src in sources:
            rev = src.get("targetRevision", "")
            if rev in FORBIDDEN_REVISIONS:
                fail(f"{path.name}: {name} source {src['repoURL']} has unpinned revision {rev!r}")
        for src in sources:
            helm = src.get("helm")
            if not helm or "ref" in src:
                continue
            checkout = work / f"{name}-chart"
            if not checkout.exists():
                run(["git", "clone", "--quiet", "--depth", "1", "--branch",
                     src["targetRevision"], src["repoURL"], str(checkout)])
            cmd = ["helm", "template", helm.get("releaseName", name), str(checkout / src["path"])]
            for vf in helm.get("valueFiles", []):
                resolved = ROOT / vf.removeprefix("$values/") if vf.startswith("$values/") else checkout / vf
                if not resolved.is_file():
                    fail(f"{path.name}: {name} references missing values file {vf}")
                cmd += ["-f", str(resolved)]
            run(cmd)
            rendered += 1
            print(f"ok: {path.relative_to(ROOT)} -> {name} renders")
    return rendered


def check_image_tags() -> None:
    for values in ROOT.glob("apps/*/envs/*/values.yaml"):
        data = yaml.safe_load(values.read_text()) or {}
        tag = (data.get("image") or {}).get("tag")
        if not tag or tag == "latest":
            fail(f"{values.relative_to(ROOT)}: image.tag must be set and must not be 'latest'")
        print(f"ok: {values.relative_to(ROOT)} image.tag={tag}")


def main() -> None:
    check_image_tags()
    total = 0
    with tempfile.TemporaryDirectory() as tmp:
        for manifest in sorted(ROOT.glob("clusters/*/*.yaml")):
            total += validate_application(manifest, Path(tmp))
    if total == 0:
        fail("no Helm Applications were rendered; is clusters/ empty?")


if __name__ == "__main__":
    main()
