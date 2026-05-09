import { config } from "dotenv";
import { resolve } from "path";
import { execSync } from "child_process";

config({ path: resolve("../../.env") });

const key = process.env.TRIGGER_SECRET_KEY;
console.log("TRIGGER_SECRET_KEY present:", !!key);
if (key) console.log("Key prefix:", key.slice(0, 12) + "...");

// Try whoami
try {
  const result = execSync("npx trigger.dev@latest whoami", {
    env: process.env,
    timeout: 15000,
    encoding: "utf8",
  });
  console.log("whoami:", result);
} catch (e) {
  console.log("whoami error:", e.stdout, e.stderr);
}
