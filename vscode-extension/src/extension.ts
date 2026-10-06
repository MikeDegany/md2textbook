import { existsSync } from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import { Cli, MINIMUM_VERSION, convertFile, describeFailure, findCli, isOlder } from "./cli";
import { offerInstall, offerUpgrade } from "./install";
import { isLocked, pdfPathFor } from "./pdfPath";

const MARKDOWN_SUFFIX = /\.(md|markdown|mdown)$/i;
const SAVE_DELAY_MS = 600;

let output: vscode.OutputChannel;
let status: vscode.StatusBarItem;
let cached: Cli | undefined;
let warnedAboutVersion = false;
const converting = new Set<string>();
const saveTimers = new Map<string, NodeJS.Timeout>();

const settings = () => vscode.workspace.getConfiguration("md2textbook");

function updateStatus(): void {
  if (converting.size > 0) {
    status.text = "$(sync~spin) md2textbook: converting...";
    status.show();
  } else {
    status.hide();
  }
}

async function ensureCli(): Promise<Cli | undefined> {
  if (cached) {
    return cached;
  }
  cached = await findCli(settings().get<string>("command", "md2textbook"));
  if (!cached) {
    output.appendLine("md2textbook was not found.");
    return undefined;
  }
  output.appendLine(`Using "${cached.parts.join(" ")}" (version ${cached.version})`);
  if (isOlder(cached.version, MINIMUM_VERSION) && !warnedAboutVersion) {
    warnedAboutVersion = true;
    void offerUpgrade(cached.version, MINIMUM_VERSION).then((outcome) => {
      if (outcome === "retry") {
        cached = undefined;
      }
    });
  }
  return cached;
}

async function openPdf(pdf: string): Promise<void> {
  const uri = vscode.Uri.file(pdf);
  if (vscode.env.remoteName) {
    await vscode.commands.executeCommand("revealInExplorer", uri);
    void vscode.window.showInformationMessage(
      `PDF saved as ${path.basename(pdf)}. This window runs on a remote machine, so it cannot start a PDF reader on your computer. Right-click the file in the Explorer and choose Download.`,
    );
    return;
  }
  const mode = settings().get<string>("openWith", "external");
  if (mode === "vscode") {
    try {
      await vscode.commands.executeCommand("vscode.open", uri);
      return;
    } catch {
      output.appendLine("No PDF viewer in VS Code; opening the default reader instead.");
    }
  }
  if (mode === "none") {
    void vscode.window
      .showInformationMessage(`PDF ready: ${path.basename(pdf)}`, "Open PDF", "Show in Folder")
      .then((pick) => {
        if (pick === "Open PDF") {
          void vscode.env.openExternal(uri);
        } else if (pick === "Show in Folder") {
          void vscode.commands.executeCommand("revealFileInOS", uri);
        }
      });
    return;
  }
  await vscode.env.openExternal(uri);
}

async function resolveCli(auto: boolean): Promise<Cli | undefined> {
  let cli = await ensureCli();
  if (!cli && !auto) {
    if ((await offerInstall()) === "retry") {
      cached = undefined;
      cli = await ensureCli();
    }
  }
  return cli;
}

async function convert(markdownPath: string, auto: boolean): Promise<string | undefined> {
  if (converting.has(markdownPath)) {
    return undefined;
  }
  converting.add(markdownPath);
  updateStatus();
  try {
    const document = vscode.workspace.textDocuments.find((doc) => doc.uri.fsPath === markdownPath);
    if (!auto && document?.isDirty) {
      await document.save();
    }
    const cli = await resolveCli(auto);
    if (!cli) {
      if (auto) {
        output.appendLine("Skipped conversion on save: md2textbook is not installed.");
      }
      return undefined;
    }
    const pdf = pdfPathFor(markdownPath);
    const name = path.basename(pdf);
    while (await isLocked(pdf)) {
      if (auto) {
        output.appendLine(`Skipped conversion on save: ${name} is open in another program.`);
        vscode.window.setStatusBarMessage(`$(warning) ${name} is open in a PDF reader; not updated`, 6000);
        return undefined;
      }
      const pick = await vscode.window.showErrorMessage(
        `Close ${name} in your PDF reader, then press Retry. It cannot be updated while it is open.`,
        "Retry",
        "Cancel",
      );
      if (pick !== "Retry") {
        return undefined;
      }
    }
    output.appendLine(`Converting ${markdownPath}`);
    const result = auto
      ? await convertFile(cli, markdownPath, pdf)
      : await vscode.window.withProgress(
          { location: vscode.ProgressLocation.Notification, title: `Converting ${path.basename(markdownPath)}...` },
          () => convertFile(cli, markdownPath, pdf),
        );
    if (result.stdout.trim()) {
      output.appendLine(result.stdout.trim());
    }
    if (result.stderr.trim()) {
      output.appendLine(result.stderr.trim());
    }
    if (result.code !== 0) {
      const reason = describeFailure(result);
      if (auto) {
        vscode.window.setStatusBarMessage(`$(error) md2textbook failed: ${reason}`, 8000);
      } else {
        void vscode.window
          .showErrorMessage(`Conversion failed: ${reason}`, "Show Output")
          .then((pick) => pick && output.show());
      }
      return undefined;
    }
    if (!auto || settings().get<boolean>("openAfterAutoConvert", false)) {
      await openPdf(pdf);
    } else {
      vscode.window.setStatusBarMessage(`$(check) ${name} updated`, 4000);
    }
    return pdf;
  } finally {
    converting.delete(markdownPath);
    updateStatus();
  }
}

function targetMarkdown(uri?: vscode.Uri): string | undefined {
  const target = uri ?? vscode.window.activeTextEditor?.document.uri;
  if (!target || target.scheme !== "file" || !MARKDOWN_SUFFIX.test(target.fsPath)) {
    void vscode.window.showInformationMessage("Open a saved Markdown (.md) file first.");
    return undefined;
  }
  return target.fsPath;
}

async function openExisting(uri?: vscode.Uri): Promise<void> {
  const markdownPath = targetMarkdown(uri);
  if (!markdownPath) {
    return;
  }
  const pdf = pdfPathFor(markdownPath);
  if (existsSync(pdf)) {
    await openPdf(pdf);
    return;
  }
  const pick = await vscode.window.showInformationMessage(
    `${path.basename(pdf)} does not exist yet. Convert now?`,
    "Convert",
  );
  if (pick === "Convert") {
    await convert(markdownPath, false);
  }
}

async function checkInstall(): Promise<void> {
  cached = undefined;
  const cli = await ensureCli();
  if (!cli) {
    if ((await offerInstall()) === "retry") {
      await checkInstall();
    }
    return;
  }
  void vscode.window.showInformationMessage(`md2textbook ${cli.version} is ready (${cli.parts.join(" ")}).`);
}

export function activate(context: vscode.ExtensionContext): void {
  output = vscode.window.createOutputChannel("md2textbook");
  status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
  context.subscriptions.push(output, status);

  context.subscriptions.push(
    vscode.commands.registerCommand("md2textbook.convert", (uri?: vscode.Uri) => {
      const markdownPath = targetMarkdown(uri);
      return markdownPath ? convert(markdownPath, false) : undefined;
    }),
    vscode.commands.registerCommand("md2textbook.openPdf", openExisting),
    vscode.commands.registerCommand("md2textbook.checkInstall", checkInstall),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration("md2textbook.command")) {
        cached = undefined;
      }
    }),
    vscode.workspace.onDidSaveTextDocument((document) => {
      if (
        !settings().get<boolean>("convertOnSave", false) ||
        document.languageId !== "markdown" ||
        document.uri.scheme !== "file"
      ) {
        return;
      }
      const markdownPath = document.uri.fsPath;
      clearTimeout(saveTimers.get(markdownPath));
      saveTimers.set(
        markdownPath,
        setTimeout(() => void convert(markdownPath, true), SAVE_DELAY_MS),
      );
    }),
  );
}

export function deactivate(): void {
  saveTimers.forEach((timer) => clearTimeout(timer));
}
