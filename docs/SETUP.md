# Development Setup — Notary SDK (PUBLIC)

## Prerequisites

Before starting, ensure the following are completed **outside this repository**:

1. **Repository Creation** — The `notarydev/notary-sdk` repository exists on GitHub
2. **PyPI Name Reservation** — The name `notary-sdk` is reserved on PyPI
3. **npm Name Reservation** — The name `@notary/sdk` is reserved on npm
4. **Project Integration** — The repository is connected to the GitHub Project (WO-20)
5. **Trusted Publishing** — Set up PyPI and npm trusted publishing (OIDC) for automated releases
   - [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
   - [npm Trusted Publishing](https://docs.npmjs.com/creating-and-viewing-access-tokens)

## Local Development

### Python SDK

1. **Clone the repository**
   ```bash
   git clone https://github.com/notarydev/notary-sdk.git
   cd notary-sdk
   ```

2. **Create a virtual environment**
   ```bash
   python3.9+ -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests**
   ```bash
   pytest tests/
   ```

5. **Lint and type-check**
   ```bash
   ruff check src/ tests/
   mypy src/
   ```

### TypeScript SDK

1. **Navigate to the TypeScript package**
   ```bash
   cd packages/notary-sdk-ts
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Build and test**
   ```bash
   npm run build
   npm test
   ```

## CI/CD Workflows

Three GitHub Actions workflows are configured:

### 1. `python.yml` — Python Linting, Type-Check, and Tests
- Triggers: push, pull request
- Runs: Ruff lint, mypy type-check, pytest

### 2. `typescript.yml` — TypeScript Linting, Build, and Tests
- Triggers: push, pull request
- Runs: ESLint, tsc compile, npm test

### 3. `publish.yml` — Publish to PyPI and npm
- Triggers: GitHub release / tag
- **Requires**: Trusted publishing configured on PyPI and npm
- **Requires**: GitHub environment secrets (see below)

## Secrets and Configuration

No secrets are hardcoded. The `publish.yml` workflow uses **trusted publishing** (OIDC).

### For Manual Token-Based Publishing (if needed)

If you prefer token-based authentication, configure these repository secrets:

- `PYPI_API_TOKEN` — PyPI API token (get from https://pypi.org/account/tokens/)
- `NPM_TOKEN` — npm automation token (get from https://npmjs.com/settings/~/tokens)

These are optional and are documented in the workflow as placeholders.

## Merging and Releasing

1. **Merge to main** — All tests must pass on the `scaffold/initial-setup` branch
2. **Tag a release** — Create a GitHub release with a semantic version tag (e.g., `v0.1.0`)
3. **Automated publishing** — The `publish.yml` workflow triggers automatically and publishes to PyPI and npm

## Troubleshooting

### Tests fail locally but pass in CI
- Ensure Python version matches CI (3.9+)
- Clear cache: `rm -rf .pytest_cache __pycache__`
- Reinstall: `pip install -e ".[dev]" --force-reinstall`

### Type-checking fails
- Ensure all code has type hints
- Run `mypy src/ --show-error-codes` for detailed diagnostics

### npm/pip not found
- Activate venv: `source venv/bin/activate`
- Verify installation: `pip --version`, `npm --version`
