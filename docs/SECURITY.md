# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in the Notary SDK, please **do not** open a public GitHub issue. Instead, please report the vulnerability responsibly to the Notary security team.

### Private Disclosure

Email your findings to: **security@notary.dev** (placeholder — configure with your actual security contact).

Please include:
- A description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact
- Suggested fixes (if you have any)

We will acknowledge receipt within 48 hours and work with you on a timeline for disclosure.

## Security Considerations

### Offline-First Design

The Notary SDK is designed to be completely offline. It has **zero** cloud or network dependencies:
- All cryptographic operations use Python's standard library (`hmac`, `hashlib`)
- No external packages are imported in core sealing/verification paths
- All secrets should be managed locally

### Supported Algorithms

- **Hashing**: SHA-256 (via `hashlib`)
- **HMAC**: HMAC-SHA256 (via `hmac`)
- **Merkle Chaining**: SHA-256 tree construction

### Verification

Always verify forensic snapshots using the local `verify.py` module before trusting any captured data.

## Version Support

We support the following Python versions:
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

Please keep your Python installation up to date with the latest security patches.
