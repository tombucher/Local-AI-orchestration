/**
 * Assemblage d'un aperçu : une page HTML et ses fichiers (CSS, JS) réunis en
 * un seul document pour un cadre isolé (srcdoc), qui ne peut pas aller
 * chercher styles.css ou app.js ailleurs. Utilisé par l'onglet Production
 * d'un projet et par l'écran de validation d'une tâche de code.
 */

export interface FichierApercu {
  path: string;
  content: string;
}

export interface MessageConsole {
  niveau: 'error' | 'warn' | 'log';
  message: string;
}

export const MARQUE_SONDE = 'apercu-orchestrateur';

/**
 * Sonde placée en tête de l'aperçu : elle relaie console et erreurs du site vers
 * l'orchestrateur (postMessage — le cadre reste isolé, sans accès à la page).
 */
const SONDE = `<script>(function(){
function envoyer(n,a){try{parent.postMessage({source:'${MARQUE_SONDE}',niveau:n,message:Array.prototype.map.call(a,function(x){try{return typeof x==='string'?x:x instanceof Error?(x.name+' : '+x.message):JSON.stringify(x)}catch(e){return String(x)}}).join(' ')},'*')}catch(e){}}
['error','warn','log'].forEach(function(n){var o=console[n];console[n]=function(){envoyer(n,arguments);o.apply(console,arguments)}});
window.addEventListener('error',function(e){envoyer('error',[e.message+(e.lineno?' (ligne '+e.lineno+')':'')])});
window.addEventListener('unhandledrejection',function(e){envoyer('error',['Promesse rejetée : '+(e.reason&&e.reason.message||e.reason)])});
})();</script>`;

const echapperRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * Assemble la page d'entrée avec ses feuilles de styles et scripts en ligne : un
 * cadre isolé (srcdoc) ne peut pas aller chercher styles.css ou app.js ailleurs.
 */
export const assemblerApercu = (entry: string, files: FichierApercu[]): string => {
  const parChemin = new Map(files.map((f) => [f.path.replace(/^\.\//, ''), f.content]));
  let html = parChemin.get(entry) ?? '';
  const scriptsDiffere: string[] = [];

  for (const [chemin, contenu] of parChemin) {
    const ref = `(?:\\./)?${echapperRegex(chemin)}`;
    if (chemin.endsWith('.css')) {
      html = html.replace(
        new RegExp(`<link\\b[^>]*href=["']${ref}["'][^>]*>`, 'gi'),
        () => `<style>/* ${chemin} */\n${contenu}</style>`,
      );
    } else if (/\.(m?js)$/.test(chemin)) {
      const sur = contenu.replace(/<\/script/gi, '<\\/script');
      html = html.replace(
        new RegExp(`<script\\b([^>]*)src=["']${ref}["']([^>]*)>\\s*</script>`, 'gi'),
        (_m, avant: string, apres: string) => {
          // Un module (import … from) doit le rester une fois en ligne
          const ouvrante = /type=["']module["']/i.test(avant + apres) ? '<script type="module">' : '<script>';
          // Un script différé attend le DOM : en ligne, il doit passer en fin de page
          if (/\b(defer|type=["']module["'])/i.test(avant + apres)) {
            scriptsDiffere.push(`${ouvrante}/* ${chemin} */\n${sur}</script>`);
            return '';
          }
          return `${ouvrante}/* ${chemin} */\n${sur}</script>`;
        },
      );
    }
  }
  if (scriptsDiffere.length) {
    html = /<\/body>/i.test(html)
      ? html.replace(/<\/body>/i, `${scriptsDiffere.join('\n')}\n</body>`)
      : `${html}\n${scriptsDiffere.join('\n')}`;
  }
  // La sonde passe avant tout script du site, pour capter ses premières erreurs
  return /<head[^>]*>/i.test(html) ? html.replace(/<head[^>]*>/i, (m) => `${m}\n${SONDE}`) : `${SONDE}\n${html}`;
};

// ------------------------------------------------- projet sans page HTML --

const PAGE_SECOURS = '__apercu__.html';
const IMPORT_NU = /(?:^|[\s;])(?:import\s+(?:[\w*{}\s,]+\s+from\s+)?|import\s*\(\s*|export\s+[\w*{}\s,]+\s+from\s+)["']([^"'./][^"']*)["']/g;

/** Nom de paquet d'un import nu : « three/addons/x.js » → « three », « @a/b/c » → « @a/b » */
const paquetDe = (specifier: string) => {
  const morceaux = specifier.split('/');
  return specifier.startsWith('@') ? morceaux.slice(0, 2).join('/') : morceaux[0];
};

/**
 * Carte d'imports pour les `import … from 'three'` : sans Node ni Vite, le
 * navigateur ne sait pas où trouver « three ». Les versions viennent du
 * package.json du projet s'il y en a un, les modules d'esm.sh.
 */
const carteImports = (files: FichierApercu[]): string | null => {
  const versions: Record<string, string> = {};
  const paquet = files.find((f) => f.path.endsWith('package.json'));
  if (paquet) {
    try {
      const deps = JSON.parse(paquet.content).dependencies ?? {};
      for (const [nom, version] of Object.entries(deps)) versions[nom] = String(version).replace(/^[\^~>=<\s]+/, '');
    } catch {
      // package.json illisible : versions les plus récentes
    }
  }
  const paquets = new Set<string>();
  for (const f of files) {
    if (!/\.(m?js|jsx)$/.test(f.path)) continue;
    for (const m of f.content.matchAll(IMPORT_NU)) {
      if (!/^(https?:|data:|blob:)/.test(m[1])) paquets.add(paquetDe(m[1]));
    }
  }
  if (paquets.size === 0) return null;
  const imports: Record<string, string> = {};
  for (const nom of paquets) {
    const url = `https://esm.sh/${nom}${versions[nom] ? `@${versions[nom]}` : ''}`;
    imports[nom] = url;
    imports[`${nom}/`] = `${url}/`;
  }
  return `<script type="importmap">${JSON.stringify({ imports })}</script>`;
};

const estModule = (code: string) => /^\s*(import|export)\s/m.test(code);

const ID_CHERCHE = /(?:getElementById\(\s*|querySelector(?:All)?\(\s*)["'`]#?([A-Za-z][\w-]*)["'`]/g;

/**
 * Les éléments qu'un script va chercher par leur id (`#scene`, `#perf-indicator`) :
 * sans page HTML, personne ne les fournit et le script s'arrête aussitôt.
 * Une toile pour ce qui ressemble à une scène de dessin, un bloc sinon.
 */
const elementsAttendus = (scripts: FichierApercu[]): string => {
  const ids = new Set<string>();
  for (const f of scripts) {
    for (const m of f.content.matchAll(ID_CHERCHE)) {
      // querySelector('.classe') ou 'div' : seuls les « #id » et getElementById comptent
      if (m[0].includes('querySelector') && !m[0].includes('#')) continue;
      ids.add(m[1]);
    }
  }
  return [...ids]
    .map((id) => (/canvas|scene|toile|webgl|gl$|stage/i.test(id) ? `<canvas id="${id}"></canvas>` : `<div id="${id}"></div>`))
    .join('\n');
};

/**
 * Ce qu'il faut assembler pour voir tourner le code. Sans page HTML (projet
 * planifié comme un projet Node/Vite : package.json, styles.css, app.js),
 * il n'y avait rien à ouvrir et le code se validait à l'aveugle : on fabrique
 * une page minimale qui charge les styles et les scripts.
 */
export const preparerApercu = (
  entry: string | null,
  files: FichierApercu[],
): { entry: string; files: FichierApercu[]; secours: boolean } | null => {
  const carte = carteImports(files);
  if (entry) {
    const page = files.find((f) => f.path === entry);
    if (!page || !carte || /type=["']importmap["']/i.test(page.content)) return { entry, files, secours: false };
    // Page existante, imports nus : la carte passe en tête, avant tout script
    const avecCarte = /<head[^>]*>/i.test(page.content)
      ? page.content.replace(/<head[^>]*>/i, (m) => `${m}\n${carte}`)
      : `${carte}\n${page.content}`;
    return { entry, files: files.map((f) => (f === page ? { ...f, content: avecCarte } : f)), secours: false };
  }
  const styles = files.filter((f) => /\.css$/.test(f.path));
  const scripts = files.filter((f) => /\.(m?js)$/.test(f.path));
  if (scripts.length === 0 && styles.length === 0) return null;
  const page = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aperçu</title>
${carte ?? ''}
${styles.map((f) => `<link rel="stylesheet" href="${f.path}">`).join('\n')}
</head>
<body>
${elementsAttendus(scripts)}
${scripts.map((f) => `<script ${estModule(f.content) ? 'type="module"' : 'defer'} src="${f.path}"></script>`).join('\n')}
</body>
</html>`;
  return { entry: PAGE_SECOURS, files: [...files, { path: PAGE_SECOURS, content: page }], secours: true };
};
