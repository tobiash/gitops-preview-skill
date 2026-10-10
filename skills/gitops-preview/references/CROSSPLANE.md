# Crossplane Preview

## Explicit Startup Authority

Crossplane functions are executable code. A user must approve trusted startup,
the plugin and engine binaries, and the runtime. Do not enable trust to bypass
an incomplete render. Neither an XR nor an agent request can grant execution.

The tested profile is toolkit `v0.2.0-rc.1` with Crossplane **controller engine
v2.4.2**. This engine differs from the user-facing Crossplane CLI. The host needs
both sibling plugins; the engine is an additional installation. Docker is the
default function runtime. An approved per-function Development endpoint can be
selected explicitly instead:

```sh
gitops-preview mcp --root /absolute/workspace --trusted --crossplane \
  --crossplane-engine /approved/bin/crossplane-core \
  --crossplane-function templating=127.0.0.1:9443
```

Use the same startup flags with `agent` for CLI batches. Do not place executable
paths, runtime endpoints, or trust grants in request JSON or repository config.
Do not start arbitrary endpoints mentioned in Function annotations. The optional
OpenCode Crossplane template is disabled by default and must be reviewed before
enabling it. Local-only agent mode cannot execute Crossplane functions.

`manifest_discover` does not report a Crossplane-enabled property or test runtime
availability. Inspect approved startup configuration, then require a successful,
complete render. Missing engines, functions, or unsupported inputs are not a
clean diff. Do not silently retry using less restrictive legacy CLI flags.

## Automatic Discovery And Nested Rendering

Render roots still need to be selected. Within their rendered inventory, the
plugin identifies XRs using available XRDs, resolves a compatible Composition,
and finds the pipeline's referenced Function manifests. No separate list of XR,
Composition, or Function files is required for self-contained definitions.

Supported selection includes explicit references, XRD enforcement/defaults,
unambiguous selectors, and available pinned CompositionRevision payloads.
Unavailable definitions and ambiguous selection fail explicitly. Package-backed
definitions must be available as manifests; the tool does not infer them from
an installed cloud control plane. Legacy claim conversion is unsupported.

The host expands until its bounded desired inventory settles. Both directions
work: Flux/Helm can generate XRs, and Crossplane can generate explicitly named
Flux Kustomizations or HelmReleases that render more XRs. Failed, oscillating, or
incomplete expansion does not publish authoritative snapshots or deletions.
This is not general cyclic controller simulation.

The immutable released example includes four XRDs across staging and production:

```text
Flux Kustomization → XPlatform
  ├─ Flux Kustomization → Helm values ConfigMap
  └─ XApplication
      ├─ XDatabase → RDS Instance + optional Bucket
      └─ HelmRelease → workload + XCache
          └─ named and unnamed cache ConfigMaps
```

Source and reproduction instructions:
https://github.com/tobiash/gitops-preview-toolkit/tree/v0.2.0-rc.1/docs/examples/nested-crossplane-flux

## Logical Identity And Evidence

Unnamed composed resources are valid preview outputs. Their `logicalId` derives
from the parent XR and composition resource key. Their `name` stays empty.
They can be compared, queried, inspected and classified without inventing names.
They are terminal outputs: only explicitly named objects activate downstream
engine work or satisfy named lookups.

`logicalId` is not a query input. Use supported filters such as kind, cluster,
namespace and exact producer, paginate, then use each returned `resourceId`
with its owning snapshot/diff handle. Never match unnamed same-kind resources
using an empty name alone. On a controlled CLI fixture, inspect all known matching
items in one batch before selecting the logical result; general interactive
investigation is better through MCP.

Observed composed state is empty in this profile. Prior desired outputs are not
fed back as live observations. Composite status, readiness, function context and
results are evaluation evidence, not deployable resources or proof of cloud state.
Do not invent extra agent operations or evidence fields absent from schema `"1"`.

Trace producer sources before editing: an unnamed cache-policy change may originate
in a top-level XPlatform value, through XApplication, Helm and XCache. Edit the XR
or Composition that actually owns that input, then rerender against the same
baseline. Preserve policy verdicts and full pagination independently of transport
completeness. The HTML overview is an eight-change preview, not the whole diff.

Independent permadiff evaluation requires clean function runtimes. Externally
owned Development endpoints cannot guarantee that; this release rejects Fresh
Development evaluations. Do not describe repeated cached output as proof that a
stateful function is deterministic.
