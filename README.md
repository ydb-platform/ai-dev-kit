# YDB Skills

AI coding agent skills for [YDB](https://ydb.tech) — SDK code review, SQL/YQL assistance, and DevOps guidance.

## What's Inside

| Skill | Description |
|-------|-------------|
| **ydb-sdk** | Review code using YDB SDK for anti-patterns, performance issues, and incorrect usage. Covers Go, Python, Java, C++, C#, Terraform, CLI. |
| **ydb-sql** | Help write, optimize, and debug YQL/SQL queries. Schema design, SQL-to-YQL conversion. |
| **ydb-ops** | DevOps guidance: deployment, configuration, monitoring, troubleshooting. |

## Installation

### Claude Code (plugin)

Install as a Claude Code plugin for the full experience (skills + agents + slash commands):

```bash
claude plugin add https://github.com/ydb-platform/ai-dev-kit
```

This gives you:
- 3 auto-triggering skills
- 3 specialized agents (ydb-sdk, ydb-sql, ydb-ops)
- Slash commands: `/review`, `/sql`, `/ops`

### Any Coding Agent (universal installer)

Install skills for any supported agent using the installer script:

```bash
# Remote install — auto-detect agents
curl -fsSL https://ai.ydb.sh | bash

# Install for a specific agent
curl -fsSL https://ai.ydb.sh | bash -s -- --agent=cursor

# Install for multiple agents
curl -fsSL https://ai.ydb.sh | bash -s -- --agent=claude,copilot,gemini

# Install globally (user-level)
curl -fsSL https://ai.ydb.sh | bash -s -- --agent=claude --global

# See all options
curl -fsSL https://ai.ydb.sh | bash -s -- --help
```

### Local install (from cloned repo)

```bash
git clone https://github.com/ydb-platform/ai-dev-kit.git
cd ai-dev-kit

# Auto-detect agents in current project
./install.sh --detect

# Install for specific agent
./install.sh --agent=cursor

# Dry run — see what would be done
./install.sh --agent=claude --dry-run
```

### Supported Agents

| Agent | Project dir | Global dir |
|-------|-------------|------------|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Cursor | `.cursor/skills/` | — |
| Windsurf | `.windsurf/skills/` | — |
| GitHub Copilot | `.github/skills/` | `~/.copilot/skills/` |
| Codex CLI | `.agents/skills/` | `~/.codex/skills/` |
| Roo Code | `.roo/skills/` | — |
| Gemini CLI | `.gemini/skills/` | `~/.gemini/skills/` |
| Amp | `.agents/skills/` | `~/.config/agents/skills/` |
| Kiro | `.kiro/skills/` | — |
| Trae | `.trae/skills/` | — |
| Generic | `.agents/skills/` | `~/.agents/skills/` |

## Usage

### Claude Code Plugin

After installing the plugin, skills trigger automatically based on context:

```
> Review my Go code that uses ydb-go-sdk
  → triggers ydb-sdk skill

> Help me write a YQL query to get users by date range
  → triggers ydb-sql skill

> How do I set up YDB monitoring with Prometheus?
  → triggers ydb-ops skill
```

Slash commands for explicit invocation:

```
> /review src/db/
> /sql write a query to get active users with pagination
> /ops how to do a rolling restart
```

### Other Agents

After installing with `install.sh`, reference the skill in your prompt:

```
Review this code for YDB anti-patterns using the ydb-sdk skill.
```

The agent will load `SKILL.md` and follow the review workflow using reference files.

## Repository Structure

```
.claude-plugin/plugin.json    # Claude Code plugin manifest
agents/                        # Agent definitions (Claude Code)
  ydb-sdk.md                   # SDK code reviewer
  ydb-sql.md                   # SQL/YQL assistant
  ydb-ops.md                   # DevOps advisor
commands/                      # Slash commands (Claude Code)
  review.md                    # /review — SDK code review
  sql.md                       # /sql — YQL/SQL help
  ops.md                       # /ops — DevOps guidance
skills/                        # Skills (universal)
  ydb-sdk/
    SKILL.md                   # Review workflow
    references/                # 16 reference files (Go, Python, Java, C++, C#, Terraform, CLI)
    tests/                     # Test fixtures with intentionally bad code
  ydb-sql/
    SKILL.md                   # Query assistance workflow
    references/                # YQL syntax, optimization, schema design, SQL conversion
  ydb-ops/
    SKILL.md                   # Operations workflow
    references/                # Deployment, config, monitoring, troubleshooting
install.sh                     # Universal installer for all coding agents
```

## Supported Languages (ydb-sdk)

| Language | SDK | References |
|----------|-----|------------|
| Go | ydb-go-sdk | driver, query, topics |
| Python | ydb-python-sdk | driver, query, topics |
| Java | ydb-java-sdk / JDBC | driver, query, topics |
| C++ | ydb-cpp-sdk | driver, query |
| C# | Ydb.Sdk / ADO.NET | query |
| Terraform | yandex_ydb_table | HCL resources |
| CLI | ydb commands | shell scripts |

## License

Apache-2.0
