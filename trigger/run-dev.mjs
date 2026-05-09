import { config } from "dotenv";
import { spawn } from "child_process";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "../../.env") });

const proc = spawn("npx", ["trigger.dev@latest", "dev"], {
  stdio: "inherit",
  env: process.env,
  shell: true,
});

proc.on("exit", (code) => process.exit(code ?? 0));
