import { promises as fs } from "node:fs";
import * as path from "node:path";

export function pdfPathFor(markdownPath: string): string {
  const { dir, name } = path.parse(markdownPath);
  return path.join(dir, `${name}.pdf`);
}

export async function isLocked(pdfPath: string): Promise<boolean> {
  try {
    const handle = await fs.open(pdfPath, "r+");
    await handle.close();
    return false;
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    return code === "EBUSY" || code === "EPERM" || code === "EACCES";
  }
}
