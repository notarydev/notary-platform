# Contributing to Notary SDK

Thank you for your interest in contributing! We welcome contributions from the community.

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Set up your development environment (see [SETUP.md](./SETUP.md))
4. Make your changes
5. Run tests and linting: `make check`
6. Commit with clear messages
7. Push and open a pull request

## Development Workflow

### Install Dependencies

```bash
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

### Linting and Type Checking

```bash
ruff check src/ tests/
mypy src/
```

## Code Standards

- **Python**: PEP 8, enforced by Ruff
- **Type hints**: Full coverage required (enforced by mypy)
- **Tests**: All new code must include tests
- **Docstrings**: All public APIs must be documented

## Pull Request Process

1. Ensure all tests pass and linting is clean
2. Add an entry to the changelog (if applicable)
3. Provide a clear description of the change
4. Link any related issues
5. Wait for review and address feedback

## Code of Conduct

Be respectful and constructive in all interactions. We are committed to maintaining a welcoming community.

## License

All contributions are licensed under the Apache License 2.0.
