import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { test } from "node:test";
import { isLocked, pdfPathFor } from "../../src/pdfPath";

test("pdfPathFor puts the PDF next to the Markdown file", () => {
  const md = path.join("some dir", "My Report.v2.md");
  assert.equal(pdfPathFor(md), path.join("some dir", "My Report.v2.pdf"));
});

test("isLocked is false for a missing or ordinary file", async () => {
  const dir = mkdtempSync(path.join(os.tmpdir(), "md2tb-"));
  try {
    assert.equal(await isLocked(path.join(dir, "missing.pdf")), false);
    const file = path.join(dir, "free.pdf");
    writeFileSync(file, "x");
    assert.equal(await isLocked(file), false);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("isLocked is true while another program holds the file open", { skip: process.platform !== "win32" }, async () => {
  const dir = mkdtempSync(path.join(os.tmpdir(), "md2tb-"));
  const file = path.join(dir, "held.pdf");
  writeFileSync(file, "x");
  const holder = spawn(
    "powershell",
    [
      "-NoProfile",
      "-Command",
      `$f = [System.IO.File]::Open('${file}', 'Open', 'ReadWrite', 'None'); Start-Sleep -Seconds 20`,
    ],
    { windowsHide: true },
  );
  try {
    let locked = false;
    for (let i = 0; i < 40 && !locked; i++) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      locked = await isLocked(file);
    }
    assert.equal(locked, true);
  } finally {
    holder.kill();
    await new Promise((resolve) => setTimeout(resolve, 300));
    rmSync(dir, { recursive: true, force: true });
  }
});
