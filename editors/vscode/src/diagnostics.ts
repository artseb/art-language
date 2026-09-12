/** Lex/parse diagnostics, produced by the interpreter itself. */
import * as vscode from 'vscode';

import { pythonPath, resolveInterpreter, runPython } from './interpreter';

interface RawDiagnostic {
  line: number;
  column: number;
  message: string;
  stage: string;
  severity: string;
}

/** Highlight the token at (line, column), or the rest of the line. */
function rangeFor(document: vscode.TextDocument, raw: RawDiagnostic): vscode.Range {
  const line = Math.min(Math.max(raw.line - 1, 0), Math.max(document.lineCount - 1, 0));
  const textLine = document.lineAt(line);
  const character = Math.min(Math.max(raw.column - 1, 0), textLine.text.length);
  const position = new vscode.Position(line, character);

  const wordRange = document.getWordRangeAtPosition(position);
  if (wordRange) {
    return wordRange;
  }

  if (character >= textLine.text.length) {
    // End of line (typically "unexpected end of input"): point at the
    // last non-whitespace character so the squiggle stays visible.
    const start = Math.max(textLine.firstNonWhitespaceCharacterIndex, 0);
    return new vscode.Range(
      new vscode.Position(line, Math.min(start, Math.max(textLine.text.trimEnd().length - 1, 0))),
      textLine.range.end
    );
  }

  return new vscode.Range(position, new vscode.Position(line, character + 1));
}

export class DiagnosticsRunner {
  private readonly collection: vscode.DiagnosticCollection;
  private readonly timers = new Map<string, NodeJS.Timeout>();

  constructor(
    private readonly extensionPath: string,
    private readonly output: vscode.OutputChannel
  ) {
    this.collection = vscode.languages.createDiagnosticCollection('art');
  }

  get diagnostics(): vscode.DiagnosticCollection {
    return this.collection;
  }

  dispose(): void {
    for (const timer of this.timers.values()) {
      clearTimeout(timer);
    }
    this.timers.clear();
    this.collection.dispose();
  }

  forget(document: vscode.TextDocument): void {
    this.collection.delete(document.uri);
    const key = document.uri.toString();
    const timer = this.timers.get(key);
    if (timer) {
      clearTimeout(timer);
      this.timers.delete(key);
    }
  }

  schedule(document: vscode.TextDocument): void {
    if (document.languageId !== 'art') {
      return;
    }

    const config = vscode.workspace.getConfiguration('art', document.uri);
    if (!config.get<boolean>('diagnostics.enabled', true)) {
      this.collection.delete(document.uri);
      return;
    }

    const key = document.uri.toString();
    const existing = this.timers.get(key);
    if (existing) {
      clearTimeout(existing);
    }

    const delay = Math.max(config.get<number>('diagnostics.delay', 300), 0);
    this.timers.set(
      key,
      setTimeout(() => {
        this.timers.delete(key);
        void this.check(document);
      }, delay)
    );
  }

  async check(document: vscode.TextDocument): Promise<void> {
    if (document.languageId !== 'art') {
      return;
    }

    const paths = resolveInterpreter(document, this.extensionPath);
    if (!paths) {
      // Without the interpreter there is nothing to check against;
      // highlighting and the rest of the extension still work.
      this.collection.delete(document.uri);
      return;
    }

    let result;
    try {
      result = await runPython(
        pythonPath(document),
        [...paths.checkCommand, '--stdin'],
        paths.root,
        document.getText()
      );
    } catch (error) {
      this.output.appendLine(`Failed to run the syntax checker: ${String(error)}`);
      return;
    }

    if (result.stderr.trim()) {
      this.output.appendLine(result.stderr.trim());
    }

    let parsed: { diagnostics: RawDiagnostic[] };
    try {
      parsed = JSON.parse(result.stdout) as { diagnostics: RawDiagnostic[] };
    } catch {
      this.output.appendLine(`Unexpected checker output: ${result.stdout}`);
      return;
    }

    this.collection.set(
      document.uri,
      parsed.diagnostics.map((raw) => {
        const diagnostic = new vscode.Diagnostic(
          rangeFor(document, raw),
          raw.message,
          raw.severity === 'warning'
            ? vscode.DiagnosticSeverity.Warning
            : vscode.DiagnosticSeverity.Error
        );
        diagnostic.source = `art (${raw.stage})`;
        return diagnostic;
      })
    );
  }
}
