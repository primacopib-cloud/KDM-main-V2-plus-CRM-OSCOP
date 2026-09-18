import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Store, Gavel, Coins, Globe2, QrCode, CalendarClock, BadgePercent, ArrowRight, ArrowLeft, Share2, Facebook, Instagram, MessageCircle, Package, MousePointerClick, Timer, RotateCcw, Trophy } from 'lucide-react';
import { toast } from 'sonner';
import { CONCEPT_I18N } from './conceptI18n';
import { detaillantAPI } from '../services/api.detaillant';
import { PopsLeaderboard } from '../components/detaillant/PopsLeaderboard';
import { API } from '../services/http';

const imgSrc = (u) => (u?.startsWith('/api/') ? `${API}${u.slice(4)}` : u);

const ICONS = [Gavel, Coins, BadgePercent, Globe2, CalendarClock, QrCode];
const LANGS = [['fr', '🇫🇷 FR'], ['en', '🇬🇧 EN'], ['es', '🇪🇸 ES'], ['gcf', '🌺 KR']];

// Apparition douce au scroll (stagger via delay)
const Reveal = ({ children, delay = 0, className = '', ...rest }) => {
  const ref = useRef(null);
  const [vis, setVis] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setVis(true); obs.disconnect(); }
    }, { threshold: 0.12 });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return (
    <div ref={ref} {...rest}
      className={`${className} transition-[opacity,transform] duration-700 ease-out ${vis ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}
      style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
};

const DEMO_START = 24;
const DEMO_FLOOR = 20.4; // −15 %

// Mini-démo interactive : chaque clic = un Coop'Act qui fait baisser le prix
const DemoLot = ({ t }) => {
  const [price, setPrice] = useState(DEMO_START);
  const [drops, setDrops] = useState([]);
  const [flash, setFlash] = useState(false);
  const [secs, setSecs] = useState(47 * 60 + 32);
  const [clicks, setClicks] = useState(0);
  const won = price <= DEMO_FLOOR + 1e-9;
  const pct = Math.round(((DEMO_START - price) / (DEMO_START - DEMO_FLOOR)) * 100);

  useEffect(() => {
    const id = setInterval(() => setSecs((s) => (s > 0 ? s - 1 : 47 * 60 + 32)), 1000);
    return () => clearInterval(id);
  }, []);

  const bid = () => {
    if (won) return;
    const step = 0.15 + Math.random() * 0.6;
    const np = Math.max(DEMO_FLOOR, +(price - step).toFixed(2));
    setDrops((l) => [+(price - np).toFixed(2), ...l].slice(0, 4));
    setPrice(np);
    setClicks((c) => c + 1);
    setFlash(true);
    setTimeout(() => setFlash(false), 450);
  };

  const reset = () => { setPrice(DEMO_START); setDrops([]); setClicks(0); };
  const mm = String(Math.floor(secs / 60)).padStart(2, '0');
  const ss = String(secs % 60).padStart(2, '0');

  return (
    <div className={`relative mt-10 rounded-2xl border p-6 sm:p-8 overflow-hidden transition-colors duration-500 ${
      won ? 'border-emerald-400/50 bg-emerald-500/[0.07]' : 'border-[#D9B35A]/30 bg-[#D9B35A]/[0.04]'}`}
      data-testid="concept-demo">
      <div className="absolute -top-16 -right-16 w-56 h-56 rounded-full bg-[#D9B35A]/10 blur-3xl pointer-events-none" />
      <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.18em] text-[#E9CF8E]">
        <MousePointerClick className="w-3.5 h-3.5" /> {t.demoTag}
      </div>
      <h2 className="text-base md:text-lg font-bold mt-2">{t.demoTitle}</h2>
      <p className="text-xs text-white/55 mt-1">{t.demoSub}</p>

      <div className="grid sm:grid-cols-[1fr_auto] gap-6 items-center mt-6">
        <div>
          <div className="flex items-end gap-3 flex-wrap">
            <span data-testid="concept-demo-price"
              className={`text-5xl sm:text-6xl font-black tabular-nums transition-[transform,color] duration-300 inline-block ${
                flash ? 'scale-110 text-[#E9CF8E]' : 'scale-100 text-white'}`}>
              {price.toFixed(2)} €
            </span>
            <span className="text-[11px] text-white/45 pb-1.5">
              {t.demoValue} <s>{DEMO_START.toFixed(2)} €</s> · {t.demoFloor}
            </span>
          </div>
          <div className="mt-3 h-1.5 rounded-full bg-white/10 overflow-hidden" data-testid="concept-demo-progress">
            <div className="h-full rounded-full bg-gradient-to-r from-[#D9B35A] to-emerald-400 transition-[width] duration-500"
              style={{ width: `${pct}%` }} />
          </div>
          <div className="flex items-center gap-2 mt-3 min-h-[22px] flex-wrap" data-testid="concept-demo-drops">
            {drops.map((d, i) => (
              <span key={`${d}-${i}`}
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold border transition-opacity duration-300 ${
                  i === 0 ? 'text-emerald-300 border-emerald-400/40 bg-emerald-500/10' : 'text-white/35 border-white/10'}`}
                style={{ opacity: 1 - i * 0.22 }}>
                −{d.toFixed(2)} €
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-col items-center gap-3">
          <span className="inline-flex items-center gap-1.5 text-[11px] text-white/50 tabular-nums" data-testid="concept-demo-timer">
            <Timer className="w-3.5 h-3.5 text-[#D9B35A]" /> {t.demoTime} {mm}:{ss}
          </span>
          {won ? (
            <div className="flex flex-col items-center gap-2">
              <span className="inline-flex items-center gap-2 px-5 h-11 rounded-full bg-emerald-500 text-white text-sm font-black animate-pulse"
                data-testid="concept-demo-won">
                <Trophy className="w-4 h-4" /> {t.demoWon}
              </span>
              <button onClick={reset} data-testid="concept-demo-reset"
                className="inline-flex items-center gap-1.5 px-4 h-8 rounded-full border border-white/20 text-xs font-semibold text-white/70 hover:bg-white/5 transition-colors">
                <RotateCcw className="w-3.5 h-3.5" /> {t.demoReset}
              </button>
            </div>
          ) : (
            <button onClick={bid} data-testid="concept-demo-bid-btn"
              className="group inline-flex flex-col items-center gap-0.5 px-7 h-14 rounded-2xl bg-[#D9B35A] text-black font-black hover:bg-[#E9CF8E] active:scale-95 transition-[transform,background-color] duration-150 shadow-[0_8px_30px_rgba(217,179,90,0.35)]">
              <span className="text-sm leading-tight">{t.demoBid}</span>
              <span className="text-[9px] font-bold opacity-60 leading-tight">{t.demoEach}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

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
      <div className="max-w-5xl mx-auto px-6 py-14 relative">
        <div className="absolute top-0 left-1/3 w-[28rem] h-[28rem] rounded-full bg-[#D9B35A]/[0.06] blur-3xl pointer-events-none" />
        <Link to="/" data-testid="concept-back-home"
          className="inline-flex items-center gap-1.5 mb-6 px-3 h-8 rounded-full border border-white/20 text-xs font-semibold text-white/70 hover:text-white hover:bg-white/5 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Retour à l'accueil
        </Link>
        <Reveal>
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
        </Reveal>
        <Reveal delay={80}>
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
        </Reveal>
        <Reveal delay={160}>
          <div className="flex flex-wrap gap-3 mt-8">
            <Link to="/espace-detaillant" data-testid="concept-cta-join"
              className="group inline-flex items-center gap-2 px-6 h-11 rounded-full bg-[#D9B35A] text-black text-sm font-bold hover:bg-[#E9CF8E] transition-colors">
              {t.cta} <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
            <Link to="/coopact" data-testid="concept-cta-coopact"
              className="inline-flex items-center gap-2 px-6 h-11 rounded-full border border-white/20 text-sm font-semibold hover:bg-white/5 hover:border-white/40 transition-colors">
              {t.cta2}
            </Link>
          </div>
        </Reveal>

        <Reveal delay={220}><DemoLot t={t} /></Reveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-14">
          {t.features.map(([title, desc], i) => {
            const Icon = ICONS[i];
            return (
              <Reveal key={title} delay={i * 70}>
                <div className="group h-full rounded-2xl border border-white/10 bg-white/[0.03] p-5 transition-[transform,border-color,background-color] duration-300 hover:-translate-y-1.5 hover:border-[#D9B35A]/40 hover:bg-white/[0.06]"
                  data-testid="concept-feature">
                  <Icon className="w-5 h-5 text-[#D9B35A] transition-transform duration-300 group-hover:scale-110 group-hover:-rotate-6" />
                  <p className="text-sm font-bold mt-2">{title}</p>
                  <p className="text-xs text-white/55 mt-1 leading-relaxed">{desc}</p>
                </div>
              </Reveal>
            );
          })}
        </div>

        <Reveal>
          <div className="mt-14 rounded-2xl overflow-hidden border border-white/10 hover:border-[#D9B35A]/30 transition-colors duration-500" data-testid="concept-video">
            <div className="px-5 pt-4 pb-2 bg-white/[0.03]">
              <p className="text-sm font-bold text-[#E9CF8E]">{t.videoTitle}</p>
            </div>
            <div className="relative w-full aspect-video bg-black overflow-hidden" data-testid="concept-video-player">
              <img
                src="https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/d2654cc9c8482382481b532f0baff06c1e3047fd5e3be7274dff062ebb82d8ee.jpeg"
                alt="Rayon d'alimentation générale : produits par lots de 3 mis en rayon par des employés POP'S"
                className="w-full h-full object-cover"
                style={{ animation: 'popsKenBurns 26s ease-in-out infinite alternate' }}
              />
              <style>{`@keyframes popsKenBurns { from { transform: scale(1) translateX(0); } to { transform: scale(1.12) translateX(-1.5%); } }`}</style>
            </div>
          </div>
        </Reveal>

        {catalog.length > 0 && (
          <Reveal>
            <div className="mt-14" data-testid="concept-catalog">
              <h2 className="text-base md:text-lg font-bold text-[#E9CF8E] flex items-center gap-2">
                <Package className="w-4 h-4" /> {t.catalogTitle}
              </h2>
              <p className="text-xs text-white/50 mt-1">{t.catalogSub}</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mt-4">
                {catalog.slice(0, 12).map((p, i) => (
                  <div key={p.sku} style={{ transitionDelay: `${i * 40}ms` }}
                    className="group rounded-xl border border-white/10 bg-white/[0.03] overflow-hidden transition-[transform,border-color] duration-300 hover:-translate-y-1 hover:border-emerald-400/40"
                    data-testid={`concept-catalog-${p.sku}`}>
                    <div className="h-20 bg-white/[0.04] flex items-center justify-center overflow-hidden">
                      {p.image_url
                        ? <img src={imgSrc(p.image_url)} alt={p.name} loading="lazy" className="w-full h-full object-contain p-1.5 transition-transform duration-500 group-hover:scale-110" />
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
          </Reveal>
        )}

        <Reveal>
          <div className="rounded-2xl border border-[#D9B35A]/30 bg-[#D9B35A]/5 p-6 mt-12">
            <p className="text-sm font-bold text-[#E9CF8E]">{t.how}</p>
            <ol className="mt-3 space-y-2">
              {t.steps.map((s, i) => (
                <li key={s}
                  className="group flex items-start gap-3 rounded-xl px-3 py-2 -mx-3 text-xs text-white/60 transition-[background-color] duration-300 hover:bg-[#D9B35A]/10">
                  <span className="shrink-0 inline-flex items-center justify-center w-5 h-5 rounded-full bg-[#D9B35A]/20 text-[#E9CF8E] text-[10px] font-black transition-[transform,background-color] duration-300 group-hover:scale-110 group-hover:bg-[#D9B35A] group-hover:text-black">
                    {i + 1}
                  </span>
                  <span className="leading-relaxed pt-0.5">{s}</span>
                </li>
              ))}
            </ol>
          </div>
        </Reveal>

        <Reveal><PopsLeaderboard t={t} /></Reveal>

        <Reveal>
          <div className="flex flex-wrap items-center gap-3 mt-10" data-testid="concept-share">
            <span className="inline-flex items-center gap-1.5 text-xs text-white/50">
              <Share2 className="w-3.5 h-3.5" /> {t.share}
            </span>
            <a data-testid="concept-share-whatsapp" target="_blank" rel="noreferrer"
              href={`https://wa.me/?text=${encodeURIComponent(`${t.shareMsg} ${shareUrl}`)}`}
              className="inline-flex items-center gap-1.5 px-4 h-9 rounded-full bg-[#25D366]/15 border border-[#25D366]/40 text-[#4ade80] text-xs font-bold hover:bg-[#25D366]/25 hover:-translate-y-0.5 transition-[background-color,transform] duration-200">
              <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
            </a>
            <a data-testid="concept-share-facebook" target="_blank" rel="noreferrer"
              href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}&quote=${encodeURIComponent(t.shareMsg)}`}
              className="inline-flex items-center gap-1.5 px-4 h-9 rounded-full bg-[#1877F2]/15 border border-[#1877F2]/40 text-[#7db8ea] text-xs font-bold hover:bg-[#1877F2]/25 hover:-translate-y-0.5 transition-[background-color,transform] duration-200">
              <Facebook className="w-3.5 h-3.5" /> Facebook
            </a>
            <button onClick={copyForInstagram} data-testid="concept-share-instagram"
              className="inline-flex items-center gap-1.5 px-4 h-9 rounded-full bg-[#E1306C]/15 border border-[#E1306C]/40 text-[#f08bb1] text-xs font-bold hover:bg-[#E1306C]/25 hover:-translate-y-0.5 transition-[background-color,transform] duration-200">
              <Instagram className="w-3.5 h-3.5" /> Instagram
            </button>
          </div>
        </Reveal>
      </div>
    </div>
  );
}
