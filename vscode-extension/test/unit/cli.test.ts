import assert from "node:assert/strict";
import { test } from "node:test";
import { candidateCommands, describeFailure, isOlder, lastLine, parseVersion, run, splitCommand } from "../../src/cli";

test("splitCommand handles quotes and extra spaces", () => {
  assert.deepEqual(splitCommand("md2textbook"), ["md2textbook"]);
  assert.deepEqual(splitCommand('python  -m "my tool"'), ["python", "-m", "my tool"]);
  assert.deepEqual(splitCommand("   "), []);
});

test("candidateCommands tries the configured command first and drops duplicates", () => {
  const list = candidateCommands("md2textbook");
  assert.deepEqual(list[0], ["md2textbook"]);
  assert.deepEqual(list[1], ["python", "-m", "md2textbook"]);
  const same = candidateCommands("python -m md2textbook");
  assert.equal(same.filter((c) => c.join(" ") === "python -m md2textbook").length, 1);
});

test("parseVersion reads the CLI banner", () => {
  assert.equal(parseVersion("md2textbook 0.1.3\n"), "0.1.3");
  assert.equal(parseVersion("something else"), undefined);
});

test("isOlder compares dotted versions numerically", () => {
  assert.equal(isOlder("0.1.2", "0.1.3"), true);
  assert.equal(isOlder("0.1.3", "0.1.3"), false);
  assert.equal(isOlder("0.10.0", "0.9.9"), false);
  assert.equal(isOlder("1.0", "0.9.9"), false);
});

test("describeFailure prefers the last stderr line", () => {
  const result = { code: 1, stdout: "", stderr: "Traceback...\nValueError: bad link\n", notFound: false };
  assert.equal(describeFailure(result), "ValueError: bad link");
  assert.equal(lastLine(""), "");
  assert.match(describeFailure({ code: 2, stdout: "", stderr: "", notFound: false }), /code 2/);
});

test("run reports a missing program instead of throwing", async () => {
  const result = await run(["definitely-not-a-real-program-md2textbook"], []);
  assert.equal(result.notFound, true);
  assert.equal(result.code, null);
});
