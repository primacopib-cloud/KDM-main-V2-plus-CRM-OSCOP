import { useEffect, useRef, useState } from 'react';
import { X, Play, Pause, RotateCcw, Ticket, Share2, Link as LinkIcon, Volume2, VolumeX } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const IMG = 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/';
/*
 * Montage publicitaire 30 s — 6 scènes vidéo réelles (Veo 3, uploads/videos) sur 7 :
 * accroche boutique, sélection produits ×3, commande smartphone, préparation relais, retrait drive, famille finale.
 * Reste en image fixe : scène 2 « concept lot ×3 » (packshot). Musique libre de droits : à fournir (l'audio provient des clips).
 * Note test : le Chromium headless n'a pas le codec H.264 → repli image auto ; navigateurs réels OK (Range 206 côté serveur).
 */
const SCENES = [
  { img: '/images/spot/scene1-paniers.jpg',
    imgMobile: '/images/spot/scene1-paniers.jpg', pos: 'center 82%',
    duration: 4000, kicker: 'LOLODRIVE by O’SCOP', title: 'L’ÉPICERIE DE VOTRE TERRITOIRE', sub: 'Des produits du terroir, sélectionnés pour vous.' },
  { img: '/images/spot/scene2-riz.jpg',
    imgMobile: '/images/spot/scene2-riz.jpg', pos: 'center 55%',
    duration: 4000, kicker: 'LE CONCEPT', title: 'EXCLUSIVEMENT PAR LOT DE 3', sub: 'Au meilleur prix coop\u00e9ratif n\u00e9goci\u00e9.' },
  ...[
    ['legumes', 'L\u00c9GUMES DU SOLEIL'], ['yaourts', 'YAOURTS'], ['pates', 'P\u00c2TES'], ['riz', 'RIZ'],
    ['cereales', 'C\u00c9R\u00c9ALES'], ['huiles', 'HUILES'], ['beurre', 'BEURRE'], ['lait', 'LAIT'],
  ].map(([slug, name]) => ({
    video: `/api/uploads/videos/lolospot_prod_${slug}.mp4`,
    img: `/images/spot/prod-${slug}.jpg`,
    imgMobile: `/images/spot/prod-${slug}.jpg`,
    duration: 2500, kicker: 'TOUS VOS ESSENTIELS', title: name,
    sub: 'Par lot de 3 \u2014 au meilleur prix coop\u00e9ratif n\u00e9goci\u00e9.',
  })),
  { video: '/api/uploads/videos/lolospot_order.mp4',
    poster: `${IMG}ed2ed1e5a423c20f9be1f285167fdf1fe6c2defebfc13b5be0b193fc982668ef.jpeg`,
    img: `${IMG}ed2ed1e5a423c20f9be1f285167fdf1fe6c2defebfc13b5be0b193fc982668ef.jpeg`,
    imgMobile: `${IMG}3eb7e909af822d8bee4a2945d40a93f4465399b835bbcfcc7a555d57527ac45e.jpeg`,
    duration: 5000, kicker: 'AVEC VOTRE PASS LOLODRIVE', title: 'COMMANDEZ EN LIGNE', sub: 'En quelques clics, en ligne et en relais.' },
  { video: '/api/uploads/videos/lolospot_prep3.mp4',
    img: `${IMG}fa54989012e3b561d3aa55de0d3af3fcca6df2ed139aab997e9b6804ff79540f.jpeg`,
    imgMobile: `${IMG}53e97ce3eeb653344afa45510ff5095de03f6370b1efd973b63dc6b4dd2b3ea9.jpeg`,
    duration: 4000, kicker: 'VOTRE RELAIS PR\u00c9PARE', title: 'VOS PANIERS PR\u00c9PAR\u00c9S AVEC SOIN', sub: 'L\u2019\u00e9quipe LOLODRIVE pr\u00e9pare vos paniers pour vous.' },
  { video: '/api/uploads/videos/lolospot_pickup3.mp4',
    poster: `${IMG}1d44d39839da8cf759365ab785c891742cf1999c05a103315d8f229f5cf6c455.jpeg`,
    img: `${IMG}1d44d39839da8cf759365ab785c891742cf1999c05a103315d8f229f5cf6c455.jpeg`,
    imgMobile: `${IMG}e60c1ff0ae184631bc39136afbd62932c14607d478bfb3248910ff67ed5c2791.jpeg`,
    duration: 5000, kicker: 'PR\u00c8S DE CHEZ VOUS', title: 'LIVRAISON OU RETRAIT DRIVE', sub: 'Optez pour une livraison ou un retrait drive en relais.' },
  { video: '/api/uploads/videos/lolospot_final.mp4',
    poster: `${IMG}2c4c4c0249af14104048ae27f62936bf211c576e43239ccd602020c7c5483ffa.jpeg`,
    img: `${IMG}2c4c4c0249af14104048ae27f62936bf211c576e43239ccd602020c7c5483ffa.jpeg`,
    imgMobile: `${IMG}5a23665bd1ac32b48f3c636d27c1ec6d4a4564a6105c1671e4a1c0436b4b8388.jpeg`,
    duration: 4000, kicker: 'LOLODRIVE by O\u2019SCOP', title: 'ON VOUS ACCUEILLE AVEC PLAISIR', sub: 'L\u2019\u00e9quipe LOLODRIVE vous attend. Rejoignez la coop\u00e9rative avec votre PASS.', final: true },
];
const API = process.env.REACT_APP_BACKEND_URL;
const mediaUrl = (u) => (u && u.startsWith('/') ? `${API}${u}` : u);
const wordGroups = (title) => {
  const words = title.split(' ');
  const groups = [];
  for (let i = 0; i < words.length; i += 2) groups.push(words.slice(i, i + 2).join(' '));
  return groups;
};

// Spot publicitaire LOLODRIVE — montage 30 s, vidéo quand disponible, repli image sobre
export const LolodriveSpot = ({ onClose }) => {
  const navigate = useNavigate();
  const [scene, setScene] = useState(0);
  const [done, setDone] = useState(false);
  const [paused, setPaused] = useState(false);
  const [muted, setMuted] = useState(true);
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState({});
  const timer = useRef(null);
  const startRef = useRef(0);
  const remainingRef = useRef(SCENES[0].duration);
  const autoPausedRef = useRef(false);
  const viewedRef = useRef(false);
  const videoRef = useRef(null);
  const reduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  useEffect(() => {
    if (viewedRef.current) return;
    viewedRef.current = true;
    fetch(`${API}/api/lolodrive/spot/view`, { method: 'POST' }).catch(() => {});
  }, []);

  useEffect(() => { remainingRef.current = SCENES[scene].duration; }, [scene]);

  useEffect(() => {
    if (done || paused) return undefined;
    startRef.current = Date.now();
    timer.current = setTimeout(() => {
      setScene((prev) => {
        if (prev < SCENES.length - 1) return prev + 1;
        setDone(true);
        return prev;
      });
    }, Math.max(200, remainingRef.current));
    return () => {
      clearTimeout(timer.current);
      remainingRef.current -= Date.now() - startRef.current;
    };
  }, [scene, done, paused]);

  // Pause quand l'onglet devient invisible ; reprise si la pause était automatique
  useEffect(() => {
    const onVis = () => {
      if (document.hidden) {
        setPaused((p) => { if (!p) autoPausedRef.current = true; return true; });
      } else if (autoPausedRef.current) {
        autoPausedRef.current = false;
        setPaused(false);
      }
    };
    document.addEventListener('visibilitychange', onVis);
    return () => document.removeEventListener('visibilitychange', onVis);
  }, []);

  // Synchronise lecture vidéo / pause / son (fondu d'entrée à l'activation du son)
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = muted;
    if (paused || done) { v.pause(); return; }
    const p = v.play();
    // Ne replier sur l'image qu'en cas d'erreur média réelle (AbortError transitoire ignoré)
    if (p && p.catch) p.catch(() => { if (v.error) setFailed((f) => ({ ...f, [scene]: true })); });
  }, [scene, paused, muted, done]);
  const unmute = () => {
    setMuted(false);
    const v = videoRef.current;
    if (v) {
      v.volume = 0;
      let vol = 0;
      const iv = setInterval(() => {
        vol = Math.min(1, vol + 0.12);
        v.volume = vol;
        if (vol >= 1) clearInterval(iv);
      }, 70);
    }
  };

  const s = SCENES[scene];
  const showVideo = s.video && !failed[scene];
  const next = SCENES[scene + 1];
  const anim = (delay, name = 'spotIn') => (reduced ? {} : { animation: `${name} 450ms ${delay}ms ease-out backwards` });

  return (
    <div className="fixed inset-0 z-[120] bg-black flex items-center justify-center overflow-hidden" data-testid="lolodrive-spot"
      role="dialog" aria-label="Spot publicitaire LOLODRIVE">
      <style>{`
        @keyframes spotIn { 0% { opacity: 0; transform: translateY(10px); } 100% { opacity: 1; transform: translateY(0); } }
        @keyframes spotSceneFade { 0% { opacity: 0; } 100% { opacity: 1; } }
        @keyframes spotBar { 0% { width: 0; } 100% { width: 100%; } }
      `}</style>
      {/* Scène */}
      <div key={scene} className="absolute inset-0" style={reduced ? {} : { animation: 'spotSceneFade 350ms ease-out' }}>
        {showVideo ? (
          <video
            ref={videoRef}
            src={mediaUrl(s.video)}
            poster={s.poster ? mediaUrl(s.poster) : undefined}
            className="w-full h-full object-cover"
            autoPlay
            muted={muted}
            playsInline
            preload="auto"
            onError={(e) => {
              const code = e.currentTarget && e.currentTarget.error && e.currentTarget.error.code;
              console.warn('[spot] video error scene', scene, 'code', code, 'src', e.currentTarget && e.currentTarget.currentSrc);
              if (code) setFailed((f) => ({ ...f, [scene]: true }));
            }}
          />
        ) : (
          <picture className="contents">
            {s.imgMobile && <source media="(max-width: 640px)" srcSet={mediaUrl(s.imgMobile)} data-testid={`spot-scene-src-mobile-${scene}`} />}
            <img src={mediaUrl(s.img)} alt="" className="w-full h-full object-cover" style={s.pos ? { objectPosition: s.pos } : undefined} />
          </picture>
        )}
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, rgba(8,4,16,0.30) 0%, rgba(8,4,16,0.10) 45%, rgba(8,4,16,0.85) 100%)' }} />
        {/* Bandes ciné */}
        <div className="absolute top-0 left-0 right-0 h-[6vh] bg-black" />
        <div className="absolute bottom-0 left-0 right-0 h-[6vh] bg-black" />
        {/* Cartouche LOT ×3 (offre réelle du concept), discret */}
        {!s.final && (
          <div className="absolute top-[9vh] left-4 px-2.5 py-1 rounded-md text-[11px] sm:text-xs font-bold tracking-wide text-white/90 bg-black/45 border border-white/25 backdrop-blur-sm select-none">
            LOT ×3
          </div>
        )}
        {/* Textes */}
        <div className="absolute inset-x-0 bottom-[26vh] sm:bottom-[11vh] px-6 text-center">
          <p className="text-[#8CC63E] font-semibold text-[11px] sm:text-sm uppercase m-0 tracking-[0.24em]" style={anim(80)}>{s.kicker}</p>
          <h2 className="text-white font-black m-0 mt-2 text-2xl sm:text-4xl lg:text-5xl leading-tight" style={{ textShadow: '0 2px 18px rgba(0,0,0,0.55)' }}>
            {wordGroups(s.title).map((g, gi) => (
              <span key={gi} className="inline-block mr-[0.3em]" style={anim(180 + gi * 140)}>{g}</span>
            ))}
          </h2>
          <p className="text-white/80 text-sm sm:text-base m-0 mt-2 max-w-2xl mx-auto" style={anim(420)}>{s.sub}</p>
          {s.final && (
            <div style={anim(560)} className="mt-5 flex items-center justify-center gap-3 flex-wrap">
              <button type="button" data-testid="spot-cta-pass" onClick={() => {
                fetch(`${API}/api/lolodrive/spot/cta`, { method: 'POST' }).catch(() => {});
                onClose();
                navigate('/pass-lolodrive');
              }}
                className="px-6 h-12 rounded-full font-bold text-sm text-[#1F0A33] hover:brightness-110 transition-[filter]"
                style={{ background: 'linear-gradient(135deg, #D9B35A, #8CC63E)' }}>
                <Ticket className="w-4 h-4 inline mr-2" /> Découvrir le PASS LOLODRIVE
              </button>
            </div>
          )}
        </div>
      </div>
      {/* Préchargement de la prochaine séquence vidéo uniquement */}
      {next && next.video && !failed[scene + 1] && (
        <video src={mediaUrl(next.video)} preload="auto" muted playsInline className="hidden" aria-hidden="true" />
      )}
      {/* Progression scènes */}
      <div className="absolute top-[7vh] left-1/2 -translate-x-1/2 flex gap-1.5 z-10">
        {SCENES.map((sc, i) => (
          <div key={i} className="h-1 rounded-full bg-white/25 overflow-hidden" style={{ width: `${Math.max(22, sc.duration / 140)}px` }}>
            {i < scene || done ? <div className="h-full w-full bg-[#D9B35A]" />
              : i === scene && !paused ? <div key={`${scene}-${paused}`} className="h-full bg-[#D9B35A]" style={{ animation: `spotBar ${remainingRef.current}ms linear forwards` }} />
                : i === scene ? <div className="h-full bg-[#D9B35A]" style={{ width: `${100 - (remainingRef.current / sc.duration) * 100}%` }} /> : null}
          </div>
        ))}
      </div>
      {/* Commandes accessibles */}
      <div className="absolute top-[8vh] right-4 z-10 flex items-center gap-2">
        {!done && (
          <button type="button" data-testid="spot-pause" aria-label={paused ? 'Reprendre le spot' : 'Mettre le spot en pause'}
            onClick={() => { autoPausedRef.current = false; setPaused((p) => !p); }}
            className="p-2 rounded-full text-white bg-white/10 border border-white/25 hover:bg-white/20 transition-colors">
            {paused ? <Play className="w-5 h-5" /> : <Pause className="w-5 h-5" />}
          </button>
        )}
        <button type="button" data-testid="spot-mute" aria-label={muted ? 'Activer le son' : 'Couper le son'}
          onClick={() => (muted ? unmute() : setMuted(true))}
          className="p-2 rounded-full text-white bg-white/10 border border-white/25 hover:bg-white/20 transition-colors">
          {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
        </button>
        <button type="button" data-testid="spot-close" aria-label="Fermer le spot" onClick={onClose}
          className="p-2 rounded-full text-white bg-white/10 border border-white/25 hover:bg-white/20 transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>
      {done && (
        <div className="absolute bottom-[3vh] left-1/2 -translate-x-1/2 z-10 flex items-center gap-1.5 sm:gap-2 flex-wrap justify-center max-w-[94vw]">
          <button type="button" data-testid="spot-replay" onClick={() => { setScene(0); setDone(false); setPaused(false); remainingRef.current = SCENES[0].duration; }}
            className="inline-flex items-center gap-2 px-3 sm:px-4 h-9 sm:h-10 rounded-full text-[10px] sm:text-xs font-bold text-white bg-white/10 border border-white/25 hover:bg-white/20 transition-colors">
            <RotateCcw className="w-3.5 h-3.5" /> Revoir le spot
          </button>
          <a data-testid="spot-share-wa"
            href={`https://wa.me/?text=${encodeURIComponent(`🎬 Regarde le spot LOLODRIVE : les courses par lot ×3 à prix mini, en ligne et en point relais ! ${window.location.origin}/catalogue-lolodrive?spot=1`)}`}
            target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-2 px-3 sm:px-4 h-9 sm:h-10 rounded-full text-[10px] sm:text-xs font-bold text-white bg-[#25D366]/25 border border-[#25D366]/50 hover:bg-[#25D366]/40 transition-colors">
            <Share2 className="w-3.5 h-3.5" /> Partager sur WhatsApp
          </a>
          <button type="button" data-testid="spot-share-copy"
            onClick={() => {
              navigator.clipboard.writeText(`${window.location.origin}/catalogue-lolodrive?spot=1`)
                .then(() => setCopied(true)).catch(() => {});
              setTimeout(() => setCopied(false), 2500);
            }}
            className="inline-flex items-center gap-2 px-3 sm:px-4 h-9 sm:h-10 rounded-full text-[10px] sm:text-xs font-bold text-white bg-white/10 border border-white/25 hover:bg-white/20 transition-colors">
            <LinkIcon className="w-3.5 h-3.5" /> {copied ? 'Lien copié ✓' : 'Copier le lien du spot'}
          </button>
          <a data-testid="spot-download-vertical" href={`${API}/api/uploads/videos/lolospot_vertical.mp4`} download="spot-lolodrive-story.mp4"
            className="inline-flex items-center gap-2 px-3 sm:px-4 h-9 sm:h-10 rounded-full text-[10px] sm:text-xs font-bold text-white bg-[#D9B35A]/20 border border-[#D9B35A]/50 hover:bg-[#D9B35A]/35 transition-colors">
            ⬇️ Version story (9:16)
          </a>
        </div>
      )}
    </div>
  );
};

// Bouton déclencheur réutilisable — autoPlay : lance le spot à la première visite (flag localStorage)
export const LolodriveSpotButton = ({ className = '', autoPlay = false }) => {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    // Lien de partage : ?spot=1 ouvre le spot directement
    if (new URLSearchParams(window.location.search).has('spot')) {
      setOpen(true);
      return undefined;
    }
    if (!autoPlay) return undefined;
    try {
      if (localStorage.getItem('kdm_spot_seen')) return undefined;
      const t = setTimeout(() => {
        localStorage.setItem('kdm_spot_seen', '1');
        setOpen(true);
      }, 1200);
      return () => clearTimeout(t);
    } catch { return undefined; }
  }, [autoPlay]);
  return (
    <>
      <button type="button" data-testid="open-lolodrive-spot" onClick={() => setOpen(true)}
        className={`inline-flex items-center gap-2 px-4 h-10 rounded-full text-xs sm:text-sm font-bold text-white border border-[#8CC63E]/50 bg-[#8CC63E]/15 hover:bg-[#8CC63E]/30 transition-colors ${className}`}>
        <Play className="w-4 h-4 fill-current" /> Voir le spot LOLODRIVE
      </button>
      {open && <LolodriveSpot onClose={() => setOpen(false)} />}
    </>
  );
};
