import { useEffect, useRef, useState } from 'react';
import { X, Play, Pause, RotateCcw, Ticket, Share2, Link as LinkIcon, Volume2, VolumeX } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const IMG = 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/';
/*
 * Montage publicitaire 30 s.
 * Vidéos réelles du projet (Veo 3, uploads/videos, H.264/AAC valides) : boutique antillaise (scène 1) + cave/terroir (scène 3).
 * Note : le Chromium headless de test n'embarque pas le codec H.264 → repli image automatique en environnement de test ;
 * sur les navigateurs réels (Chrome, Safari, Firefox), les vidéos jouent normalement (Range requests supportées côté serveur).
 * SÉQUENCES VIDÉO MANQUANTES (clé FAL expirée — à fournir pour un rendu 100 % vidéo) :
 *  - sélection de produits par 3 en magasin, commande sur smartphone, préparation/chargement des sacs,
 *    retrait au point relais, famille finale, et une piste musicale libre de droits.
 * En attendant, ces scènes utilisent des images fixes présentées sobrement (fondu, sans faux mouvement).
 */
const SCENES = [
  { video: '/api/uploads/videos/8aa3c90e-b59d-4ae7-b8d4-ff5e6ccab36d.mp4',
    poster: `${IMG}c0c71f4f0cace537b3db6b0c91c1d22217126f055e31fb54f4072536c58685b7.jpeg`,
    img: `${IMG}c0c71f4f0cace537b3db6b0c91c1d22217126f055e31fb54f4072536c58685b7.jpeg`,
    duration: 4000, kicker: 'LOLODRIVE by O’SCOP', title: 'VOTRE TERRITOIRE, VOS PRODUITS', sub: 'L’épicerie antillaise, par lot de 3.' },
  { img: `${IMG}03b0b0754e0126acf04556bc2c87535f4f6c847886d7a38aa7b1c2d4f9090d25.jpeg`,
    duration: 4000, kicker: 'LE CONCEPT', title: 'ACHETEZ PAR LOT ×3', sub: '3 fois plus malin. 3 fois moins cher à l’unité.' },
  { video: '/api/uploads/videos/c7492609-8a49-4c57-b4d0-576c62091831.mp4',
    poster: `${IMG}76fb75f13d4956f61e133f4254f19748210d76a544df1563775d75b31e7969ec.jpeg`,
    img: `${IMG}76fb75f13d4956f61e133f4254f19748210d76a544df1563775d75b31e7969ec.jpeg`,
    duration: 4000, kicker: 'LE TERROIR', title: 'LES PRODUITS DE CHEZ NOUS', sub: 'Rhums, épicerie, frais : le catalogue de votre territoire.' },
  { img: `${IMG}ed2ed1e5a423c20f9be1f285167fdf1fe6c2defebfc13b5be0b193fc982668ef.jpeg`,
    duration: 5000, kicker: 'EN LIGNE', title: 'COMMANDEZ EN 3 CLICS', sub: 'Tout le catalogue à prix mini, depuis votre canapé.' },
  { img: `${IMG}0cf29917f13c278e3b19b8be49129ca514173f41acb07096e6b1ed7ef07f1b86.jpeg`,
    duration: 4000, kicker: 'VOTRE RELAIS PRÉPARE', title: 'VOS COURSES PRÊTES PAR 3', sub: 'Riz, pâtes, huile… vos essentiels regroupés pour vous.' },
  { img: `${IMG}c0c71f4f0cace537b3db6b0c91c1d22217126f055e31fb54f4072536c58685b7.jpeg`,
    duration: 5000, kicker: 'PRÈS DE CHEZ VOUS', title: 'RETRAIT EN POINT RELAIS', sub: 'Votre relais LOLODRIVE vous attend au coin de la rue.' },
  { img: `${IMG}2c4c4c0249af14104048ae27f62936bf211c576e43239ccd602020c7c5483ffa.jpeg`,
    duration: 4000, kicker: 'LOLODRIVE by O’SCOP', title: 'LA VIE MOINS CHÈRE, ENSEMBLE', sub: 'Le PASS qui change vos courses. Rejoignez la coopérative.', final: true },
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
          <img src={mediaUrl(s.img)} alt="" className="w-full h-full object-cover" />
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
        <div className="absolute inset-x-0 bottom-[11vh] px-6 text-center">
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
        <div className="absolute bottom-[8vh] left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 flex-wrap justify-center">
          <button type="button" data-testid="spot-replay" onClick={() => { setScene(0); setDone(false); setPaused(false); remainingRef.current = SCENES[0].duration; }}
            className="inline-flex items-center gap-2 px-4 h-10 rounded-full text-xs font-bold text-white bg-white/10 border border-white/25 hover:bg-white/20 transition-colors">
            <RotateCcw className="w-3.5 h-3.5" /> Revoir le spot
          </button>
          <a data-testid="spot-share-wa"
            href={`https://wa.me/?text=${encodeURIComponent(`🎬 Regarde le spot LOLODRIVE : les courses par lot ×3 à prix mini, en ligne et en point relais ! ${window.location.origin}/catalogue-lolodrive?spot=1`)}`}
            target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-2 px-4 h-10 rounded-full text-xs font-bold text-white bg-[#25D366]/25 border border-[#25D366]/50 hover:bg-[#25D366]/40 transition-colors">
            <Share2 className="w-3.5 h-3.5" /> Partager sur WhatsApp
          </a>
          <button type="button" data-testid="spot-share-copy"
            onClick={() => {
              navigator.clipboard.writeText(`${window.location.origin}/catalogue-lolodrive?spot=1`)
                .then(() => setCopied(true)).catch(() => {});
              setTimeout(() => setCopied(false), 2500);
            }}
            className="inline-flex items-center gap-2 px-4 h-10 rounded-full text-xs font-bold text-white bg-white/10 border border-white/25 hover:bg-white/20 transition-colors">
            <LinkIcon className="w-3.5 h-3.5" /> {copied ? 'Lien copié ✓' : 'Copier le lien du spot'}
          </button>
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
