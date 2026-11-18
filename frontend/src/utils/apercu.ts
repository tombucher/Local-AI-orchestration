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
          // Un script différé attend le DOM : en ligne, il doit passer en fin de page
          if (/\b(defer|type=["']module["'])/i.test(avant + apres)) {
            scriptsDiffere.push(`<script>/* ${chemin} */\n${sur}</script>`);
            return '';
          }
          return `<script>/* ${chemin} */\n${sur}</script>`;
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
