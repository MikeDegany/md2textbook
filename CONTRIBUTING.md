# Contributing

Bug reports, ideas and pull requests are welcome.

## Reporting a problem

Open an [issue](https://github.com/MikeDegany/md2textbook/issues/new/choose) and fill in the form. The most useful thing you can include is a small Markdown file that reproduces the problem.

## Development setup

```bash
git clone https://github.com/MikeDegany/md2textbook
cd md2textbook
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

Convert the feature tour to check visual changes:

```bash
md2textbook examples/showcase.md
```

## Pull requests

1. Fork the repository and create a branch.
2. Keep the change focused, and add a test when behavior changes.
3. Add a line under "Unreleased" in `CHANGELOG.md`.
4. Make sure `pytest` passes, then open the pull request. CI runs the tests on Linux, Windows and macOS.

## Style

Match the surrounding code: short names, type hints where they help, comments only to explain a non-obvious reason.
