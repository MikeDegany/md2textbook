# Changelog

## [0.1.1] - 2026-10-06

### Changed
- The PDF is now only saved next to the Markdown file; no PDF reader is started. The `md2textbook.openWith` setting defaults to `none`; set it to `external` or `vscode` to open the PDF automatically.
- After a manual conversion a small message confirms where the PDF was saved, with a "Show in Folder" button.

## [0.1.0] - 2026-10-05

### Added
- Convert the open or right-clicked Markdown file to a textbook-style PDF with md2textbook, and open it in the default PDF reader.
- Editor title button, editor and Explorer context menu entries, and the `Ctrl+Alt+P` shortcut.
- Optional convert on save.
- Finds md2textbook on PATH or via `python -m md2textbook`, and offers to install or upgrade it.
- Detects a PDF locked by a reader and asks you to close it and retry.
