#!/usr/bin/env python3
"""Validate the portable skill and inactive examples without third-party modules."""

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = {"discover", "render", "preview", "query", "inspect", "compare", "check", "release"}
REQUEST_FIELDS = {
    "operation", "source", "base", "target", "paths", "recursive", "id",
    "beforeId", "afterId", "resourceId", "query", "offset", "limit", "fields",
    "maxCPURequests", "maxMemRequests", "maxCPULimits", "maxMemLimits",
    "requireRequests", "requireLimits",
}
QUERY_FIELDS = {"cluster", "kind", "name", "namespace", "group", "labels", "producer", "action"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    skill = ROOT / "skills/gitops-preview/SKILL.md"
    license_path = skill.parent / "LICENSE"
    require(license_path.is_file(), "distributed skill directory must include LICENSE")
    require(license_path.read_bytes() == (ROOT / "LICENSE").read_bytes(),
            "distributed skill LICENSE must match root LICENSE byte-for-byte")
    text = skill.read_text()
    require(len(text.splitlines()) < 100, "SKILL.md must be under 100 lines")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    require(match is not None, "missing skill frontmatter")
    metadata = {}
    for line in match[1].splitlines():
        key, separator, value = line.partition(": ")
        require(separator and key not in metadata, "invalid/duplicate frontmatter field")
        metadata[key] = value
    require(set(metadata) == {"name", "description"}, "use portable name/description metadata")
    name = metadata["name"]
    require(name == skill.parent.name and len(name) <= 64, "invalid skill name/length")
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name), "invalid skill name syntax")
    description = metadata["description"]
    require(0 < len(description) <= 1024 and "Use when " in description, "invalid description")
    expected = {"WORKFLOW.md", "CONTRACT.md", "INSTALL.md", "CROSSPLANE.md"}
    references = skill.parent / "references"
    require({p.name for p in references.iterdir()} == expected, "unexpected reference layout")
    for name in expected:
        require(f"(references/{name})" in text, f"unlinked reference {name}")
    for path in [ROOT / "README.md", skill, *references.glob("*.md")]:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            require(resolved.is_relative_to(ROOT) and resolved.exists(), f"broken link: {path}: {target}")
            if path.parent == references:
                require(resolved.parent != references, "references must not form a nested reading chain")

    examples = list((ROOT / "examples/requests").glob("*.json"))
    require(len(examples) >= 2, "need single and batch examples")
    forms = set()
    for path in examples:
        data = json.loads(path.read_text())
        batch = "requests" in data
        forms.add(batch)
        if batch:
            require(set(data) == {"requests"}, f"invalid batch: {path}")
        requests = data["requests"] if batch else [data]
        require(isinstance(requests, list) and 1 <= len(requests) <= 32, "invalid batch size")
        for index, request in enumerate(requests):
            require(set(request) <= REQUEST_FIELDS, f"unknown request fields: {path}")
            require(request.get("operation") in OPERATIONS, "invalid operation")
            require(set(request.get("query", {})) <= QUERY_FIELDS, "unknown query field")
            for key in ("id", "beforeId", "afterId", "resourceId"):
                value = request.get(key, "")
                if value.startswith("@"):
                    ref = re.fullmatch(r"@(\d+)\.([A-Za-z0-9_.]+)", value)
                    require(batch and ref and int(ref[1]) < index, f"invalid batch reference: {value}")
                    require(not ref[2].startswith("data."), "references already start at data")
    require(forms == {False, True}, "missing single or batch form")

    hosts = ROOT / "examples/hosts"
    opencode = json.loads((hosts / "opencode.json.example").read_text())
    require(set(opencode) == {"$schema", "mcp"}, "unexpected OpenCode config/permissions")
    require(opencode["$schema"] == "https://opencode.ai/config.json", "wrong OpenCode schema")
    server = opencode["mcp"]["gitops-preview"]
    command = ["/ABSOLUTE/PATH/TO/gitops-preview", "mcp", "--root", "/ABSOLUTE/PATH/TO/WORKSPACE"]
    require(server == {"type": "local", "command": command, "enabled": True}, "unsafe OpenCode template")
    claude = json.loads((hosts / "claude.mcp.json.example").read_text())
    require(claude == {"mcpServers": {"gitops-preview": {
        "type": "stdio", "command": command[0], "args": command[1:],
    }}}, "unsafe Claude template")
    crossplane = json.loads((hosts / "opencode.crossplane.json.example").read_text())
    require(crossplane == {"$schema": opencode["$schema"], "mcp": {
        "gitops-preview-crossplane": {
            "type": "local", "enabled": False,
            "command": command + ["--trusted", "--crossplane", "--crossplane-engine",
                                  "/APPROVED/PATH/TO/crossplane-core"],
        },
    }}, "Crossplane template must remain disabled with explicit startup grants")
    for active in ("opencode.json", "opencode.jsonc", ".mcp.json", ".opencode", ".claude"):
        require(not (ROOT / active).exists(), f"unexpected active host configuration: {active}")
    for script in ("validate.py", "test-workflow.py", "test-crossplane.py"):
        path = ROOT / "scripts" / script
        require(path.read_text().startswith("#!/usr/bin/env python3\n"), "missing script shebang")
        require(path.stat().st_mode & 0o111, f"script is not executable: {script}")
    print("PASS: skill metadata, bundled license, one-level references, JSON requests, inactive host templates")


if __name__ == "__main__":
    main()
