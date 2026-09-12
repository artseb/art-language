/** Outline, go-to-definition, completion and hover, all driven by the
 * regex scan in scanner.ts plus the static tables in language.ts. */
import * as vscode from 'vscode';

import {
  BUILTINS,
  BUILTINS_BY_NAME,
  Documented,
  KEYWORDS,
  KEYWORDS_BY_NAME,
  TYPE_NAMES,
  TYPE_NAMES_BY_NAME,
} from './language';
import { ArtSymbol, ArtSymbolKind, flatten, scanDocument } from './scanner';

const SYMBOL_KINDS: Record<ArtSymbolKind, vscode.SymbolKind> = {
  class: vscode.SymbolKind.Class,
  enum: vscode.SymbolKind.Enum,
  enumMember: vscode.SymbolKind.EnumMember,
  function: vscode.SymbolKind.Function,
  method: vscode.SymbolKind.Method,
  constructor: vscode.SymbolKind.Constructor,
  accessor: vscode.SymbolKind.Property,
  operator: vscode.SymbolKind.Operator,
  variable: vscode.SymbolKind.Variable,
  field: vscode.SymbolKind.Field,
  import: vscode.SymbolKind.Module,
};

const COMPLETION_KINDS: Record<ArtSymbolKind, vscode.CompletionItemKind> = {
  class: vscode.CompletionItemKind.Class,
  enum: vscode.CompletionItemKind.Enum,
  enumMember: vscode.CompletionItemKind.EnumMember,
  function: vscode.CompletionItemKind.Function,
  method: vscode.CompletionItemKind.Method,
  constructor: vscode.CompletionItemKind.Constructor,
  accessor: vscode.CompletionItemKind.Property,
  operator: vscode.CompletionItemKind.Operator,
  variable: vscode.CompletionItemKind.Variable,
  field: vscode.CompletionItemKind.Field,
  import: vscode.CompletionItemKind.Module,
};

function selectionRange(symbol: ArtSymbol): vscode.Range {
  return new vscode.Range(
    new vscode.Position(symbol.line, symbol.startColumn),
    new vscode.Position(symbol.line, symbol.endColumn)
  );
}

function fullRange(symbol: ArtSymbol): vscode.Range {
  return new vscode.Range(
    new vscode.Position(symbol.line, symbol.startColumn),
    new vscode.Position(symbol.endLine, Number.MAX_SAFE_INTEGER)
  );
}

export class ArtDocumentSymbolProvider implements vscode.DocumentSymbolProvider {
  provideDocumentSymbols(document: vscode.TextDocument): vscode.DocumentSymbol[] {
    const convert = (symbol: ArtSymbol): vscode.DocumentSymbol => {
      const item = new vscode.DocumentSymbol(
        symbol.name,
        symbol.detail,
        SYMBOL_KINDS[symbol.kind],
        fullRange(symbol),
        selectionRange(symbol)
      );
      item.children = symbol.children.map(convert);
      return item;
    };

    return scanDocument(document.getText()).map(convert);
  }
}

export class ArtDefinitionProvider implements vscode.DefinitionProvider {
  provideDefinition(
    document: vscode.TextDocument,
    position: vscode.Position
  ): vscode.Location[] {
    const wordRange = document.getWordRangeAtPosition(position);
    if (!wordRange) {
      return [];
    }

    const word = document.getText(wordRange);
    return flatten(scanDocument(document.getText()))
      .filter((symbol) => symbol.name === word)
      .map((symbol) => new vscode.Location(document.uri, selectionRange(symbol)));
  }
}

function documentedItem(
  entry: Documented,
  kind: vscode.CompletionItemKind
): vscode.CompletionItem {
  const item = new vscode.CompletionItem(entry.name, kind);
  item.detail = entry.signature;
  item.documentation = new vscode.MarkdownString(entry.documentation);
  return item;
}

export class ArtCompletionProvider implements vscode.CompletionItemProvider {
  provideCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position
  ): vscode.CompletionItem[] {
    const linePrefix = document.lineAt(position.line).text.slice(0, position.character);

    // After `:` or `->` only a type name can follow.
    if (/(:|->)\s*\w*$/.test(linePrefix)) {
      return TYPE_NAMES.map((type) =>
        documentedItem(type, vscode.CompletionItemKind.TypeParameter)
      );
    }

    const items: vscode.CompletionItem[] = [];

    for (const keyword of KEYWORDS) {
      items.push(documentedItem(keyword, vscode.CompletionItemKind.Keyword));
    }

    for (const builtin of BUILTINS) {
      const item = documentedItem(builtin, vscode.CompletionItemKind.Function);
      item.insertText = new vscode.SnippetString(`${builtin.name}($0)`);
      items.push(item);
    }

    const seen = new Set<string>();
    for (const symbol of flatten(scanDocument(document.getText()))) {
      if (symbol.line === position.line || seen.has(`${symbol.kind}:${symbol.name}`)) {
        continue;
      }
      seen.add(`${symbol.kind}:${symbol.name}`);

      const item = new vscode.CompletionItem(symbol.name, COMPLETION_KINDS[symbol.kind]);
      item.detail = symbol.detail;
      items.push(item);
    }

    return items;
  }
}

export class ArtHoverProvider implements vscode.HoverProvider {
  provideHover(
    document: vscode.TextDocument,
    position: vscode.Position
  ): vscode.Hover | undefined {
    const wordRange = document.getWordRangeAtPosition(position);
    if (!wordRange) {
      return undefined;
    }

    const word = document.getText(wordRange);
    const entry =
      BUILTINS_BY_NAME.get(word) ?? KEYWORDS_BY_NAME.get(word) ?? TYPE_NAMES_BY_NAME.get(word);

    if (entry) {
      const markdown = new vscode.MarkdownString();
      markdown.appendCodeblock(entry.signature ?? entry.name, 'art');
      markdown.appendMarkdown(entry.documentation);
      return new vscode.Hover(markdown, wordRange);
    }

    const declaration = flatten(scanDocument(document.getText())).find(
      (symbol) => symbol.name === word
    );
    if (!declaration) {
      return undefined;
    }

    const markdown = new vscode.MarkdownString();
    markdown.appendCodeblock(declaration.detail, 'art');
    return new vscode.Hover(markdown, wordRange);
  }
}
