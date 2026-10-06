import { existsSync, rmSync, symlinkSync } from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { runTests } from "@vscode/test-electron";

// VS Code's test launcher splits paths at spaces, so go through a space-free folder link.
function spaceFreeRoot(root: string): string {
  if (!root.includes(" ")) {
    return root;
  }
  const link = path.join(os.tmpdir(), "md2textbook-repo-link");
  rmSync(link, { recursive: true, force: true });
  symlinkSync(root, link, "junction");
  return link;
}

async function main(): Promise<void> {
  const repoRoot = spaceFreeRoot(path.resolve(__dirname, "../../.."));
  const extensionDevelopmentPath = path.join(repoRoot, "vscode-extension");
  const extensionTestsPath = path.join(extensionDevelopmentPath, "out", "test", "suite", "index");
  const workspace = path.join(repoRoot, "examples");
  const installed = path.join(process.env.LOCALAPPDATA ?? "", "Programs", "Microsoft VS Code", "Code.exe");
  const vscodeExecutablePath = process.env.VSCODE_EXE ?? (existsSync(installed) ? installed : undefined);
  await runTests({
    vscodeExecutablePath,
    extensionDevelopmentPath,
    extensionTestsPath,
    launchArgs: [
      workspace,
      "--disable-extensions",
      "--disable-workspace-trust",
      "--user-data-dir",
      path.join(os.tmpdir(), "md2textbook-test-profile"),
    ],
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
