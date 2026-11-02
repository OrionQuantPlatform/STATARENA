import { execFileSync } from "node:child_process";
import { copyFile, lstat, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const inputs = ["dashboard/frontend", "dashboard/backend", "dashboard/shared", "dashboard/package.json", "dashboard/bun.lock", "data/computed/dashboard/index.json"];
const excluded = /(?:^|\/)(?:node_modules|\.next(?:-dev)?|\.vercel|\.env(?:\.[^/]*)?)(?:\/|$)/i;
export async function packageSource({ root, destination, revision, tracked }) {
  if (!/^[a-f0-9]{40}$/i.test(revision)) throw new Error("Invalid Git revision");
  const files = tracked.filter((file) => inputs.some((input) => file === input || file.startsWith(input + "/")) && !excluded.test(file) && !file.split("/").some((part) => part === "." || part === ".."));
  if (!files.includes("data/computed/dashboard/index.json") || !files.includes("dashboard/frontend/package.json")) throw new Error("Required deployment inputs are missing");
  await mkdir(destination);
  for (const file of files) {
    const source = path.join(root, ...file.split("/"));
    const target = path.join(destination, ...file.split("/"));
    if (!(await lstat(source)).isFile()) throw new Error(`Not a regular file: ${file}`);
    await mkdir(path.dirname(target), { recursive: true });
    await copyFile(source, target);
  }
  await writeFile(path.join(destination, "dashboard/shared/data-revision.js"), `export const packagedDataRevision = "${revision}";\n`);
  return { destination, revision, files: files.length };
}
async function main() {
  const destinationArgument = process.argv[2];
  if (!destinationArgument) throw new Error("Usage: node dashboard/scripts/prepare-vercel-source.mjs <new-output-directory>");
  const root = execFileSync("git", ["rev-parse", "--show-toplevel"], { encoding: "utf8" }).trim();
  const revision = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim();
  try {
    execFileSync("git", ["diff", "--quiet", "HEAD", "--", ...inputs], { cwd: root });
  } catch {
    throw new Error("Commit the deployment inputs before packaging them");
  }
  const tracked = execFileSync("git", ["ls-files", "-z", "--", ...inputs], { cwd: root, maxBuffer: 16 * 1024 * 1024 }).toString("utf8").split("\0").filter(Boolean);
  const result = await packageSource({ root, destination: path.resolve(destinationArgument), revision, tracked });
  console.log(JSON.stringify(result));
}
if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) await main();
