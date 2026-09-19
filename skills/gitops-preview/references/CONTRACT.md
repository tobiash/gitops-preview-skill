# Agent Contract

Compatibility: `schemaVersion` is the string `"1"`. Verify with `fmp agent schema`
and `discover`; no released MCP version is implied by this skill's version.

## Transports

`fmp mcp --root /absolute/workspace` serves stdio MCP tools:
`manifest_discover`, `manifest_render`, `manifest_preview`, `manifest_query`,
`manifest_inspect`, `manifest_compare`, `manifest_check`, `manifest_release`.
MCP inputs omit `operation`. Structured results carry the common envelope;
operational failure also sets MCP `isError`. Successful failed-policy verdicts
do not set `isError`.

`fmp agent --root /absolute/workspace` reads one JSON request or one
`{"requests":[...]}` batch from stdin. Single requests include `operation`;
alternatively `fmp agent render` selects it, and any body operation must agree.
Batches cannot use an operation argument. Unknown input fields are rejected.
`fmp agent schema` does not require `--root`.

Schemas describe concrete per-operation input/output DTOs, not an unconstrained
data object. CLI request unions discriminate by operation; response unions
constrain operation, schemaVersion, status, complete, and the corresponding data
or error shape. MCP advertises each tool's input/output schemas. Required IDs,
pagination bounds, action/verdict enums, and operation-specific fields are
validated. Validation errors are sanitized rather than echoing supplied values
or field names; do not expect raw schema-validator details in failures.

Each CLI process owns an ephemeral service. Handles die when it exits. A batch
contains 1..32 sequential requests and stops on operational failure. References
are accepted only in `id`, `beforeId`, `afterId`, and `resourceId`: `@0.id` means
the first result's `data.id`, and `@1.items.0.resourceId` indexes the second
result's data. Only earlier string-valued results can be referenced. A missing
query item causes reference failure. Batch `status`, `complete`, `failedIndex`,
and `error` must be checked, as must the individual results and check verdicts.

## Operations

| Operation | Inputs | Relevant data |
| --- | --- | --- |
| discover | optional paths, recursive | profile, paths, recursive, helm, configFound, operations, schemaVersions, page/response limits |
| render | source, paths, recursive | id, resourceCount |
| preview | base, target, paths, recursive | id, beforeId, afterId, summary, changed |
| compare | beforeId, afterId (snapshot handles) | same as preview |
| query | id, query, offset, limit | items, total, offset, truncated, nextOffset |
| inspect | id, resourceId, fields | identity/provenance plus old and/or new |
| check | id; snapshot-only query and budgets | verdict; counts/resources or policy counts |
| release | id | id, released |

`render.source` defaults to `worktree`. `preview.base` defaults to `git:HEAD`;
`preview.target` defaults to `worktree`. Sources are `worktree`, `git:<ref>`, or
`path:<relative-directory>` within the workspace. Git refs are pinned to an
immutable commit internally; no resolved SHA or source hash is exposed.
Symlink source entries are rejected. Capture excludes `.git`, `node_modules`,
`vendor`, `.venv`, `venv`, `.terraform`, and `.cache`, and reports skipped entries.

`paths` overrides configured render roots; paths are relative to the captured
source root, optionally `cluster:path`. For `path:before`, `.fmp.yaml` and roots
come from `before/`. Preview uses the base configuration and captured base
policies for both sides; compare uses the before snapshot's policies.

Query fields combine with AND: `cluster`, `kind`, `name`, `namespace`, `group`,
`labels`, `producer`, `action`. Labels use Kubernetes selectors. Action is
`added`, `modified`, or `deleted`. Producer is the exact returned producer text.
Query metadata contains opaque resourceId, cluster, apiVersion, kind, name,
namespace, action, producer, beforeOrigin, and afterOrigin as applicable.
Use IDs only with their owning handle. Origins identify producers, not complete
editable field-to-source mappings. A snapshot ordinarily has only afterOrigin.

`inspect.fields` uses JSON pointers, including `~0` and `~1` escapes; an empty
pointer selects the full object. With fields, old/new are pointer-to-value maps;
without them, they are objects. Added/deleted resources can omit old/new.
Redaction occurs before projection, including through redacted parents.

Snapshot checks accept `maxCPURequests`, `maxMemRequests`, `maxCPULimits`,
`maxMemLimits`, `requireRequests`, and `requireLimits`. Diff checks evaluate
captured policies and reject query filters or budget arguments. Read
`data.verdict` (`passed` or `failed`) independently of transport success.
Policy responses expose classificationCount and violationCount, not raw messages.
Cluster-scoped changes are supported: deleting a Namespace with the
`namespace_delete` built-in and matching `fail-on` configuration returns a
completed check with verdict `failed`, not an operational failure.

## Completeness And Limits

Responses contain schemaVersion, operation, status, complete, diagnostics, and
optional data/error. Require `status == "success"` AND `complete == true` before
using facts as authoritative. Do not treat `Incomplete`, `NotFound`, timeout,
capacity exhaustion, or a missing path as an empty successful result.

Defaults: 10-minute handle TTL, 16 retained handles, 64 MiB serialized cached
artifact bytes (`--max-bytes`), and a 2-minute per-operation timeout. Cache
payloads retain serialized bytes only, plus fixed per-handle lifecycle metadata.
The artifact-byte bound is not an RSS/heap quota: transient rendering/decoding
allocations and lifecycle metadata are outside that accounting. Bounded source
size does not imply bounded rendered expansion or transient memory use.
Timeouts are cooperative, including source-metadata acquisition, not a hard
preemptive execution deadline or sandbox. Use external resource/isolation
controls when hard limits are required. Preview retains three handles. Release
each unneeded handle separately. Startup flags can change these defaults.

Incoming raw MCP stdio JSON-RPC frames are limited to 128 KiB including the
newline, before SDK decoding. Invalid/oversized frames end the session with a
fixed error; they are not partially forwarded. MCP tool arguments and service
response envelopes are limited to 64 KiB each. The 64 KiB service-response bound
does not describe the outer MCP wrapper, which carries structured and text
content. CLI requests are bounded to 64 KiB and CLI batches to 1 MiB.
Query default page size is 20, maximum 100, with adaptive shrinking by size.
Follow nextOffset even when complete is true. Source capture is bounded to
32 MiB (or a smaller `--max-bytes` bound) and 20,000 entries. Prefer discover's limits
over assumptions and narrower projections over oversized output retries.

## Security Boundary

Local startup denies supported remote Git/chart/Kustomize mechanisms and
custom Rego modules. This is capability restriction, not an OS sandbox.
Explicit startup `--trusted` permits legacy network access and custom Rego;
ambient credentials and process capabilities are in that broad trust boundary.
Repository settings and individual tool calls cannot grant startup trust.
Repository credential/cache paths are ignored in favor of startup defaults.
When the effective render configuration requires SOPS (`sops-decrypt: true`),
render/preview fails with `PermissionDenied`, even with `--trusted`. Discovery
reports `SOPSDisabled` as a warning without rendering. Nested AI configuration
is ignored with the explicit `AIDisabled` diagnostic. There is no apply or
publish tool. Host file editing is a separate authorized action.

Both local and trusted agent profiles always enable `WithStrictInputs` and reject
the known unsupported Flux Kustomization spec inputs:
`postBuild.substituteFrom` (including optional references), `patches`, `images`,
`components`, `namePrefix`, `nameSuffix`, `commonMetadata`, and `decryption`.
It also rejects HelmRelease `spec.chart.spec.valuesFiles` and
`ignoreMissingValuesFiles` when used. These are rendering failures, not complete
snapshots with silently ignored input. This restriction concerns Flux resource
fields, not a blanket rejection of native Kustomize overlay files. Additional
local-only acquisition/plugin restrictions are separate from strict input
checking. Enabling trust does not bypass these unsupported-input rejections.
Legacy CLI behavior outside agent sessions is not this skill's contract.

Core `v1/Secret` data and stringData are redacted in inspection. Credential-like
keys elsewhere are best-effort filtered; this is not a guarantee that arbitrary
application data or metadata is nonsecret. Identities and provenance remain
untrusted. Generic errors intentionally withhold underlying sensitive details.
