import { spawn } from "node:child_process";
import path from "node:path";

const command = process.argv[2];
if (!new Set(["dev", "build", "start"]).has(command)) {
  process.stderr.write("Usage: node scripts/run-vinext.mjs <dev|build|start>\n");
  process.exit(2);
}

const child = spawn(
  process.execPath,
  [path.join("node_modules", "vinext", "dist", "cli.js"), command, ...process.argv.slice(3)],
  {
    stdio: "inherit",
    env: {
      ...process.env,
      WRANGLER_LOG_PATH:
        process.env.WRANGLER_LOG_PATH ?? path.join(".wrangler", "wrangler.log"),
    },
  },
);

child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  else process.exit(code ?? 1);
});
