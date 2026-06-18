# Contributing

Contributions are welcome. This document covers the basics.

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Set up the environment: `uv sync`
4. Make your changes
5. Commit using [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat(scope): add new feature
   fix(scope): resolve bug with X
   docs: update installation steps
   ```
6. Push to your fork and open a Pull Request

## Branch Naming

| Prefix | Use |
| --- | --- |
| `feature/<description>` | New features |
| `fix/<description>` | Bug fixes |
| `hotfix/<description>` | Urgent production fixes |
| `refactor/<description>` | Code improvements |
| `chore/<description>` | Maintenance tasks |

## Development

```bash
uv sync                          # install deps
uv run pytest                    # run the test suite
uv run ruff check .              # lint
uv run ruff format .             # format
uv run python -m discordctl      # run the daemon (needs a configured .env)
```

New operations live in `src/discordctl/ops/handlers/` and register with the `@op("name", mutating=...)`
decorator. Every mutating op must be dry-run-by-default: return `plan(...)` and perform no write when
`ctx.dry_run` is true. Add tests under `tests/handlers/` and keep the op-catalog smoke test in sync.

## Code Standards

- Write clear, readable code over clever code
- Follow existing patterns in the codebase
- Keep functions short and focused
- This codebase favours self-documenting names over inline comments
- Handle errors explicitly; never silently swallow failures
- Type hints on every function

## Pull Requests

- Keep PRs focused on a single change
- Write a clear title following conventional commit format
- Fill in the PR template
- Make sure CI passes (lint, format, tests) before requesting review
- Respond to review feedback promptly

## Reporting Issues

Use the issue templates provided:

- **Bug Report** -- for bugs and unexpected behaviour
- **Feature Request** -- for new ideas and improvements

Include as much detail as possible. Steps to reproduce are essential for bug reports. Never paste your
bot token or `.env` contents into an issue.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
