import { partners } from '../data/mock';

const SIZES = {
  sm: { box: 'h-8 w-8', img: 'h-6 w-6' },
  md: { box: 'h-10 w-10', img: 'h-8 w-8' },
  lg: { box: 'h-14 w-14', img: 'h-11 w-11' },
};

export const BrandLogos = ({ size = 'md', className = '' }) => {
  const s = SIZES[size] || SIZES.md;
  return (
    <div className={`flex items-center gap-2 ${className}`} data-testid="brand-logos">
      <span className={`inline-flex items-center justify-center ${s.box} rounded-xl bg-white shrink-0 overflow-hidden`}
        style={{ boxShadow: '0 1px 4px rgba(217,179,90,0.3)' }}>
        <img src={partners.kdmarche.logo} alt="KDMARCHE" className={`${s.img} object-contain`} />
      </span>
      <span className="text-white/30 text-sm leading-none">×</span>
      <span className={`inline-flex items-center justify-center ${s.box} rounded-full bg-white shrink-0 overflow-hidden`}
        style={{ boxShadow: '0 1px 4px rgba(212,175,55,0.3)' }}>
        <img src={partners.oscop.logo} alt="O'SCOP" className={`${s.img} object-contain`} />
      </span>
    </div>
  );
};
