# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Images that cannot be read now say why (missing file or unreadable format) and print the cause to stderr instead of always reporting "not found".

## [0.1.2] - 2026-10-01

### Added
- `examples/showcase.md`, a feature tour used for the README screenshots.
- Screenshots in the README.
- `Source` and `Changelog` project links on PyPI.

### Fixed
- `LICENSE` now contains only the MIT text so GitHub detects the license. Font licenses stay in `src/md2textbook/fonts/`.

## [0.1.1] - 2026-10-01

### Changed
- Version bump to exercise the automated release workflow.

## [0.1.0] - 2026-10-01

### Added
- Markdown to coursebook-style PDF conversion: gradient cover, table of contents, chapter banners, running headers, page-number pills and PDF bookmarks.
- Colored boxes from `> [!KIND]` callouts and `> **Kind:**` shorthand.
- Inline and numbered display math rendered with matplotlib mathtext.
- Syntax-highlighted code with line numbers, wrapping and numbered listing captions.
- Zebra tables with repeating headers, and numbered figures.
- `md2textbook` command with `-o` and `--no-open`, a file chooser when no file is given, and `md2textbook-gui`.
- Bundled Poppins and Caladea fonts, with DejaVu fallback.
- Support for Windows, macOS and Linux.
