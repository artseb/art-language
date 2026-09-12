/** Locating the ART interpreter on disk and shelling out to it. */
import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

export interface InterpreterPaths {
  /** Directory containing run.py and the `art` package. */
  root: string;
  runScript: string;
  /** Arguments that run the syntax checker, before its own flags. */
  checkCommand: string[];
}

function looksLikeInterpreterRoot(dir: string): boolean {
  return (
    fs.existsSync(path.join(dir, 'run.py')) &&
    fs.existsSync(path.join(dir, 'art', 'lexer.py'))
  );
}

/**
 * Walk up from `start` looking for the interpreter checkout, so the
 * extension works both in the interpreter repo itself and in a project
 * that merely contains .art files nested below it.
 */
function findUpwards(start: string): string | undefined {
  let dir = start;
  for (;;) {
    if (looksLikeInterpreterRoot(dir)) {
      return dir;
    }
    const parent = path.dirname(dir);
    if (parent === dir) {
      return undefined;
    }
    dir = parent;
  }
}

/**
 * Resolve the interpreter for `document`: the configured path first, then
 * the document's own directory and its ancestors, then the workspace
 * folders, and finally the copy bundled beside this extension when it is
 * installed from the interpreter repo.
 */
export function resolveInterpreter(
  document: vscode.TextDocument | undefined,
  extensionPath: string
): InterpreterPaths | undefined {
  const configured = vscode.workspace
    .getConfiguration('art', document?.uri)
    .get<string>('interpreterPath', '')
    .trim();

  const candidates: string[] = [];

  if (configured) {
    const asPath = path.isAbsolute(configured)
      ? configured
      : path.resolve(vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '', configured);
    candidates.push(asPath.endsWith('.py') ? path.dirname(asPath) : asPath);
  }

  if (document && document.uri.scheme === 'file') {
    const found = findUpwards(path.dirname(document.uri.fsPath));
    if (found) {
      candidates.push(found);
    }
  }

  for (const folder of vscode.workspace.workspaceFolders ?? []) {
    candidates.push(folder.uri.fsPath);
  }

  // editors/vscode/ -> repository root
  candidates.push(path.resolve(extensionPath, '..', '..'));

  for (const candidate of candidates) {
    if (looksLikeInterpreterRoot(candidate)) {
      return {
        root: candidate,
        runScript: path.join(candidate, 'run.py'),
        checkCommand: checkCommandFor(candidate, extensionPath),
      };
    }
  }

  return undefined;
}

/**
 * Prefer the checker from the interpreter checkout, so it always matches
 * the interpreter being used; fall back to the copy bundled with the
 * extension for checkouts that predate it.
 */
function checkCommandFor(root: string, extensionPath: string): string[] {
  const inRepo = path.join(root, 'tools', 'art_check.py');
  if (fs.existsSync(inRepo)) {
    return [inRepo];
  }
  return [path.join(extensionPath, 'python', 'art_check.py'), '--root', root];
}

export function pythonPath(document?: vscode.TextDocument): string {
  return (
    vscode.workspace
      .getConfiguration('art', document?.uri)
      .get<string>('pythonPath', 'python3')
      .trim() || 'python3'
  );
}

export interface ProcessResult {
  stdout: string;
  stderr: string;
  code: number | null;
}

/** Run a Python script, feeding it `stdin` and collecting its output. */
export function runPython(
  python: string,
  args: string[],
  cwd: string,
  stdin?: string,
  token?: vscode.CancellationToken
): Promise<ProcessResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(python, args, { cwd });
    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });

    child.on('error', reject);
    child.on('close', (code) => resolve({ stdout, stderr, code }));

    token?.onCancellationRequested(() => child.kill());

    child.stdin.end(stdin ?? '');
  });
}
