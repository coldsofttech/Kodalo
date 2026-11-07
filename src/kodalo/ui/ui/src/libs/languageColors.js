// Colors GitHub uses for the most common languages; any other language gets one from FALLBACK.
const KNOWN = new Map([
  ['Python', '#3572A5'],
  ['JavaScript', '#f1e05a'],
  ['TypeScript', '#3178c6'],
  ['Java', '#b07219'],
  ['Kotlin', '#A97BFF'],
  ['Swift', '#F05138'],
  ['Go', '#00ADD8'],
  ['Rust', '#dea584'],
  ['C', '#555555'],
  ['C++', '#f34b7d'],
  ['C#', '#178600'],
  ['Ruby', '#701516'],
  ['PHP', '#4F5D95'],
  ['Dart', '#00B4AB'],
  ['Shell', '#89e051'],
  ['PowerShell', '#012456'],
  ['HTML', '#e34c26'],
  ['CSS', '#563d7c'],
  ['SCSS', '#c6538c'],
  ['Dockerfile', '#384d54'],
  ['HCL', '#844FBA'],
  ['Makefile', '#427819'],
  ['Lua', '#000080'],
  ['Elixir', '#6e4a7e'],
  ['Scala', '#c22d40'],
  ['Batchfile', '#C1F12E'],
  ['Jupyter Notebook', '#DA5B0B'],
]);

const FALLBACK = ['#8957e5', '#db61a2', '#3fb950', '#d29922', '#58a6ff', '#f78166', '#79c0ff'];

/** @param {string} name */
export function languageColor(name) {
  const known = KNOWN.get(name);
  if (known) return known;
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) % FALLBACK.length;
  return FALLBACK.at(hash) ?? KNOWN.get('Python');
}
