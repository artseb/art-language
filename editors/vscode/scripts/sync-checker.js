/**
 * Copy tools/art_check.py into the extension so a packaged .vsix can
 * report diagnostics even against an interpreter checkout that predates
 * the script. The copy is generated, never edited by hand, and is not
 * committed - tools/art_check.py is the only source of truth.
 */
const fs = require('fs');
const path = require('path');

const source = path.resolve(__dirname, '..', '..', '..', 'tools', 'art_check.py');
const targetDir = path.resolve(__dirname, '..', 'python');
const target = path.join(targetDir, 'art_check.py');

if (!fs.existsSync(source)) {
  console.error(`Cannot find ${source}; run this from the art-language repository.`);
  process.exit(1);
}

fs.mkdirSync(targetDir, { recursive: true });
fs.copyFileSync(source, target);
console.log(`Copied ${path.relative(process.cwd(), source)} -> ${path.relative(process.cwd(), target)}`);
