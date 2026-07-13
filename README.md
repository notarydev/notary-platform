# Notary Forensic Logger SDK

Offline-first sealing and interception library for AI agents. Record and verify every decision, API call, and LLM invocation.

## Features

- **Offline-first**: Zero cloud/network dependencies. All sealing happens locally using HMAC-SHA256 and Merkle chaining.
- **Cryptographic sealing**: Every snapshot is signed and tamper-evident.
- **Forensic completeness**: Capture LLM prompts/completions, HTTP requests/responses, and decision points.
- **Local verification**: Verify chains and root hashes without contacting any service.

## Installation

```bash
pip install notary-sdk
```

## Quick Start

See [SETUP.md](./SETUP.md) for development setup instructions.

## Repository Structure

- `src/notary/` — Python SDK package
  - `sealing.py` — HMAC-SHA256 and Merkle chaining
  - `interception.py` — LLM/HTTP/decision capture
  - `snapshot.py` — ForensicSnapshot model with schema versioning
  - `verify.py` — Local root-hash verification
- `packages/notary-sdk-ts/` — TypeScript implementation
- `tests/` — Test suite
- `.github/workflows/` — CI/CD pipelines

## License

Apache License 2.0. See [LICENSE](./LICENSE) for details.

## Security

For security vulnerability reporting, see [SECURITY.md](./SECURITY.md).

## Contributing

Contributions welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md).
