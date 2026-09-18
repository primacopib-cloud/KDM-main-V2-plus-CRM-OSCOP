import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Store, Gavel, Coins, Globe2, QrCode, CalendarClock, BadgePercent, ArrowRight, ArrowLeft, Share2, Facebook, Instagram, MessageCircle, Package } from 'lucide-react';
import { toast } from 'sonner';
import { CONCEPT_I18N } from './conceptI18n';
import { detaillantAPI } from '../services/api.detaillant';
import { PopsLeaderboard } from '../components/detaillant/PopsLeaderboard';
import { API } from '../services/http';

const imgSrc = (u) => (u?.startsWith('/api/') ? `${API}${u.slice(4)}` : u);

const ICONS = [Gavel, Coins, BadgePercent, Globe2, CalendarClock, QrCode];
const LANGS = [['fr', '🇫🇷 FR'], ['en', '🇬🇧 EN'], ['es', '🇪🇸 ES'], ['gcf', '🌺 KR']];

export default function DetaillantConceptPage() {
  const [lang, setLang] = useState('fr');
  const [catalog, setCatalog] = useState([]);
  useEffect(() => { detaillantAPI.catalogPublic().then((r) => setCatalog(r.products || [])).catch(() => {}); }, []);
  const t = CONCEPT_I18N[lang];
  const shareUrl = `${window.location.origin}/detaillant`;
  const copyForInstagram = async () => {
    try {
      await navigator.clipboard.writeText(`${t.shareMsg} ${shareUrl}`);
      toast.success('✓ Message copié — collez-le dans votre story ou bio Instagram');
    } catch { toast.error('Copie impossible'); }
    window.open('https://www.instagram.com/', '_blank');
  };
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white" data-testid="detaillant-concept-page">
      <div className="max-w-5xl mx-auto px-6 py-14">
        <Link to="/" data-testid="concept-back-home"
          className="inline-flex items-center gap-1.5 mb-6 px-3 h-8 rounded-full border border-white/20 text-xs font-semibold text-white/70 hover:text-white hover:bg-white/5 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Retour à l'accueil
        </Link>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2 text-[#D9B35A] text-xs font-bold uppercase tracking-[0.2em]">
            <Store className="w-4 h-4" /> {t.tag}
          </div>
          <div className="flex gap-1" data-testid="concept-lang-switch">
            {LANGS.map(([code, label]) => (
              <button key={code} onClick={() => setLang(code)} data-testid={`concept-lang-${code}`}
                className={`px-2.5 h-7 rounded-full text-[11px] font-bold border transition-colors ${
                  lang === code ? 'bg-[#D9B35A] text-black border-[#D9B35A]' : 'border-white/20 text-white/60 hover:bg-white/5'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black mt-4 leading-tight">
          {t.h1a}<br />
          <span className="text-[#E9CF8E]">{t.h1b}</span>
        </h1>
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-emerald-400/40 bg-emerald-500/10 text-emerald-300 text-[11px] font-bold mt-4"
          data-testid="concept-pops-badge">
          {t.popsBadge}
        </div>
        <p className="text-[11px] text-white/45 mt-2 max-w-xl" data-testid="concept-pops-def">{t.popsDef}</p>
        <p className="text-base text-white/60 mt-5 max-w-2xl">{t.sub}</p>
        <div className="flex flex-wrap gap-3 mt-8">
          <Link to="/espace-detaillant" data-testid="concept-cta-join"
            className="inline-flex items-center gap-2 px-6 h-11 rounded-full bg-[#D9B35A] text-black text-sm font-bold hover:bg-[#E9CF8E]">
            {t.cta} <ArrowRight className="w-4 h-4" />
          </Link>
          <Link to="/coopact" data-testid="concept-cta-coopact"
            className="inline-flex items-center gap-2 px-6 h-11 rounded-full border border-white/20 text-sm font-semibold hover:bg-white/5">
            {t.cta2}
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-14">
          {t.features.map(([title, desc], i) => {
            const Icon = ICONS[i];
            return (
              <div key={title} className="rounded-2xl border border-white/10 bg-white/[0.03] p-5" data-testid="concept-feature">
                <Icon className="w-5 h-5 text-[#D9B35A]" />
                <p className="text-sm font-bold mt-2">{title}</p>
                <p className="text-xs text-white/55 mt-1 leading-relaxed">{desc}</p>
              </div>
            );
          })}
        </div>
        <div className="mt-14 rounded-2xl overflow-hidden border border-white/10" data-testid="concept-video">
          <div className="px-5 pt-4 pb-2 bg-white/[0.03]">
            <p className="text-sm font-bold text-[#E9CF8E]">{t.videoTitle}</p>
          </div>
          <video controls playsInline preload="none" className="w-full aspect-video bg-black"
            poster="https://images.pexels.com/videos/853782/free-video-853782.jpg?auto=compress&w=1260"
            data-testid="concept-video-player">
            <source src="https://videos.pexels.com/video-files/853782/853782-hd_1920_1080_30fps.mp4" type="video/mp4" />
          </video>
        </div>
        {catalog.length > 0 && (
          <div className="mt-14" data-testid="concept-catalog">
            <h2 className="text-base md:text-lg font-bold text-[#E9CF8E] flex items-center gap-2">
              <Package className="w-4 h-4" /> {t.catalogTitle}
            </h2>
            <p className="text-xs text-white/50 mt-1">{t.catalogSub}</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mt-4">
              {catalog.slice(0, 12).map((p) => (
                <div key={p.sku} className="rounded-xl border border-white/10 bg-white/[0.03] overflow-hidden"
                  data-testid={`concept-catalog-${p.sku}`}>
                  <div className="h-20 bg-white/[0.04] flex items-center justify-center">
                    {p.image_url
                      ? <img src={imgSrc(p.image_url)} alt={p.name} loading="lazy" className="w-full h-full object-contain p-1.5" />
                      : <Package className="w-6 h-6 text-white/15" />}
                  </div>
                  <div className="p-2.5">
                    <p className="text-[11px] font-bold truncate">{p.name}</p>
                    <p className="text-[9px] text-white/45 truncate">{p.category || '—'}</p>
                    {p.perishable && <p className="text-[8px] text-amber-300 mt-0.5">{t.perishable}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="rounded-2xl border border-[#D9B35A]/30 bg-[#D9B35A]/5 p-6 mt-12">
          <p className="text-sm font-bold text-[#E9CF8E]">{t.how}</p>
          <ol className="text-xs text-white/60 mt-2 space-y-1.5 list-decimal list-inside">
            {t.steps.map((s) => <li key={s}>{s}</li>)}
          </ol>
        </div>
        <PopsLeaderboard t={t} />
        <div className="flex flex-wrap items-center gap-3 mt-10" data-testid="concept-share">
          <span className="inline-flex items-center gap-1.5 text-xs text-white/50">
            <Share2 className="w-3.5 h-3.5" /> {t.share}
          </span>
          <a data-testid="concept-share-whatsapp" target="_blank" rel="noreferrer"
            href={`https://wa.me/?text=${encodeURIComponent(`${t.shareMsg} ${shareUrl}`)}`}
            className="inline-flex items-center gap-1.5 px-4 h-9 rounded-full bg-[#25D366]/15 border border-[#25D366]/40 text-[#4ade80] text-xs font-bold hover:bg-[#25D366]/25 transition-colors">
            <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
          </a>
          <a data-testid="concept-share-facebook" target="_blank" rel="noreferrer"
            href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}&quote=${encodeURIComponent(t.shareMsg)}`}
            className="inline-flex items-center gap-1.5 px-4 h-9 rounded-full bg-[#1877F2]/15 border border-[#1877F2]/40 text-[#7db8ea] text-xs font-bold hover:bg-[#1877F2]/25 transition-colors">
            <Facebook className="w-3.5 h-3.5" /> Facebook
          </a>
          <button onClick={copyForInstagram} data-testid="concept-share-instagram"
            className="inline-flex items-center gap-1.5 px-4 h-9 rounded-full bg-[#E1306C]/15 border border-[#E1306C]/40 text-[#f08bb1] text-xs font-bold hover:bg-[#E1306C]/25 transition-colors">
            <Instagram className="w-3.5 h-3.5" /> Instagram
          </button>
        </div>
      </div>
    </div>
  );
}
