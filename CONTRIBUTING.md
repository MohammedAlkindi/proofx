# Contributing to ProofX

Thank you for your interest in contributing to ProofX.

ProofX is a research-focused project exploring computational mathematics, integer dynamics, and reproducible mathematical software. The priority is correctness, reproducibility, and maintainability over shipping features quickly.

Please read this document before opening an issue or submitting a pull request.

---

# Philosophy

Every contribution should improve at least one of the following:

- Mathematical correctness
- Reproducibility
- Code quality
- Documentation
- Performance
- Testing
- Developer experience

Features without a clear research or engineering benefit will generally not be accepted.

---

# Before You Start

1. Read the README.
2. Search existing issues before opening a new one.
3. If your change is substantial, open an issue first to discuss the approach.
4. Keep pull requests focused on a single objective.

---

# Development Setup

Clone the repository:

```bash
git clone https://github.com/MohammedAlkindi/ProofX.git
cd ProofX
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

---

# Code Style

We prioritize readability over cleverness.

## Python

- Follow PEP 8.
- Use type hints whenever practical.
- Prefer small, composable functions.
- Avoid unnecessary abstractions.
- Avoid global mutable state.
- Keep deterministic logic separate from I/O.

Example:

```python
def iterate(n: int) -> int:
    ...
```

instead of

```python
def iterate(n):
    ...
```

---

# Documentation

Every public function should include:

- Purpose
- Parameters
- Return value
- Important assumptions

Complex mathematical algorithms should include references where appropriate.

---

# Testing

New functionality should include tests whenever feasible.

Run checks before submitting:

```bash
pytest
ruff check .
ruff format --check .
mypy codebase
lake build
```

A pull request should not reduce overall test quality.

---

# Pull Requests

A good pull request should:

- Solve one problem
- Include a clear description
- Explain any design decisions
- Update documentation if needed
- Pass all tests

Small PRs are preferred over large ones.

---

# Commit Messages

Use concise, descriptive commit messages.

Examples:

```text
Add modular arithmetic utilities

Improve search performance

Fix overflow in iteration engine

Add regression tests for verifier
```

Avoid messages like:

```text
update

fix

changes

stuff
```

---

# Issues

Bug reports should include:

- Expected behavior
- Actual behavior
- Steps to reproduce
- Python version
- Operating system
- Relevant logs if available

Feature requests should explain:

- The problem
- Proposed solution
- Why it benefits ProofX

---

# Mathematical Contributions

When contributing new mathematical algorithms:

- Clearly describe the underlying method.
- Cite references when applicable.
- Include correctness tests.
- Explain computational complexity if relevant.
- Prefer deterministic implementations whenever possible.

---

# Performance

Performance improvements should include evidence when possible.

Useful benchmarks include:

- Runtime
- Memory usage
- Scaling behavior
- Representative workloads

---

# Security

Do not commit:

- API keys
- Secrets
- Credentials
- Private datasets
- Generated cache files

If you discover a security issue, please report it privately rather than opening a public issue.

---

# Code Review

Reviews focus on:

- Correctness
- Readability
- Mathematical soundness
- Reproducibility
- Maintainability
- Test coverage

Receiving requested changes is a normal part of the review process.

---

# License

By contributing to ProofX, you agree that your contributions will be licensed under the project's license.

---

Thank you for helping improve ProofX.
