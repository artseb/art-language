/**
 * A deliberately small, regex-based scan of an ART document.
 *
 * The real grammar lives in the Python interpreter; re-implementing it in
 * TypeScript would mean two parsers to keep in sync. Everything that needs
 * to be *correct* (errors, line/column info) is delegated to the
 * interpreter through tools/art_check.py. This scan only powers the
 * best-effort editor conveniences - outline, go-to-definition and
 * completion - where being approximate on a half-typed line is fine.
 */

export type ArtSymbolKind =
  | 'class'
  | 'enum'
  | 'enumMember'
  | 'function'
  | 'method'
  | 'constructor'
  | 'accessor'
  | 'operator'
  | 'variable'
  | 'field'
  | 'import';

export interface ArtSymbol {
  name: string;
  kind: ArtSymbolKind;
  detail: string;
  line: number;
  startColumn: number;
  endColumn: number;
  /** Last line of the symbol's body, or `line` when it has none. */
  endLine: number;
  children: ArtSymbol[];
}

interface OpenContainer {
  symbol: ArtSymbol;
  /** Brace depth the container's body sits at. */
  depth: number;
}

const CLASS_RE = /^\s*(?:(?:local|static)\s+)*class\s+([A-Za-z_]\w*)/;
const ENUM_RE = /^\s*enum\s+([A-Za-z_]\w*)/;
const FUN_RE = /^\s*(?:(?:local|static)\s+)*fun\s+([A-Za-z_]\w*)\s*\(([^)]*)\)/;
const ACCESSOR_RE = /^\s*(get|set)\s+([A-Za-z_]\w*)\s*\(/;
const OPERATOR_RE = /^\s*operator\s*([^\s(]+)\s*\(/;
const VAR_RE = /^\s*(?:(local|static)\s+)?([A-Za-z_]\w*)\s*=(?!=)/;
const IMPORT_RE = /^\s*import\s+"([^"]*)"(?:\s+as\s+([A-Za-z_]\w*))?/;
const ENUM_MEMBER_RE = /^\s*([A-Za-z_]\w*)\s*(?:\([^)]*\))?\s*[,}]?\s*$/;

/**
 * Blank out comments and string bodies so later regexes can't match inside
 * them, while keeping every character position intact.
 */
export function stripNoise(lines: string[]): string[] {
  const out: string[] = [];
  let inBlockComment = 0;

  for (const raw of lines) {
    const chars = raw.split('');
    let i = 0;

    while (i < chars.length) {
      if (inBlockComment > 0) {
        if (chars[i] === '/' && chars[i + 1] === '*') {
          inBlockComment++;
          chars[i] = ' ';
          chars[i + 1] = ' ';
          i += 2;
          continue;
        }
        if (chars[i] === '*' && chars[i + 1] === '/') {
          inBlockComment--;
          chars[i] = ' ';
          chars[i + 1] = ' ';
          i += 2;
          continue;
        }
        chars[i] = ' ';
        i++;
        continue;
      }

      if (chars[i] === '/' && chars[i + 1] === '/') {
        for (let j = i; j < chars.length; j++) {
          chars[j] = ' ';
        }
        break;
      }

      if (chars[i] === '/' && chars[i + 1] === '*') {
        inBlockComment = 1;
        chars[i] = ' ';
        chars[i + 1] = ' ';
        i += 2;
        continue;
      }

      if (chars[i] === '"') {
        i++;
        while (i < chars.length && chars[i] !== '"') {
          if (chars[i] === '\\') {
            chars[i] = ' ';
            i++;
          }
          if (i < chars.length) {
            chars[i] = ' ';
            i++;
          }
        }
        i++;
        continue;
      }

      i++;
    }

    out.push(chars.join(''));
  }

  return out;
}

function makeSymbol(
  name: string,
  kind: ArtSymbolKind,
  detail: string,
  line: number,
  text: string
): ArtSymbol {
  const startColumn = Math.max(text.indexOf(name), 0);
  return {
    name,
    kind,
    detail,
    line,
    startColumn,
    endColumn: startColumn + name.length,
    endLine: line,
    children: [],
  };
}

/** Collect the declarations of a document, nested by braces. */
export function scanDocument(source: string): ArtSymbol[] {
  const lines = stripNoise(source.split(/\r?\n/));
  const roots: ArtSymbol[] = [];
  const stack: OpenContainer[] = [];
  let depth = 0;

  const currentContainer = (): ArtSymbol | undefined =>
    stack.length > 0 ? stack[stack.length - 1].symbol : undefined;

  const push = (symbol: ArtSymbol, opensBody: boolean) => {
    const parent = currentContainer();
    if (parent) {
      parent.children.push(symbol);
    } else {
      roots.push(symbol);
    }
    if (opensBody) {
      stack.push({ symbol, depth });
    }
  };

  for (let line = 0; line < lines.length; line++) {
    const text = lines[line];
    const inClassBody = currentContainer()?.kind === 'class';
    const inEnumBody = currentContainer()?.kind === 'enum';

    let match: RegExpMatchArray | null;

    if ((match = text.match(CLASS_RE))) {
      push(makeSymbol(match[1], 'class', 'class', line, text), true);
    } else if ((match = text.match(ENUM_RE))) {
      push(makeSymbol(match[1], 'enum', 'enum', line, text), true);
    } else if ((match = text.match(FUN_RE))) {
      const name = match[1];
      const signature = `fun ${name}(${match[2].trim()})`;
      let kind: ArtSymbolKind = 'function';
      if (inClassBody || inEnumBody) {
        kind = name === currentContainer()?.name ? 'constructor' : 'method';
      }
      push(makeSymbol(name, kind, signature, line, text), true);
    } else if ((match = text.match(ACCESSOR_RE))) {
      push(
        makeSymbol(match[2], 'accessor', `${match[1]} ${match[2]}()`, line, text),
        true
      );
    } else if ((match = text.match(OPERATOR_RE))) {
      push(
        makeSymbol(match[1], 'operator', `operator ${match[1]}`, line, text),
        true
      );
    } else if ((match = text.match(IMPORT_RE))) {
      const alias = match[2] ?? match[1];
      push(makeSymbol(alias, 'import', `import "${match[1]}"`, line, text), false);
    } else if (inEnumBody && (match = text.match(ENUM_MEMBER_RE))) {
      push(makeSymbol(match[1], 'enumMember', 'enum member', line, text), false);
    } else if ((match = text.match(VAR_RE))) {
      // A bare `name = value` inside a body is far more likely to be a
      // reassignment than a declaration, so only the declared forms
      // (`local`/`static`) and top-level assignments become symbols.
      if (match[1] || depth === 0) {
        const modifier = match[1] ? `${match[1]} ` : '';
        const kind: ArtSymbolKind = inClassBody ? 'field' : 'variable';
        push(makeSymbol(match[2], kind, `${modifier}${match[2]}`, line, text), false);
      }
    }

    for (const char of text) {
      if (char === '{') {
        depth++;
      } else if (char === '}') {
        depth = Math.max(depth - 1, 0);
        while (stack.length > 0 && stack[stack.length - 1].depth >= depth) {
          const closed = stack.pop();
          if (closed) {
            closed.symbol.endLine = line;
          }
        }
      }
    }
  }

  const lastLine = Math.max(lines.length - 1, 0);
  while (stack.length > 0) {
    const closed = stack.pop();
    if (closed) {
      closed.symbol.endLine = lastLine;
    }
  }

  return roots;
}

/** Depth-first flattening of `scanDocument`, parents before children. */
export function flatten(symbols: ArtSymbol[]): ArtSymbol[] {
  const out: ArtSymbol[] = [];
  const visit = (list: ArtSymbol[]) => {
    for (const symbol of list) {
      out.push(symbol);
      visit(symbol.children);
    }
  };
  visit(symbols);
  return out;
}
