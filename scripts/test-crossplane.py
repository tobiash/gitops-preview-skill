#!/usr/bin/env python3
"""Test approved released binaries/runtimes against a temporary four-XRD example."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CACHE_QUERY = {
    "cluster": "production", "kind": "ConfigMap", "action": "modified",
    "producer": "XR XCache apps/checkout-app-cache",
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def executable(variable):
    supplied = os.environ.get(variable)
    if variable == "GITOPS_PREVIEW_BINARY":
        supplied = supplied or os.environ.get("FMP_BINARY")
    require(supplied, f"set {variable} explicitly; no automatic installation")
    found = shutil.which(supplied)
    require(found, f"{variable} must name an existing executable")
    return str(Path(found).resolve())


def success(response):
    require(response.get("schemaVersion") == "1", "unsupported agent schema")
    require(response.get("status") == "success" and response.get("complete") is True,
            f"expected complete success: {response}")


def main():
    binary = executable("GITOPS_PREVIEW_BINARY")
    engine = executable("CROSSPLANE_ENGINE")
    target = os.environ.get("CROSSPLANE_FUNCTION_TARGET")
    require(target, "set CROSSPLANE_FUNCTION_TARGET to an explicitly approved running function")
    example = os.environ.get("TOOLKIT_EXAMPLE_ROOT")
    require(example, "set TOOLKIT_EXAMPLE_ROOT to the reviewed v0.2.0-rc.1 example")
    example = Path(example).resolve()
    require(all((example / side / ".gitops-preview.yaml").is_file()
                for side in ("before", "after")), "example lacks both complete source snapshots")
    version = subprocess.run([engine, "--version"], capture_output=True, text=True, timeout=10)
    require(version.returncode == 0 and version.stdout.strip() == "v2.4.2",
            "the reviewed controller must be v2.4.2, not the public CLI")

    with tempfile.TemporaryDirectory(prefix="gitops-crossplane-skill-") as temporary:
        workspace = Path(temporary) / "example"
        workspace.mkdir()
        for side in ("before", "after"):
            shutil.copytree(example / side, workspace / side)
        grants = ["--trusted", "--crossplane", "--crossplane-engine", engine,
                  "--crossplane-function", f"templating={target}"]

        def run(request, failure=False, root=workspace, startup=grants):
            result = subprocess.run(
                [binary, "agent", "--root", str(root), *startup], input=json.dumps(request),
                capture_output=True, text=True, timeout=180, cwd=temporary,
            )
            try:
                response = json.loads(result.stdout)
            except json.JSONDecodeError as error:
                raise AssertionError(f"missing JSON; exit={result.returncode}: {result.stderr}") from error
            if failure:
                require(result.returncode != 0 and response.get("status") == "failure"
                        and response.get("complete") is False, f"failure published success: {response}")
                require("data" not in response, "incomplete operation published authoritative data")
            else:
                require(result.returncode == 0, f"CLI failed: {result.stderr}")
                success(response)
                for item in response.get("results", []):
                    success(item)
            return response

        discovery = run({"operation": "discover"}, root=workspace / "before")["data"]
        require(discovery["profile"] == "trusted" and "1" in discovery["schemaVersions"],
                "wrong startup profile/schema")
        require(discovery["helm"] and discovery["configFound"], "preferred config was not discovered")

        # Repository intent cannot enable a plugin that was not granted at startup.
        unexpanded = run({"operation": "render", "source": "path:before"}, startup=[])["data"]
        require(unexpanded["resourceCount"] < 51, "repository config granted Crossplane execution")
        denied = subprocess.run(
            [binary, "agent", "--root", str(workspace), *grants[1:]],
            input=json.dumps({"operation": "render", "source": "path:before"}),
            capture_output=True, text=True, timeout=30,
        )
        require(denied.returncode != 0 and "requires --trusted" in denied.stderr,
                "Crossplane startup bypassed the trust requirement")
        invalid = run({"operation": "render", "source": "path:before", "crossplane": True}, failure=True)
        require(invalid["error"]["code"] == "InvalidInput", "request JSON granted renderer capabilities")

        batch = json.loads((ROOT / "examples/requests/crossplane-preview-batch.json").read_text())
        results = run(batch)["results"]
        diff, page, inspected, checked = [item["data"] for item in results[:4]]
        require(diff["summary"] == {"added": 3, "modified": 17, "deleted": 1, "total": 21},
                f"nested source effects changed: {diff}")
        require(page["total"] == 1 and not page["truncated"], "controlled XR query is not unique")
        require(inspected["old"]["/spec/config/dbInstanceClass"] == "db.t3.small"
                and inspected["new"]["/spec/config/dbInstanceClass"] == "db.t3.medium"
                and inspected["old"]["/spec/config/storage"] == 20
                and inspected["new"]["/spec/config/storage"] == 40, "nested database inputs were lost")
        require(checked["verdict"] == "passed" and checked["classificationCount"] == 5,
                "policy result differs from rendered effects")
        require(all(item["data"]["released"] for item in results[4:]), "handles were not released")

        def logical_preview(before_memory, after_memory):
            requests = [
                {"operation": "preview", "base": "path:before", "target": "path:after"},
                {"operation": "query", "id": "@0.id", "query": CACHE_QUERY, "limit": 1},
                {"operation": "query", "id": "@0.id", "query": CACHE_QUERY, "offset": 1, "limit": 1},
                {"operation": "inspect", "id": "@0.id", "resourceId": "@1.items.0.resourceId", "fields": ["/data"]},
                {"operation": "inspect", "id": "@0.id", "resourceId": "@2.items.0.resourceId", "fields": ["/data"]},
            ]
            results = run({"requests": requests})["results"]
            first, second = results[1]["data"], results[2]["data"]
            require(first["total"] == second["total"] == 2 and first["truncated"]
                    and first["nextOffset"] == 1 and not second["truncated"], "pagination lost a cache output")
            inspections = [item["data"] for item in results[3:]]
            logical = [item for item in inspections if item.get("logicalId")]
            require(len(logical) == 1, "named and unnamed outputs collapsed")
            item = logical[0]
            require(item["name"] == "" and item["old"]["/data"]["maxMemoryMiB"] == str(before_memory)
                    and item["new"]["/data"]["maxMemoryMiB"] == str(after_memory), "logical output delta is incorrect")
            require(item["beforeOrigin"]["kind"] == item["afterOrigin"]["kind"] == "XR"
                    and item["afterOrigin"]["name"] == "checkout-app-cache", "logical origin was lost")
            return item["logicalId"]

        identity = logical_preview(1024, 2048)
        compared = run({"requests": [
            {"operation": "render", "source": "path:before"},
            {"operation": "render", "source": "path:after"},
            {"operation": "compare", "beforeId": "@0.id", "afterId": "@1.id"},
            {"operation": "query", "id": "@2.id", "query": CACHE_QUERY},
        ]})["results"]
        require(compared[0]["data"]["resourceCount"] == 51
                and compared[1]["data"]["resourceCount"] == 53, "nested inventories are incomplete")
        logical = [item for item in compared[3]["data"]["items"] if item.get("logicalId")]
        require(len(logical) == 1 and logical[0]["logicalId"] == identity and logical[0]["name"] == "",
                "cache restoration changed logical identity")

        # Authorized edits occur only in the temporary source, never desired YAML.
        platform = workspace / "after/environments/production/platform.yaml"
        source = platform.read_text()
        require(source.count("cacheGiB: 2") == 1, "ambiguous top-level source edit")
        platform.write_text(source.replace("cacheGiB: 2", "cacheGiB: 3"))
        require(logical_preview(1024, 3072) == identity, "top-level rerender changed output identity")

        function = workspace / "before/platform/function.yaml"
        text = function.read_text()
        require(text.count("name: templating") == 1, "ambiguous Function fixture")
        function.write_text(text.replace("name: templating", "name: absent-function"))
        failed = run({"operation": "render", "source": "path:before"}, failure=True)
        require(failed["error"]["code"] == "Incomplete", "missing Function was treated as a complete render")

    print("PASS: released four-XRD/Flux/Helm chain, logical identity, pagination, inspect, "
          "policy, compare/cache, source edit/rerender, missing Function, startup/request grants")


if __name__ == "__main__":
    main()
