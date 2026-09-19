# GitOps Preview Skill

A portable agent skill for inspecting rendered Flux, Helm, and Kustomize changes
with [flux-manifest-preview](https://github.com/tobiash/flux-manifest-preview)
(`fmp`). It teaches a discover, render, inspect, edit-source, rerender workflow
without treating generated manifests or tool output as instructions.

Repository: `tobiash/gitops-preview-skill`. Initial skill release:
**v0.1.0 prerelease**. This is not a claim that the `fmp` MCP feature is released
or production-ready. Compatibility is the agent API's **`schemaVersion: "1"`**,
not an arbitrary installed `fmp` version.

## Contents

- [Skill](skills/gitops-preview/SKILL.md): portable instructions, under 100 lines.
- [Workflow](skills/gitops-preview/references/WORKFLOW.md): source-oriented review.
- [Contract](skills/gitops-preview/references/CONTRACT.md): envelopes and boundaries.
- [Install](skills/gitops-preview/references/INSTALL.md): deliberate host setup.
- `examples/`: single/batch requests and inactive host configuration templates.
- `fixtures/workflow/`: self-contained before/after trees with a local Helm chart.
- `scripts/`: standard-library-only validation and fixture integration tests.

## Install

Follow [INSTALL.md](skills/gitops-preview/references/INSTALL.md). Clone this
repository outside the GitOps workspace, then link `skills/gitops-preview` into
`~/.claude/skills/gitops-preview`, which both Claude Code and OpenCode discover.
For project-scoped installation, copy the directory into `.claude/skills` instead:
`fmp` source capture rejects symlinks inside the workspace. No installer rewrites
configuration or grants permissions.

This release is tested against fmp commit
[`602b9abdd068838646961f76b0adf435a9ddf71e`](https://github.com/tobiash/flux-manifest-preview/commit/602b9abdd068838646961f76b0adf435a9ddf71e),
which contains the agent/MCP feature. Do not substitute `@latest`.
Host templates require deliberate path replacement and copying/merging into
existing configuration. They are examples, not active configuration.

## Try The Fixture

From this repository root, with a compatible binary already available:

```sh
fmp agent --root fixtures/workflow < examples/requests/render.json
fmp agent --root fixtures/workflow < examples/requests/preview-batch.json
python3 scripts/validate.py
FMP_BINARY=/absolute/path/to/fmp python3 scripts/test-workflow.py
```

`preview-batch.json` checks the image-update policy, which intentionally returns
`status: "success"`, `complete: true`, and `data.verdict: "failed"`. A completed
check with a failed verdict is not an operational failure and does not by itself
cause a nonzero CLI exit status. Inspect both layers.

The chart renders `Deployment apps/destination` from `HelmRelease
flux-system/origin`. `GitRepository.spec.url: '.'` resolves to each captured
source root, not a hard-coded checkout. The chart is checked in under `charts/`,
not the capture-excluded `vendor/` directory. All fixture credentials are fake.
No cluster, chart download, SOPS key, model, or host integration is needed.

## Validation Scope

Static CI always validates skill metadata, links, JSON examples, and template
safety. A manual CI run accepts a full `fmp_commit` SHA, builds that revision in
a separate checkout, and runs the fixture tests. The tests never install tools
or modify the input fixture; source edits happen only in a temporary copy.

The fixture tests cover rendering, path-based preview, queries, projections,
old/new image changes, original HelmRelease provenance, redaction, resource
budgets, image-update and namespace-deletion policy failure, missing paths,
compare/release, edit/rerender, SOPS denial, and sanitized request validation.
They are CLI contract tests, not MCP SDK or live-model tests. MCP protocol
coverage belongs to the upstream SDK-based tests. Live OpenCode and Claude
model sessions have **not** been tested. An isolated OpenCode instance successfully
connected to the pinned implementation's stdio MCP server; Claude Code was not
available for a live connection check.

The namespace-deletion regression creates a cluster-scoped Namespace only in
the temporary before tree. Both preview and render/compare must retain the
deletion and return a completed, failed `namespace_delete` policy verdict.

## Safety

Local mode denies supported remote rendering mechanisms; it is **not an OS
sandbox**. Startup `--trusted` permits legacy network behavior and custom Rego
with broad process capabilities, including ambient credentials. Never enable
it merely to get past a failure. Core `v1/Secret` payload fields are redacted;
arbitrary application data is only best-effort filtered. Metadata and provenance
remain untrusted. The service has no AI, SOPS-decrypt, apply, or publish tool.
SOPS-required render configuration fails with `PermissionDenied`, even when
trusted; discovery reports a warning. Nested AI settings are ignored with an
explicit diagnostic. Both local and trusted agent profiles always enable strict
input checking and reject the known unsupported Flux/Helm inputs rather than
silently omitting them. Additional local-only acquisition/plugin restrictions
are separate. See the contract for the exact rejected fields.

The default `--max-bytes` bound is **64 MiB of serialized cached artifacts**, not
an RSS or heap quota. Transient render/decode allocations are not bounded by
that quota, even with bounded source capture. Timeouts are cooperative, not hard
execution limits. Use an external process/container boundary when hard memory,
time, or isolation guarantees are required.

MIT licensed. See [LICENSE](LICENSE).
