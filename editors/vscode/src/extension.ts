import * as vscode from 'vscode';

import { DiagnosticsRunner } from './diagnostics';
import { pythonPath, resolveInterpreter } from './interpreter';
import {
  ArtCompletionProvider,
  ArtDefinitionProvider,
  ArtDocumentSymbolProvider,
  ArtHoverProvider,
} from './providers';

const ART: vscode.DocumentSelector = { language: 'art', scheme: 'file' };

const MISSING_INTERPRETER =
  'Could not find the ART interpreter (run.py). Set "art.interpreterPath" to your art-language checkout.';

function quote(value: string): string {
  return /[\s"']/.test(value) ? `"${value}"` : value;
}

async function runFile(extensionPath: string, terminal: { value?: vscode.Terminal }) {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'art') {
    void vscode.window.showErrorMessage('Open an ART file to run it.');
    return;
  }

  if (editor.document.isDirty) {
    await editor.document.save();
  }

  const paths = resolveInterpreter(editor.document, extensionPath);
  if (!paths) {
    void vscode.window.showErrorMessage(MISSING_INTERPRETER);
    return;
  }

  if (!terminal.value || terminal.value.exitStatus !== undefined) {
    terminal.value = vscode.window.createTerminal({ name: 'ART', cwd: paths.root });
  }

  terminal.value.show(true);
  terminal.value.sendText(
    `${quote(pythonPath(editor.document))} ${quote(paths.runScript)} ${quote(
      editor.document.uri.fsPath
    )}`
  );
}

function finalNewlineEdits(document: vscode.TextDocument): vscode.TextEdit[] {
  if (
    document.languageId !== 'art' ||
    !vscode.workspace
      .getConfiguration('art', document.uri)
      .get<boolean>('insertFinalNewlineOnSave', true)
  ) {
    return [];
  }

  const last = document.lineAt(document.lineCount - 1);
  if (last.isEmptyOrWhitespace) {
    return last.text.length === 0 ? [] : [vscode.TextEdit.delete(last.range)];
  }

  return [vscode.TextEdit.insert(last.range.end, '\n')];
}

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel('ART');
  const runner = new DiagnosticsRunner(context.extensionPath, output);
  const terminal: { value?: vscode.Terminal } = {};

  context.subscriptions.push(
    output,
    runner,
    vscode.languages.registerDocumentSymbolProvider(ART, new ArtDocumentSymbolProvider()),
    vscode.languages.registerDefinitionProvider(ART, new ArtDefinitionProvider()),
    vscode.languages.registerHoverProvider(ART, new ArtHoverProvider()),
    vscode.languages.registerCompletionItemProvider(ART, new ArtCompletionProvider(), '.'),
    vscode.commands.registerCommand('art.runFile', () => runFile(context.extensionPath, terminal)),
    vscode.commands.registerCommand('art.checkFile', async () => {
      const document = vscode.window.activeTextEditor?.document;
      if (document) {
        await runner.check(document);
      }
    }),
    vscode.workspace.onDidOpenTextDocument((document) => runner.schedule(document)),
    vscode.workspace.onDidCloseTextDocument((document) => runner.forget(document)),
    vscode.workspace.onDidSaveTextDocument((document) => void runner.check(document)),
    vscode.workspace.onWillSaveTextDocument((event) => {
      event.waitUntil(Promise.resolve(finalNewlineEdits(event.document)));
    }),
    vscode.workspace.onDidChangeTextDocument((event) => {
      const mode = vscode.workspace
        .getConfiguration('art', event.document.uri)
        .get<string>('diagnostics.run', 'onType');
      if (mode === 'onType') {
        runner.schedule(event.document);
      }
    }),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (!event.affectsConfiguration('art')) {
        return;
      }
      for (const document of vscode.workspace.textDocuments) {
        runner.schedule(document);
      }
    })
  );

  for (const document of vscode.workspace.textDocuments) {
    runner.schedule(document);
  }
}

export function deactivate(): void {
  // Everything is disposed through context.subscriptions.
}
