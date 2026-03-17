# Skills

Custom agentic skills, agents, and prompts for development workflows.

## Quick Start

Install all skills, agents, and prompts to `~/.skills`:

```bash
npx skills
```

## Commands

| Command | Description |
|---|---|
| `npx skills` | Install everything to `~/.skills` |
| `npx skills install` | Same as above |
| `npx skills install ./path` | Install to a custom directory |
| `npx skills list` | List available skills, agents, and prompts |
| `npx skills help` | Show help |

## Repository Structure

```
Skills/
├── skills/          # Reusable agentic skills
├── agents/          # Pre-configured agents
├── prompts/         # Prompt templates
├── bin/
│   └── skills.js    # CLI installer (npx skills)
└── index.js         # Programmatic API
```

## Available Skills

| Name | Description |
|---|---|
| `code-review` | Review code for correctness, security, and style |
| `summarize` | Summarize text, documents, or conversations |

## Available Agents

| Name | Description |
|---|---|
| `dev-assistant` | General-purpose software development assistant |

## Available Prompts

| Name | Description |
|---|---|
| `code-review` | Template for requesting a structured code review |
| `commit-message` | Generate a Conventional Commits-style commit message |

## Adding New Skills

Drop a `.md` file into the appropriate directory:

- **`skills/`** – Skill definitions (capabilities an agent can use)
- **`agents/`** – Agent configurations (system prompt + tools + capabilities)
- **`prompts/`** – Reusable prompt templates

## Programmatic Usage

```js
const { skills, agents, prompts } = require('skills');

console.log(Object.keys(skills));   // ['code-review', 'summarize']
console.log(Object.keys(agents));   // ['dev-assistant']
console.log(Object.keys(prompts));  // ['code-review', 'commit-message']
```

## License

MIT
