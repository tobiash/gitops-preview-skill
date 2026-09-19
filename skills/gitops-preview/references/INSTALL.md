# Deliberate Installation

These instructions do not install or overwrite anything automatically. Review
the source and choose the workspace before running commands. Skill version
v0.1.0 is a prerelease; agent API compatibility is schemaVersion `"1"`.

## Binary Prerequisite

This skill release is tested against the immutable fmp commit
`602b9abdd068838646961f76b0adf435a9ddf71e`, containing agent and MCP support.
Do not use `@latest`: released binaries may not contain this feature.

```sh
FMP_COMMIT='602b9abdd068838646961f76b0adf435a9ddf71e'
go install "github.com/tobiash/flux-manifest-preview/cmd/fmp@${FMP_COMMIT}"
fmp agent schema
```

Use Go 1.26.3 or later, as required by that revision. Alternatively build a reviewed
checkout manually and use its absolute binary path. Neither test script installs
software or changes host configuration. An old binary that reports unknown
command `agent` is incompatible, not a reason to fall back to legacy commands.

## Skill Discovery

Clone the repository into a location you manage outside
the GitOps workspace to be captured:

```sh
git clone https://github.com/tobiash/gitops-preview-skill.git
```

Optionally select a reviewed published tag or commit. For user-level discovery,
create the skills parent if needed and link the skill using the actual clone path:

```sh
mkdir -p "$HOME/.claude/skills"
ln -s /absolute/path/to/gitops-preview-skill/skills/gitops-preview "$HOME/.claude/skills/gitops-preview"
```

Do not replace an existing skill directory silently. Both hosts support the
user-level location. Keep it outside the selected `fmp --root`: source capture
rejects all symlink entries, including project-local skill links. Do not bind
the service to your entire home directory.

For project-scoped discovery, Windows, or where symlinks are unsuitable,
deliberately copy the entire `skills/gitops-preview` directory (including
references and the bundled `LICENSE`) into the project's
`.claude/skills/gitops-preview` instead. Both
hosts support this project location; external-skill discovery must not be
disabled in OpenCode. Keep copied versions under deliberate update control.

## Host MCP Templates

The repository's `examples/hosts/opencode.json.example` and
`examples/hosts/claude.mcp.json.example` are **inactive examples**. They contain
no secrets, trusted flag, or automatic permission grants. Replace executable
and workspace placeholders with absolute paths. Manually merge the relevant
server entry into existing configuration; never overwrite unrelated settings.

For OpenCode use `opencode.json` or `opencode.jsonc`. Local MCP configuration
uses `mcp.<name>.type: "local"` and a command array containing executable and
arguments. Quit and restart OpenCode after deliberately changing configuration
or skill files; the current session retains its loaded configuration.

For Claude Code use project `.mcp.json`, with `mcpServers.<name>`, `type:
"stdio"`, a command string, and an args array. Start a new session, review the
project server approval prompt, and inspect `/mcp` status. Do not bypass approval.

On either host, verify `manifest_discover` reports the selected root's expected
configuration, profile `local`, and schemaVersions containing `"1"` before
rendering. Tool display names may be prefixed by the host/server name.
Do not add `--trusted` to resolve missing remote dependencies without a separate
trust decision: it enables legacy network and custom Rego capabilities with
access to ambient credentials. Local restriction is not an OS sandbox.

Official configuration references:

- https://opencode.ai/docs/mcp-servers/
- https://opencode.ai/docs/skills/
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/skills

## Smoke Tests

From the skill repository, run `python3 scripts/validate.py` and
`FMP_BINARY=/absolute/path/to/fmp python3 scripts/test-workflow.py`.
The latter needs no Git initialization, network chart access, cluster, or model.
MCP SDK protocol tests are upstream. An isolated OpenCode instance successfully
connected to the pinned stdio server. Live OpenCode/Claude model tests have not
been performed, and Claude Code was unavailable for a connection smoke test.
Successful CLI tests alone do not certify host integration.
