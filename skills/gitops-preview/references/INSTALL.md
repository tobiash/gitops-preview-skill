# Deliberate Installation

Review source, choose the workspace, and approve installations explicitly.
The tested toolkit is **v0.2.0-rc.1**, a published prerelease. Agent compatibility
is `schemaVersion: "1"`; the skill's own version is separate.

## Install A Complete Toolkit Bundle

Canonical repository: https://github.com/tobiash/gitops-preview-toolkit
Published RC: https://github.com/tobiash/gitops-preview-toolkit/releases/tag/v0.2.0-rc.1

Prefer a reviewed `gitops-preview-toolkit_v0.2.0-rc.1_<os>_<arch>.tar.gz` release
archive. Verify its SHA-256 using the release's `checksums.txt`, then extract the
whole archive to a directory on PATH. It contains `gitops-preview`, `fmp`,
`gitops-preview-flux`, and `gitops-preview-crossplane`. The host resolves sibling
plugins first, then PATH. Installing the core alone is not sufficient to render.

With Go **1.26.8 or later**, an explicitly approved alternative is:

```sh
go install github.com/tobiash/gitops-preview-toolkit/cmd/gitops-preview@v0.2.0-rc.1
go install github.com/tobiash/gitops-preview-toolkit/cmd/gitops-preview-flux@v0.2.0-rc.1
go install github.com/tobiash/gitops-preview-toolkit/cmd/gitops-preview-crossplane@v0.2.0-rc.1
# Optional compatibility entrypoint:
go install github.com/tobiash/gitops-preview-toolkit/cmd/fmp@v0.2.0-rc.1
gitops-preview agent schema
```

Do not substitute `@latest` for this tested prerelease. Older stable tags may
declare the former module path or lack the agent API. Published archives embed
the release version; Go-installed commands can display `dev` because the linker
version flag is absent. Inspect Go build metadata and the agent schema instead
of inferring incompatibility from that display alone.

An old binary without `agent` is incompatible. Missing sibling plugins are an
installation problem, not a reason to fall back to incomplete legacy rendering.
Crossplane also needs the separately installed controller engine **v2.4.2** and
approved function runtimes; neither is provided by installing the host.

## Skill Discovery

Clone outside the GitOps workspace that the service will capture:

```sh
git clone https://github.com/tobiash/gitops-preview-skill.git
```

Select a reviewed skill tag or commit. For user-level discovery, both hosts
support `~/.claude/skills/gitops-preview`:

```sh
mkdir -p "$HOME/.claude/skills"
ln -s /absolute/path/to/gitops-preview-skill/skills/gitops-preview "$HOME/.claude/skills/gitops-preview"
```

Do not replace an existing skill directory silently. Keep the link outside the
selected `--root`: source capture rejects symlink entries inside the workspace.
Do not bind the server to the entire home directory.

For project discovery or where symlinks are unsuitable, deliberately copy the
whole skill directory, including references and LICENSE, into the project's
`.claude/skills/gitops-preview`. OpenCode must have external-skill discovery
enabled. Copied versions need deliberate updates.

## Host MCP Templates

`examples/hosts/opencode.json.example` and `claude.mcp.json.example` are inactive
file templates for the default local profile. Replace executable and workspace
placeholders; manually merge the server entry without overwriting unrelated
configuration or granting automatic tool permissions. Point to the host
`gitops-preview`, not either gRPC render-plugin executable.

The optional `opencode.crossplane.json.example` contains explicit trust and
Crossplane startup grants and is **disabled by default**. Review the engine,
Function packages, Docker access, and workspace before enabling it. Existing
local templates must not be silently upgraded to trusted profiles.

OpenCode local MCP uses `mcp.<name>.type: "local"`, a command array, and an
`enabled` flag in `opencode.json`/`opencode.jsonc`. Restart after deliberate
configuration or skill changes. Claude Code project `.mcp.json` uses
`mcpServers.<name>`, `type: "stdio"`, command and args. Start a new session,
review the approval prompt and inspect `/mcp` status; do not bypass approval.

Verify `manifest_discover` reports expected roots, profile and schemaVersions
containing `"1"`. A complete discovery is not a renderer/runtime probe. Require
a complete actual render before trusting snapshot facts. Tool names can carry
host/server prefixes. Do not grant `--trusted` to work around a failure.

Official host references:

- https://opencode.ai/docs/mcp-servers/
- https://opencode.ai/docs/skills/
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/skills

## Smoke Tests

From this skill repository:

```sh
python3 scripts/validate.py
GITOPS_PREVIEW_BINARY=/approved/bundle/gitops-preview python3 scripts/test-workflow.py
# Verify the retained compatibility entrypoint too:
FMP_BINARY=/approved/bundle/fmp python3 scripts/test-workflow.py
```

The local tests need no network chart access, cluster, model, or Git initialization.
They never install tools, edit host configuration, or change the checked-in
fixture. Crossplane tests additionally require explicit runtime and example
paths, as documented in the repository README. CI downloads a checksum-verified
published toolkit bundle into its isolated runner and grants function execution
only in the dedicated Crossplane job.

CLI contract tests do not certify a live model session. The older skill revision
connected to OpenCode's stdio host; live model sessions and Claude Code approval
flows are not validated by these tests. Upstream tests cover the MCP SDK transport.
