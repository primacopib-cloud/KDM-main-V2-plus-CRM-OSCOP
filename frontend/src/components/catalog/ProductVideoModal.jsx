import { useState } from 'react';
import { X, Clapperboard } from 'lucide-react';
import i18n from '../../i18n';
import { Flag } from '../Flag';

const API = process.env.REACT_APP_BACKEND_URL;

export const ProductVideoModal = ({ product, onClose }) => {
  const variants = product?.video_urls && Object.keys(product.video_urls).length > 1 ? product.video_urls : null;
  const uiLang = (i18n.language || 'fr').slice(0, 2);
  const [lang, setLang] = useState(
    variants ? (variants[uiLang] ? uiLang : (variants.fr ? 'fr' : Object.keys(variants)[0])) : null
  );
  const [counted, setCounted] = useState(false);

  if (!product) return null;
  const rawUrl = (variants && lang && variants[lang]) || product.video_url;
  const src = rawUrl.startsWith('http') ? rawUrl : `${API}${rawUrl}`;

  const trackView = () => {
    if (counted) return;
    setCounted(true);
    fetch(`${API}/api/public/kdmarche-video-view`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: product.id }),
    }).catch(() => {});
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
      onClick={onClose} data-testid="product-video-modal">
      <div className="rounded-[20px] overflow-hidden max-w-2xl w-full bg-[#1a1028]"
        onClick={(e) => e.stopPropagation()} style={{ boxShadow: '0 24px 64px rgba(0,0,0,0.5)' }}>
        <div className="flex items-center justify-between px-5 py-3">
          <p className="text-sm font-semibold text-white flex items-center gap-2">
            <Clapperboard size={15} className="text-[#D9B35A]" /> Spot vidéo — {product.name}
          </p>
          <div className="flex items-center gap-2">
            {variants && Object.keys(variants).map((code) => (
              <button key={code} type="button" onClick={() => setLang(code)}
                data-testid={`product-video-lang-${code}`}
                className={`h-7 px-2.5 rounded-full text-[11px] font-semibold transition-colors inline-flex items-center gap-1.5 ${
                  lang === code ? 'bg-[#D9B35A] text-black' : 'bg-white/10 text-white/70 hover:bg-white/20'
                }`}>
                <Flag code={code} className="w-3.5 h-auto rounded-[2px]" /> {code.toUpperCase()}
              </button>
            ))}
            <button type="button" onClick={onClose} data-testid="product-video-close"
              className="text-white/60 hover:text-white p-1"><X size={18} /></button>
          </div>
        </div>
        <video key={src} src={src} controls autoPlay playsInline onPlay={trackView}
          className="w-full aspect-video bg-black" data-testid="product-video-player" />
      </div>
    </div>
  );
};
