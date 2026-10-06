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

## Working on the VS Code extension

The extension lives in `vscode-extension/` and is versioned separately from the Python package. You need [Node.js](https://nodejs.org) 22 or newer.

```bash
cd vscode-extension
npm install
npm test                  # type-check and unit tests
npm run test:integration  # runs the extension inside a real VS Code (downloads it on first use)
npm run package           # builds md2textbook-<version>.vsix
```

To try it by hand, open `vscode-extension` in VS Code and press `F5`, or install the `.vsix` with **Extensions: Install from VSIX...**.

To release a new extension version, raise `version` in `vscode-extension/package.json`, add a section to `vscode-extension/CHANGELOG.md`, run `npm run package`, and upload the `.vsix` on the [Marketplace publisher page](https://marketplace.visualstudio.com/manage) (and to [Open VSX](https://open-vsx.org) if you publish there). Never commit access tokens.

## Pull requests

1. Fork the repository and create a branch.
2. Keep the change focused, and add a test when behavior changes.
3. Add a line under "Unreleased" in `CHANGELOG.md` (or in `vscode-extension/CHANGELOG.md` for the extension).
4. Make sure `pytest` passes, then open the pull request. CI runs the tests on Linux, Windows and macOS.

## Style

Match the surrounding code: short names, type hints where they help, comments only to explain a non-obvious reason.
