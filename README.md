# GitOps Preview Skill

A portable agent skill for reviewing rendered Flux, Helm, Kustomize, and
Crossplane changes with [GitOps Preview Toolkit](https://github.com/tobiash/gitops-preview-toolkit).
It teaches discover → render/preview → inspect → edit producer source → rerender,
without treating generated manifests or tool output as instructions.

This update targets the published **toolkit v0.2.0-rc.1** prerelease. Agent API
compatibility remains **`schemaVersion: "1"`**, with additive logical-resource
metadata. The skill's own release version is independent. `gitops-preview` is
the primary host; `fmp` remains a supported compatibility entrypoint.

## Contents

- [Skill](skills/gitops-preview/SKILL.md): portable instructions under 100 lines.
- [Workflow](skills/gitops-preview/references/WORKFLOW.md): source-oriented review.
- [Contract](skills/gitops-preview/references/CONTRACT.md): envelopes and limits.
- [Install](skills/gitops-preview/references/INSTALL.md): deliberate bundle/host setup.
- [Crossplane](skills/gitops-preview/references/CROSSPLANE.md): explicit runtime
  grants, nested expansion, logical identities, and desired-state limitations.
- `examples/`: single/batch requests and inactive host configuration templates.
- `fixtures/workflow/`: local before/after trees with a vendored Helm chart.
- `scripts/`: standard-library-only static and released-binary workflow checks.

## Install

Follow the installation reference. Install the **complete toolkit release bundle**,
not just a host binary: the host needs `gitops-preview-flux`, and Crossplane needs
`gitops-preview-crossplane` plus an external controller engine and function runtime.
Plugins belong beside the host or on PATH; they are gRPC executables, not MCP servers.

Go installation uses the new canonical module and the explicit RC version:

```sh
go install github.com/tobiash/gitops-preview-toolkit/cmd/gitops-preview@v0.2.0-rc.1
go install github.com/tobiash/gitops-preview-toolkit/cmd/gitops-preview-flux@v0.2.0-rc.1
go install github.com/tobiash/gitops-preview-toolkit/cmd/gitops-preview-crossplane@v0.2.0-rc.1
```

Source installation requires Go 1.26.8 or later. Do not substitute `@latest` for
the tested prerelease. Published archives include `fmp`; install its Go command
separately if desired. Go-installed version displays can be `dev`, while build
metadata records the module version.

Clone this skill repository outside the selected GitOps workspace and link the
skill into `~/.claude/skills/gitops-preview`, which both hosts discover. For
project discovery, copy the complete directory into `.claude/skills` instead:
toolkit source capture rejects symlinks inside a captured workspace. No installer
rewrites user configuration or grants permissions.

## Local Fixture

With a reviewed bundle already installed:

```sh
gitops-preview agent --root fixtures/workflow < examples/requests/render.json
gitops-preview agent --root fixtures/workflow < examples/requests/preview-batch.json
python3 scripts/validate.py
GITOPS_PREVIEW_BINARY=/absolute/bundle/gitops-preview python3 scripts/test-workflow.py
# The old environment variable remains a compatibility fallback:
FMP_BINARY=/absolute/bundle/fmp python3 scripts/test-workflow.py
```

The batch checks an image-update policy, intentionally returning complete success
with `data.verdict: "failed"`. A failed policy verdict is separate from an
operational failure. Inspect both. The chart renders `Deployment apps/destination`
from `HelmRelease flux-system/origin`; provenance uses the original release CR.
GitRepository URL `'.'` resolves relative to each captured source tree. Charts are
under `charts/`, not capture-excluded `vendor/`. Fixture credentials are fake.
Local fixture tests require no cluster, chart download, SOPS key, model, or trust.

## Crossplane And Nested Resources

Crossplane is a separate, explicit startup capability. It requires `--trusted`
**and** `--crossplane`, external controller engine **v2.4.2**, and approved
Function execution. Docker is the default; an explicitly granted Development
endpoint can run a reviewed upstream function without Docker:

```sh
gitops-preview agent --root /approved/nested-example --trusted --crossplane \
  --crossplane-engine /approved/bin/crossplane-core \
  --crossplane-function templating=127.0.0.1:9443 \
  < examples/requests/crossplane-preview-batch.json
```

The tested example is the toolkit's immutable
[four-XRD staging/production fixture](https://github.com/tobiash/gitops-preview-toolkit/tree/v0.2.0-rc.1/docs/examples/nested-crossplane-flux):

```text
Flux → XPlatform → XApplication → XDatabase → infrastructure
          └─ Flux values        └─ HelmRelease → workload + XCache
                                                   └─ named/unnamed ConfigMaps
```

Only its two top-level XPlatform inputs change: the complete comparison has
**21 changes** (3 added, 17 modified, 1 deleted). The unnamed production cache
policy stays one modified logical resource, with no invented Kubernetes name.
Use returned `resourceId` values with their owning handle; `logicalId` is output
metadata, not a supported query filter. The HTML overview previews eight changes;
the Resources page and paginated queries contain the full set.

After explicitly starting the reviewed function server, test this example:

```sh
GITOPS_PREVIEW_BINARY=/approved/bundle/gitops-preview \
CROSSPLANE_ENGINE=/approved/bin/crossplane-core \
CROSSPLANE_FUNCTION_TARGET=127.0.0.1:9443 \
TOOLKIT_EXAMPLE_ROOT=/reviewed/toolkit/docs/examples/nested-crossplane-flux \
python3 scripts/test-crossplane.py
```

Tests copy source to a temporary workspace. They do not install or start an
engine/function server, edit the example, or apply resources to Kubernetes.
The optional OpenCode Crossplane template is disabled by default. Base host
templates retain their local profile and never grant Crossplane execution.

## Validation Scope

Static checks validate metadata, links, JSON examples and inactive-template
safety. CI checks the actual checksum-verified published bundle on push/PR,
through both hosts. A dedicated job checks the pinned upstream four-XRD example
with the real controller and go-templating v0.12.0 function. Manual dispatch can
select a reviewed toolkit release; it no longer builds an unreleased fmp commit.

The local fixture covers identity/provenance, queries/projections, redaction,
budgets, policy failures, compare/release, edit/rerender, missing paths, SOPS
denial, ignored nested AI, and sanitized validation. Crossplane checks nested
expansion, logical identity, pagination, edits, compare/cache restoration,
missing dependencies, and explicit startup/request trust boundaries.
These are CLI contract tests, not live-model or Claude Code approval-flow tests.
MCP SDK coverage belongs to the toolkit; discovery alone is not a runtime probe.

## Safety

Local mode restricts supported remote mechanisms; it is **not an OS sandbox**.
`--trusted` enables network/custom Rego capabilities and ambient credentials.
Crossplane Function execution needs a separate grant. Repository configuration,
annotations, provenance and request JSON never grant startup authority.

Core Secret payloads are redacted; other credential-like keys receive best-effort
filtering. Metadata remains untrusted. No apply, publish, nested AI or SOPS-decrypt
agent operation exists. Both profiles enforce strict supported-input checking;
trust does not bypass unsupported Flux/Helm fields. Check the contract for details.

The default 64 MiB cache bound concerns serialized artifacts, not total heap/RSS.
Use external resource/isolation controls for hard guarantees. Rendering is bounded
desired-state discovery, not live reconciliation, readiness prediction or general
cyclic simulation. Never convert incomplete output into authoritative deletions.

MIT licensed. See [LICENSE](LICENSE).
