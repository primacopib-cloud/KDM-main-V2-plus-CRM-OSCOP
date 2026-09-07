const MAP = { en: 'gb' };

const T_CODES = {
  GUADELOUPE: 'gp', MARTINIQUE: 'mq', GUYANE: 'gf', 'GUYANE FRANCAISE': 'gf',
  REUNION: 're', 'LA REUNION': 're', MAYOTTE: 'yt', CARIBBEAN: 'fr', CARAIBE: 'fr',
  FRANCE: 'fr', 'FRANCE METROPOLITAINE': 'fr', 'SAINT-MARTIN': 'mf', 'SAINT-BARTHELEMY': 'bl',
};

export const territoryFlagCode = (t) => {
  const k = String(t || '').toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
  if (T_CODES[k]) return T_CODES[k];
  return k.length === 2 ? k.toLowerCase() : null;
};

export const TerritoryFlag = ({ territory, className = 'w-4 h-auto rounded-[2px] inline-block' }) => {
  const c = territoryFlagCode(territory);
  return c ? <Flag code={c} className={className} /> : null;
};

export const Flag = ({ code, className = 'w-4 h-auto rounded-[2px] inline-block' }) => {
  const c = MAP[String(code).toLowerCase()] || String(code).toLowerCase();
  return (
    <img src={`https://flagcdn.com/w40/${c}.png`} srcSet={`https://flagcdn.com/w80/${c}.png 2x`}
      alt={String(code).toUpperCase()} className={className}
      style={{ boxShadow: '0 0 0 1px rgba(0,0,0,0.15)' }} loading="lazy" />
  );
};
