import { spawn } from "node:child_process";

export const MINIMUM_VERSION = "0.1.3";

export interface RunResult {
  code: number | null;
  stdout: string;
  stderr: string;
  notFound: boolean;
}

export interface Cli {
  parts: string[];
  version: string;
}

export function splitCommand(text: string): string[] {
  const parts: string[] = [];
  const pattern = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    parts.push(match[1] ?? match[2] ?? match[3]);
  }
  return parts;
}

export function candidateCommands(configured: string): string[][] {
  const candidates = [
    splitCommand(configured),
    ["python", "-m", "md2textbook"],
    ["py", "-m", "md2textbook"],
    ["python3", "-m", "md2textbook"],
  ].filter((parts) => parts.length > 0);
  const seen = new Set<string>();
  return candidates.filter((parts) => {
    const key = parts.join("\u0000");
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function parseVersion(text: string): string | undefined {
  return /md2textbook\s+(\d+(?:\.\d+)*)/i.exec(text)?.[1];
}

export function isOlder(version: string, minimum: string): boolean {
  const a = version.split(".").map(Number);
  const b = minimum.split(".").map(Number);
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const diff = (a[i] ?? 0) - (b[i] ?? 0);
    if (diff !== 0) {
      return diff < 0;
    }
  }
  return false;
}

export function lastLine(text: string): string {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  return lines[lines.length - 1] ?? "";
}

export function describeFailure(result: RunResult): string {
  const reason = lastLine(result.stderr) || lastLine(result.stdout);
  return reason || `md2textbook exited with code ${result.code}`;
}

export function run(parts: string[], extraArgs: string[]): Promise<RunResult> {
  return new Promise((resolve) => {
    const [command, ...args] = parts;
    let stdout = "";
    let stderr = "";
    let child;
    try {
      child = spawn(command, [...args, ...extraArgs], {
        windowsHide: true,
        env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      });
    } catch (error) {
      resolve({ code: null, stdout, stderr: String(error), notFound: true });
      return;
    }
    child.stdout.on("data", (chunk) => (stdout += chunk.toString("utf8")));
    child.stderr.on("data", (chunk) => (stderr += chunk.toString("utf8")));
    child.on("error", (error: NodeJS.ErrnoException) =>
      resolve({ code: null, stdout, stderr: error.message, notFound: error.code === "ENOENT" }),
    );
    child.on("close", (code) => resolve({ code, stdout, stderr, notFound: false }));
  });
}

export async function findCli(configured: string): Promise<Cli | undefined> {
  for (const parts of candidateCommands(configured)) {
    const result = await run(parts, ["--version"]);
    const version = result.code === 0 ? parseVersion(result.stdout) : undefined;
    if (version) {
      return { parts, version };
    }
  }
  return undefined;
}

export function convertFile(cli: Cli, markdownPath: string, pdfPath: string): Promise<RunResult> {
  return run(cli.parts, [markdownPath, "-o", pdfPath, "--no-open"]);
}

export async function findPython(): Promise<string | undefined> {
  for (const command of ["python", "py", "python3"]) {
    const result = await run([command], ["--version"]);
    if (result.code === 0 && /Python 3\.(\d+)/.test(result.stdout + result.stderr)) {
      return command;
    }
  }
  return undefined;
}
