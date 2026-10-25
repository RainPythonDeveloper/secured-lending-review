import { readFileSync } from 'node:fs';

const SANDBOX_FIXTURE_DIRECTORY = new URL('./tbc-sandbox/', import.meta.url);

export function readSandboxFixtureText(fileName: string): string {
  return readFileSync(new URL(fileName, SANDBOX_FIXTURE_DIRECTORY), 'utf8');
}

export function loadSandboxFixture(fileName: string): unknown {
  const fixture: unknown = JSON.parse(readSandboxFixtureText(fileName));
  return fixture;
}
