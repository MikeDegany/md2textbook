import assert from "node:assert/strict";
import { copyFileSync, existsSync, mkdtempSync, rmSync, statSync } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import * as vscode from "vscode";

type TestCase = { name: string; run: () => Promise<void> };

const examples = path.resolve(__dirname, "../../../../examples");
const config = () => vscode.workspace.getConfiguration("md2textbook");

function sampleCopy(): { dir: string; markdown: string } {
  const dir = mkdtempSync(path.join(os.tmpdir(), "md2tb space-"));
  copyFileSync(path.join(examples, "showcase.md"), path.join(dir, "showcase.md"));
  copyFileSync(path.join(examples, "showcase_figure.png"), path.join(dir, "showcase_figure.png"));
  return { dir, markdown: path.join(dir, "showcase.md") };
}

const cases: TestCase[] = [
  {
    name: "extension is present and registers its commands",
    async run() {
      await vscode.extensions.all.find((ext) => ext.packageJSON.name === "md2textbook")?.activate();
      const commands = await vscode.commands.getCommands(true);
      for (const id of ["md2textbook.convert", "md2textbook.openPdf", "md2textbook.checkInstall"]) {
        assert.ok(commands.includes(id), `${id} is not registered`);
      }
    },
  },
  {
    name: "convert command writes the PDF next to the Markdown file",
    async run() {
      await config().update("openWith", "none", vscode.ConfigurationTarget.Global);
      const { dir, markdown } = sampleCopy();
      try {
        const pdf = await vscode.commands.executeCommand<string | undefined>(
          "md2textbook.convert",
          vscode.Uri.file(markdown),
        );
        assert.equal(pdf?.toLowerCase(), path.join(dir, "showcase.pdf").toLowerCase());
        assert.ok(existsSync(pdf!), "PDF was not created");
        assert.ok(statSync(pdf!).size > 50_000, "PDF is suspiciously small");
      } finally {
        rmSync(dir, { recursive: true, force: true });
      }
    },
  },
  {
    name: "a wrong configured command falls back to python -m md2textbook",
    async run() {
      await config().update("openWith", "none", vscode.ConfigurationTarget.Global);
      await config().update("command", "definitely-not-installed-md2textbook", vscode.ConfigurationTarget.Global);
      const { dir, markdown } = sampleCopy();
      try {
        const pdf = await vscode.commands.executeCommand<string | undefined>(
          "md2textbook.convert",
          vscode.Uri.file(markdown),
        );
        assert.ok(pdf && existsSync(pdf), "fallback conversion did not produce a PDF");
      } finally {
        await config().update("command", undefined, vscode.ConfigurationTarget.Global);
        rmSync(dir, { recursive: true, force: true });
      }
    },
  },
  {
    name: "convert on save creates a PDF without opening a reader",
    async run() {
      await config().update("openWith", "none", vscode.ConfigurationTarget.Global);
      await config().update("convertOnSave", true, vscode.ConfigurationTarget.Global);
      const { dir, markdown } = sampleCopy();
      try {
        const document = await vscode.workspace.openTextDocument(markdown);
        const editor = await vscode.window.showTextDocument(document);
        await editor.edit((edit) => edit.insert(new vscode.Position(document.lineCount, 0), "\n\nExtra paragraph.\n"));
        await document.save();
        const pdf = path.join(dir, "showcase.pdf");
        for (let i = 0; i < 120 && !existsSync(pdf); i++) {
          await new Promise((resolve) => setTimeout(resolve, 500));
        }
        assert.ok(existsSync(pdf), "convert on save did not produce a PDF within 60 s");
      } finally {
        await config().update("convertOnSave", undefined, vscode.ConfigurationTarget.Global);
        await vscode.commands.executeCommand("workbench.action.closeAllEditors");
        await new Promise((resolve) => setTimeout(resolve, 1000));
        rmSync(dir, { recursive: true, force: true });
      }
    },
  },
];

export async function run(): Promise<void> {
  const failures: string[] = [];
  for (const test of cases) {
    try {
      await test.run();
      console.log(`  ok   ${test.name}`);
    } catch (error) {
      failures.push(test.name);
      console.error(`  FAIL ${test.name}\n       ${error instanceof Error ? error.message : error}`);
    }
  }
  if (failures.length > 0) {
    throw new Error(`${failures.length} integration test(s) failed`);
  }
}
