import { ArrowLeft } from 'lucide-react';
import { trackCta } from '../services/ctaTracking';

export const BackToShowcase = ({ page = 'home', className = '' }) => (
  <a href="https://objectifscopoutremer.com" data-testid="hero-back-objectifscop"
    onClick={() => trackCta(`back_showcase_${page}`)}
    className={`inline-flex items-center gap-2.5 group text-white/70 hover:text-white transition-colors ${className}`}>
    <span className="w-8 h-8 rounded-full border border-[#D9B35A]/60 bg-[#D9B35A]/10 flex items-center justify-center group-hover:bg-[#D9B35A]/25 transition-colors">
      <ArrowLeft className="w-4 h-4 text-[#F2D07A] rtl:-scale-x-100" />
    </span>
    <span className="text-xs font-bold tracking-[0.14em] uppercase">OBJECTIFSCOPOUTREMER.COM</span>
  </a>
);
