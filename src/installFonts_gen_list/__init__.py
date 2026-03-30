#!/usr/bin/env python3
import os
import re
import pathlib
import requests
import sys

OWNER = "NixOS"
REPO = "nixpkgs"
ISSUE_NUMBER = 495640
IGNORE_FILE = "pkgs/build-support/setup-hooks/install-fonts.sh"
PATTERN = "$out/share/fonts"

TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

session = requests.Session()
session.headers.update(HEADERS)


def gh_get(url, params=None):
    r = session.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r


def paged_json(url, params=None):
    out = []
    page = 1
    params = dict(params or {})
    params.setdefault("per_page", 100)
    while True:
        params["page"] = page
        data = gh_get(url, params=params).json()
        if not data:  # Fixed syntax error here
            break
        if isinstance(data, list):
            out.extend(data)
            if len(data) < params["per_page"]:
                break
            page += 1
        else:
            return data
    return out


def issue_body():
    url = f"https://api.github.com{OWNER}/{REPO}/issues/{ISSUE_NUMBER}"
    return gh_get(url).json().get("body") or ""


def mentioned_pr_numbers(text):
    seen = set()
    out = []
    for m in re.finditer(r"(?<!\w)#(\d+)\b", text):
        n = int(m.group(1))
        if n != ISSUE_NUMBER and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def pr_data(pr_number):
    url = f"https://api.github.com{OWNER}/{REPO}/pulls/{pr_number}"
    return gh_get(url).json()


def pr_files(pr_number):
    url = f"https://api.github.com{OWNER}/{REPO}/pulls/{pr_number}/files"
    return paged_json(url)


def fonts_matches():
    # Ensure we are in the root of nixpkgs
    root = pathlib.Path(".")
    if not (root / "pkgs").exists():
        print(
            "Error: 'pkgs' directory not found. Run this from the nixpkgs root.",
            file=sys.stderr,
        )
        sys.exit(1)

    matches = []
    # Narrowing rglob to pkgs/ for performance
    for path in root.joinpath("pkgs").rglob("*"):
        if not path.is_file():
            continue

        # Get path relative to the repo root for comparison
        rel = path.relative_to(root).as_posix()
        if rel == IGNORE_FILE:
            continue

        try:
            # Skip large binaries to speed up local search
            if path.suffix in [".nix", ".sh", ".md", ""]:
                if PATTERN in path.read_text(encoding="utf-8", errors="ignore"):
                    matches.append(rel)
        except Exception:
            pass
    return sorted(matches)


def main():
    body = issue_body()
    all_pr_numbers = mentioned_pr_numbers(body)

    file_to_pr = {}

    for n in all_pr_numbers:
        try:
            pr = pr_data(n)
            merged = pr.get("merged_at") is not None
            for f_info in pr_files(n):
                file_path = f_info.get("filename")
                if file_path:
                    file_to_pr.setdefault(file_path, []).append((n, merged))
        except Exception as e:
            print(f"Error fetching PR #{n}: {e}", file=sys.stderr)

    matches = fonts_matches()

    for path in matches:
        pr_annos = file_to_pr.get(path, [])
        if pr_annos:
            pr_annos.sort(key=lambda x: x[0])
            pr_num = pr_annos[-1][0]
            merged_any = any(merged for _, merged in pr_annos)
            status = "[x]" if merged_any else "[ ]"
            print(f"- {status} `{path}` `#{pr_num}`")
        else:
            print(f"- [ ] `{path}`")


if __name__ == "__main__":
    main()
