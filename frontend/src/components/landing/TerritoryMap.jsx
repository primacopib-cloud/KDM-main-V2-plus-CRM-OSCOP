import i18n from '@/i18n';

// Positions équirectangulaires (viewBox 1000x420, lon -90..70, lat 30..-35)
const T = [
  { code: 'GUADELOUPE', label: 'Guadeloupe', x: 178, y: 89, anchor: 'end', dx: -16 },
  { code: 'MARTINIQUE', label: 'Martinique', x: 196, y: 118, anchor: 'start', dx: 16 },
  { code: 'GUYANE', label: 'Guyane', x: 231, y: 168, anchor: 'start', dx: 16 },
  { code: 'MAYOTTE', label: 'Mayotte', x: 845, y: 277, anchor: 'end', dx: -16 },
  { code: 'REUNION', label: 'Réunion', x: 910, y: 331, anchor: 'end', dx: -16 },
];

const arc = (a, b) => {
  const mx = (a.x + b.x) / 2;
  const my = Math.min(a.y, b.y) - Math.max(40, Math.abs(a.x - b.x) * 0.18);
  return `M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}`;
};

// Carte interactive « réseau des Outre-mer » (accueil)
export const TerritoryMap = ({ zone, onSelect }) => (
  <div className="relative rounded-3xl overflow-hidden border border-white/[0.08] mb-6" data-testid="territory-map"
    style={{ background: 'radial-gradient(120% 140% at 50% -20%, rgba(217,179,90,0.10), rgba(20,8,38,0.4) 45%, rgba(12,4,24,0.6))' }}>
    <svg viewBox="0 0 1000 420" className="w-full h-auto block" role="img" aria-label="Carte des territoires d'Outre-mer">
      <defs>
        <linearGradient id="tm-arc" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#D9B35A" stopOpacity="0.05" />
          <stop offset="50%" stopColor="#D9B35A" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#D9B35A" stopOpacity="0.05" />
        </linearGradient>
        <radialGradient id="tm-glow">
          <stop offset="0%" stopColor="#D9B35A" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#D9B35A" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Grille méridiens / parallèles */}
      {[...Array(9)].map((_, i) => (
        <line key={`v${i}`} x1={100 + i * 100} y1="0" x2={100 + i * 100} y2="420" stroke="rgba(255,255,255,0.045)" strokeWidth="1" />
      ))}
      {[...Array(4)].map((_, i) => (
        <line key={`h${i}`} x1="0" y1={84 + i * 84} x2="1000" y2={84 + i * 84} stroke="rgba(255,255,255,0.045)" strokeWidth="1" />
      ))}
      {/* Équateur */}
      <line x1="0" y1="194" x2="1000" y2="194" stroke="rgba(217,179,90,0.18)" strokeWidth="1" strokeDasharray="6 8" />
      <text x="12" y="188" fontSize="11" fill="rgba(217,179,90,0.4)" fontStyle="italic">Équateur</text>

      {/* Arcs du réseau coopératif */}
      {[[0, 1], [1, 2], [2, 3], [3, 4], [0, 4]].map(([a, b]) => (
        <path key={`${a}-${b}`} d={arc(T[a], T[b])} fill="none" stroke="url(#tm-arc)" strokeWidth="1.5" strokeDasharray="4 6">
          <animate attributeName="stroke-dashoffset" from="60" to="0" dur="6s" repeatCount="indefinite" />
        </path>
      ))}

      {/* Étiquettes de bassins */}
      <text x="200" y="38" fontSize="13" fill="rgba(247,242,233,0.45)" textAnchor="middle" letterSpacing="3">ANTILLES · GUYANE</text>
      <text x="855" y="38" fontSize="13" fill="rgba(247,242,233,0.45)" textAnchor="middle" letterSpacing="3">OCÉAN INDIEN</text>

      {/* Marqueurs */}
      {T.map((t) => {
        const active = zone === t.code;
        return (
          <g key={t.code} onClick={() => onSelect(t.code)} style={{ cursor: 'pointer' }} data-testid={`map-zone-${t.code}`}>
            {active && <circle cx={t.x} cy={t.y} r="34" fill="url(#tm-glow)" />}
            <circle cx={t.x} cy={t.y} r={active ? 15 : 11} fill={active ? 'rgba(217,179,90,0.28)' : 'rgba(255,255,255,0.06)'}
              stroke={active ? '#D9B35A' : 'rgba(217,179,90,0.45)'} strokeWidth={active ? 2 : 1.2}
              style={{ transition: 'all .25s ease' }} />
            <circle cx={t.x} cy={t.y} r={active ? 5.5 : 4} fill={active ? '#E9CF8E' : '#D9B35A'} style={{ transition: 'all .25s ease' }}>
              {!active && <animate attributeName="opacity" values="1;0.45;1" dur="2.4s" repeatCount="indefinite" />}
            </circle>
            {active && (
              <circle cx={t.x} cy={t.y} r="15" fill="none" stroke="#D9B35A" strokeWidth="1.5" opacity="0.8">
                <animate attributeName="r" values="15;30" dur="1.8s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.7;0" dur="1.8s" repeatCount="indefinite" />
              </circle>
            )}
            <text x={t.x + t.dx} y={t.y + 5} fontSize={active ? 16 : 14} fontWeight={active ? 700 : 500}
              fill={active ? '#E9CF8E' : 'rgba(247,242,233,0.75)'} textAnchor={t.anchor}
              style={{ transition: 'all .25s ease', userSelect: 'none' }}>
              {t.label}
            </text>
          </g>
        );
      })}
    </svg>
    <p className="absolute bottom-2 right-4 text-[10px]" style={{ color: 'rgba(247,242,233,0.35)' }}>
      {i18n.t('landing.map_hint', 'Cliquez sur un territoire pour découvrir ses produits')}
    </p>
  </div>
);
