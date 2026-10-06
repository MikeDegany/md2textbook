import * as vscode from "vscode";
import { findPython } from "./cli";

export type InstallOutcome = "retry" | "cancel";

async function pipInTerminal(args: string[]): Promise<InstallOutcome> {
  const python = await findPython();
  if (!python) {
    const pick = await vscode.window.showErrorMessage(
      "Python 3.10 or newer is required. Install it from python.org first and tick 'Add python.exe to PATH'.",
      "Open python.org",
    );
    if (pick) {
      await vscode.env.openExternal(vscode.Uri.parse("https://www.python.org/downloads/"));
    }
    return "cancel";
  }
  const terminal = vscode.window.createTerminal("md2textbook install");
  terminal.show();
  terminal.sendText(`${python} -m pip ${args.join(" ")}`);
  const pick = await vscode.window.showInformationMessage(
    "Installing in the terminal. When it prints 'Successfully installed', press Retry.",
    "Retry",
    "Cancel",
  );
  return pick === "Retry" ? "retry" : "cancel";
}

export async function offerInstall(): Promise<InstallOutcome> {
  const pick = await vscode.window.showInformationMessage(
    "md2textbook is not installed on this computer. Install it now with pip?",
    "Install",
    "Cancel",
  );
  return pick === "Install" ? pipInTerminal(["install", "--user", "--upgrade", "md2textbook"]) : "cancel";
}

export async function offerUpgrade(found: string, minimum: string): Promise<InstallOutcome> {
  const pick = await vscode.window.showWarningMessage(
    `md2textbook ${found} is installed, but ${minimum} or newer is recommended. Upgrade now?`,
    "Upgrade",
    "Not now",
  );
  return pick === "Upgrade"
    ? pipInTerminal(["install", "--user", "--upgrade", "--no-cache-dir", "md2textbook"])
    : "cancel";
}
