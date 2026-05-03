# CI/CD Recommendations for ooUI

## Overview

This document provides recommended CI/CD setup to ensure code quality, test coverage, and security compliance.

---

## 1. Automated Testing (GitHub Actions)

### Create `.github/workflows/test.yml`

```yaml
name: Tests & Lint

on:
  push:
    branches: ["main", "develop"]
  pull_request:
    branches: ["main"]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: ["windows-latest", "ubuntu-latest", "macos-latest"]
        python-version: ["3.10", "3.11", "3.12"]
        exclude:
          # PyQt6 on Linux/macOS may have additional deps
          - os: "ubuntu-latest"
            python-version: "3.10"

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-qt pytest-cov PyQt6

      - name: Run unit tests
        run: |
          pytest -q --tb=short --cov=. --cov-report=term-missing

      - name: Run security tests
        run: |
          pytest -q tests/test_security.py -v

      - name: Upload coverage (optional)
        if: matrix.os == 'windows-latest' && matrix.python-version == '3.11'
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: false
```

### Create `.github/workflows/lint.yml`

```yaml
name: Lint

on:
  push:
    branches: ["main", "develop"]
  pull_request:
    branches: ["main"]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install linting tools
        run: |
          python -m pip install --upgrade pip
          pip install flake8 black isort mypy

      - name: Run flake8
        run: flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

      - name: Check code formatting (black)
        run: black --check .

      - name: Check import ordering (isort)
        run: isort --check-only .

      - name: Run type checking (mypy)
        run: mypy . --ignore-missing-imports || true  # Optional; not strict yet
```

---

## 2. Local Development Setup

### Create `requirements-dev.txt`

```txt
# Testing
pytest==9.0.3
pytest-qt==4.5.0
pytest-cov==4.1.0

# Linting & Formatting
flake8==6.1.0
black==23.12.1
isort==5.13.2
mypy==1.7.0

# PyQt6 (already in main requirements but useful for clarity)
PyQt6==6.11.0
```

### Create `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ["--max-line-length=100"]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ["--maxkb=500"]
```

### Installation

```powershell
# Install dev dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files
```

---

## 3. Security Scanning

### Add to `.github/workflows/security.yml`

```yaml
name: Security Scan

on:
  push:
    branches: ["main", "develop"]
  pull_request:
    branches: ["main"]
  schedule:
    - cron: "0 0 * * *"  # Daily at midnight UTC

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install security tools
        run: |
          python -m pip install --upgrade pip
          pip install bandit safety

      - name: Run bandit (security linter)
        run: |
          bandit -r . -ll --skip B101,B601 || true

      - name: Check dependencies (safety)
        run: |
          safety check --db online || true
```

---

## 4. Recommended Local Workflow

Before pushing code:

```powershell
# 1. Install dev dependencies (once)
pip install -r requirements-dev.txt
pre-commit install

# 2. Run tests locally
pytest -q

# 3. Check security-specific tests
pytest -q tests/test_security.py

# 4. Format code
black .
isort .

# 5. Lint
flake8 .

# 6. Type check (optional, not strict yet)
mypy . --ignore-missing-imports

# 7. Security scan (optional)
bandit -r . -ll
```

---

## 5. Configuration Files

### Create `setup.cfg` (flake8 config)

```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv,build,dist,.venv
ignore = E203,W503,E501

[isort]
profile = black
line_length = 100

[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
ignore_missing_imports = True
```

### Create `pyproject.toml` (black config)

```toml
[tool.black]
line-length = 100
target-version = ['py310']
exclude = '''
/(
    \.git
  | \.venv
  | venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "-q --tb=short"
```

---

## 6. Manual Quality Gates (before merge)

- ✅ **All tests pass**: `pytest -q` returns 0 errors
- ✅ **Security tests pass**: `pytest -q tests/test_security.py` returns 0 errors
- ✅ **Code formatted**: `black --check .` returns 0 errors
- ✅ **No lint warnings**: `flake8 .` returns clean
- ✅ **Dependencies audited**: `safety check` shows no critical vulns
- ✅ **PR reviewed**: At least 1 approval from maintainers

---

## 7. Documentation

### Create `CONTRIBUTING.md`

```markdown
# Contributing to ooUI

## Setup

1. Clone the repository
2. Install Python 3.10+
3. Install dev dependencies:
   ```
   pip install -r requirements-dev.txt
   pre-commit install
   ```

## Making Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and run tests: `pytest -q`
3. Commit (pre-commit will auto-format): `git commit -m "..."`
4. Push and open a PR

## Testing

- Unit tests: `pytest -q`
- Security tests: `pytest -q tests/test_security.py`
- Coverage: `pytest --cov=. --cov-report=html`

## Code Standards

- Line length: 100 characters (black)
- Follow PEP 8 (isort for import ordering)
- Type hints recommended (mypy for validation)
- Docstrings on public functions/classes

## Security

See [SECURITY_FIXES.md](docs/SECURITY_FIXES.md) for details on recent security improvements and CWE mitigations.
```

---

## 8. Summary Checklist

- [ ] Create `.github/workflows/test.yml` (unit tests)
- [ ] Create `.github/workflows/lint.yml` (code style)
- [ ] Create `.github/workflows/security.yml` (security scan)
- [ ] Add `requirements-dev.txt`
- [ ] Add `.pre-commit-config.yaml`
- [ ] Add `setup.cfg` and `pyproject.toml`
- [ ] Add `CONTRIBUTING.md`
- [ ] Update main `README.md` with testing instructions
- [ ] Set branch protection rules on GitHub (require status checks)

---

## Next Iteration

After this setup is in place:
1. **Add coverage reporting** to track test coverage over time
2. **Add code quality gates** (e.g., SonarQube) to block merges if coverage drops
3. **Automate releases** with semantic versioning and changelog generation
4. **Monitor dependencies** with Dependabot for automated security updates

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [OWASP Secure Coding Practices](https://cheatsheetseries.owasp.org/)
