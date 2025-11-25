#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const run = (command, args) => {
  console.log(`> ${command} ${args.join(" ")}`);
  const result = spawnSync(command, args, { stdio: "inherit", shell: true });
  if (result.error) {
    console.error(result.error);
  }
  if (result.status !== 0) {
    console.error(`Command ${command} ${args.join(" ")} exited with status ${result.status}`);
    process.exit(result.status ?? 1);
  }
};

const filteredArgs = process.argv.slice(2).filter((arg) => arg !== "--ci");

run("npm", ["run", "generate:openapi:ts"]);
run("npx", ["tsc", "--project", "tsconfig.contracts.json", "--noEmit", ...filteredArgs]);
