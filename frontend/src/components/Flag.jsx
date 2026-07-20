const MAP = { en: 'gb' };

export const Flag = ({ code, className = 'w-4 h-auto rounded-[2px] inline-block' }) => {
  const c = MAP[String(code).toLowerCase()] || String(code).toLowerCase();
  return (
    <img src={`https://flagcdn.com/w40/${c}.png`} srcSet={`https://flagcdn.com/w80/${c}.png 2x`}
      alt={String(code).toUpperCase()} className={className}
      style={{ boxShadow: '0 0 0 1px rgba(0,0,0,0.15)' }} loading="lazy" />
  );
};
