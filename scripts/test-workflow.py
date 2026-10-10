#!/usr/bin/env python3
"""Exercise an explicitly supplied toolkit bundle against a temporary local fixture."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
IMAGE = "/spec/template/spec/containers/0/image"
PRIVATE = ("fixture-private-plaintext", "fixture-private-annotation", "Zml4dHVyZS1wcml2YXRl")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def success(response):
    require(response.get("schemaVersion") == "1", "unsupported response schema")
    require(response.get("status") == "success" and response.get("complete") is True,
            f"expected complete success: {response}")
    require(not response.get("error"), f"unexpected error: {response}")


def main():
    supplied = os.environ.get("GITOPS_PREVIEW_BINARY") or os.environ.get("FMP_BINARY")
    require(supplied, "set GITOPS_PREVIEW_BINARY to an existing compatible executable; no automatic install")
    binary = shutil.which(supplied)
    require(binary, f"supplied toolkit executable is not available: {supplied}")
    binary = str(Path(binary).resolve())

    with tempfile.TemporaryDirectory(prefix="gitops-preview-test-") as temporary:
        workspace = Path(temporary) / "workflow"
        shutil.copytree(ROOT / "fixtures/workflow", workspace)

        def run(request, failure=False, root=workspace, trusted=False):
            result = subprocess.run(
                [binary, "agent", "--root", str(root)] + (["--trusted"] if trusted else []),
                input=json.dumps(request), text=True, capture_output=True, timeout=120,
                cwd=temporary,
            )
            for private in PRIVATE:
                require(private not in result.stdout + result.stderr, "fixture secret leaked")
            try:
                response = json.loads(result.stdout)
            except json.JSONDecodeError as error:
                raise AssertionError(f"expected agent JSON; exit={result.returncode}, stderr={result.stderr}") from error
            if failure:
                require(result.returncode != 0, "operational failure must exit nonzero")
                require(response.get("schemaVersion") == "1", "unsupported failure schema")
                require(response.get("status") == "failure" and response.get("complete") is False,
                        f"expected failure, not an empty success: {response}")
                require(response.get("error", {}).get("code"), "missing failure code")
            else:
                require(result.returncode == 0, f"CLI failed: {result.stderr}")
                success(response)
                for item in response.get("results", []):
                    success(item)
            return response

        discovery = run({"operation": "discover"}, root=workspace / "before")["data"]
        require(discovery["profile"] == "local" and "1" in discovery["schemaVersions"], "wrong capabilities")
        require(discovery["paths"] == ["manifests"] and discovery["helm"], "wrong fixture roots")
        single = json.loads((ROOT / "examples/requests/render.json").read_text())
        rendered = run(single)["data"]
        require(rendered["resourceCount"] >= 2, "missing rendered fixture resources")
        expired = run({"operation": "query", "id": rendered["id"]}, failure=True)
        require(expired["error"]["code"] == "NotFound", "CLI handles must not survive process exit")

        batch = json.loads((ROOT / "examples/requests/preview-batch.json").read_text())

        def preview(expected_image):
            results = run(batch)["results"]
            diff, page, inspection, policy, budget = [item["data"] for item in results]
            require(diff["changed"] and diff["summary"]["modified"] >= 1, "missing image delta")
            require(page["total"] == 1 and not page["truncated"], "expected one matching deployment")
            resource = page["items"][0]
            require(resource["name"] == "destination" and resource["namespace"] == "apps", "wrong release identity")
            require(resource["action"] == "modified", "wrong change action")
            for origin_key in ("beforeOrigin", "afterOrigin"):
                for evidence in (resource, inspection):
                    origin = evidence[origin_key]
                    require((origin["kind"], origin["name"], origin["namespace"]) ==
                            ("HelmRelease", "origin", "flux-system"), "lost original HelmRelease provenance")
            require(inspection["old"][IMAGE] == "example.invalid/demo:1.0.0", "wrong old image")
            require(inspection["new"][IMAGE] == expected_image, "wrong new image")
            require(inspection["new"]["/spec/replicas"] == 2, "wrong replica count")
            require(policy["verdict"] == "failed" and policy["classificationCount"] >= 1,
                    "built-in image_update fail-on must fail without operational failure")
            require(budget["verdict"] == "passed", "declared resources should pass generous budget")

        preview("example.invalid/demo:2.0.0")

        requests = [
            {"operation": "render", "source": "path:before"},
            {"operation": "query", "id": "@0.id", "query": {"kind": "Secret"}},
            {"operation": "inspect", "id": "@0.id", "resourceId": "@1.items.0.resourceId"},
            {"operation": "inspect", "id": "@0.id", "resourceId": "@1.items.0.resourceId",
             "fields": ["/data/harmless", "/stringData/harmless"]},
            {"operation": "check", "id": "@0.id", "query": {"kind": "Deployment"}, "maxCPURequests": "1m"},
        ]
        results = run({"requests": requests})["results"]
        secret = results[2]["data"]["new"]
        require(secret["data"] == "[REDACTED]" and secret["stringData"] == "[REDACTED]", "Secret payload not redacted")
        require(all(value == "[REDACTED]" for value in results[3]["data"]["new"].values()), "projection bypasses redaction")
        require(results[4]["data"]["verdict"] == "failed", "tiny CPU budget should fail")

        # All source edits stay inside this disposable copy, never the repository.
        release = workspace / "after/manifests/release.yaml"
        source = release.read_text()
        require(source.count("example.invalid/demo:2.0.0") == 1, "ambiguous source edit")
        release.write_text(source.replace("example.invalid/demo:2.0.0", "example.invalid/demo:3.0.0"))
        preview("example.invalid/demo:3.0.0")

        comparison = run({"requests": [
            {"operation": "render", "source": "path:before"},
            {"operation": "render", "source": "path:after"},
            {"operation": "compare", "beforeId": "@0.id", "afterId": "@1.id"},
            {"operation": "check", "id": "@2.id"},
            {"operation": "release", "id": "@2.id"},
            {"operation": "release", "id": "@0.id"},
            {"operation": "release", "id": "@1.id"},
        ]})["results"]
        require(comparison[2]["data"]["changed"], "compare missed edit")
        require(comparison[3]["data"]["verdict"] == "failed", "compare lost policy")
        require(all(item["data"]["released"] for item in comparison[4:]), "release failed")

        run({"operation": "render", "source": "path:missing"}, failure=True)
        run({"operation": "render", "source": "path:before", "paths": ["missing"]}, failure=True)
        failed = run({"requests": [
            {"operation": "render", "source": "path:before", "paths": ["missing"]},
            {"operation": "discover"},
        ]}, failure=True)
        require(failed["failedIndex"] == 0 and len(failed["results"]) == 1, "batch did not stop at failure")

        # Exercise cluster-scoped identity through both direct diff and cache decode.
        policy_config = (
            "paths: [manifests]\nresolve-git: true\nhelm: true\npolicies:\n"
            "  builtin: [namespace_delete]\n  fail-on: [namespace_delete]\n"
        )
        for side in ("before", "after"):
            (workspace / side / ".fmp.yaml").write_text(policy_config)
        (workspace / "before/manifests/namespace.yaml").write_text(
            "apiVersion: v1\nkind: Namespace\nmetadata:\n  name: removed\n"
        )
        for initial in (
            [{"operation": "preview", "base": "path:before", "target": "path:after"}],
            [
                {"operation": "render", "source": "path:before"},
                {"operation": "render", "source": "path:after"},
                {"operation": "compare", "beforeId": "@0.id", "afterId": "@1.id"},
            ],
        ):
            index = len(initial) - 1
            handle = f"@{index}.id"
            results = run({"requests": initial + [
                {"operation": "query", "id": handle, "query": {"kind": "Namespace", "action": "deleted"}},
                {"operation": "inspect", "id": handle, "resourceId": f"@{index + 1}.items.0.resourceId"},
                {"operation": "check", "id": handle},
            ]})["results"]
            require(results[index]["data"]["summary"]["deleted"] == 1, "Namespace deletion lost from diff")
            page, inspection, policy = [item["data"] for item in results[index + 1:]]
            require(page["total"] == 1 and not page["truncated"], "Namespace deletion lost from query")
            resource = page["items"][0]
            require(resource["name"] == "removed" and not resource.get("namespace"), "wrong cluster-scoped identity")
            require(inspection["old"]["kind"] == "Namespace" and "new" not in inspection, "wrong deletion inspection")
            require(policy["verdict"] == "failed" and policy["classificationCount"] == 1,
                    "namespace_delete must return a completed failed verdict")

        before_config = workspace / "before/.fmp.yaml"
        before_config.write_text(policy_config + "ai:\n  enabled: true\n")
        ignored = run({"operation": "render", "source": "path:before"})
        require(any(item["code"] == "AIDisabled" for item in ignored["diagnostics"]), "missing ignored-AI diagnostic")
        before_config.write_text(policy_config + "sops-decrypt: true\n")
        for trusted in (False, True):
            discovery = run({"operation": "discover"}, root=workspace / "before", trusted=trusted)
            require(any(item["code"] == "SOPSDisabled" and item["severity"] == "warning"
                        for item in discovery["diagnostics"]), "missing SOPS discovery warning")
            denied = run({"operation": "render", "source": "path:before"}, failure=True, trusted=trusted)
            require(denied["error"]["code"] == "PermissionDenied", "SOPS-required rendering must fail even when trusted")

        invalid = run({"operation": "discover", "source": PRIVATE[0]}, failure=True)
        require(invalid["error"]["code"] == "InvalidInput", "operation-specific schema must reject source on discover")

    print("PASS: render/preview/query/inspect/check, provenance, redaction, edit/rerender, compare/release, "
          "namespace deletion, SOPS denial, AI diagnostic, sanitized validation, failures")


if __name__ == "__main__":
    main()
