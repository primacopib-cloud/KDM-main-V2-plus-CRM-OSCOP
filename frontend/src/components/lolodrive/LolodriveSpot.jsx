import { useEffect, useRef, useState } from 'react';
import { X, Play, RotateCcw, Ticket, Share2, Link as LinkIcon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const SCENES = [
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/03b0b0754e0126acf04556bc2c87535f4f6c847886d7a38aa7b1c2d4f9090d25.jpeg', kicker: 'LE CONCEPT', title: 'ACHETEZ PAR LOT ×3', sub: '3 fois plus malin. 3 fois moins cher à l’unité.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/0b81e622a804740a64f116f11cdc67b68ac642af1b583382206aa5d3d31efe6c.jpeg', kicker: 'PRIX MINI', title: '3 SACS, 1 PRIX MALIN', sub: 'Farine, riz, huile… tous vos basiques en lot de 3.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/0cf29917f13c278e3b19b8be49129ca514173f41acb07096e6b1ed7ef07f1b86.jpeg', kicker: 'TOUS VOS ESSENTIELS', title: 'TOUJOURS PAR 3', sub: 'Des volumes groupés, des prix négociés par la coopérative.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/6c56ab7e6014f75dd19aa182a53b71d7c629d8369cfce46ce5c0c4d308299bc8.jpeg', kicker: 'FRAÎCHEUR LOCALE', title: 'LES LÉGUMES AUSSI PAR 3', sub: 'Paniers de saison, circuits courts de votre territoire.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/8cf70561efa90776a937c8cb7d877202eeeb46950b26675f165eab7f63dbce79.jpeg', kicker: 'PETIT DÉJEUNER', title: 'CÉRÉALES EN LOT ×3', sub: 'De quoi tenir tout le mois, sans exploser le budget.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/76fb75f13d4956f61e133f4254f19748210d76a544df1563775d75b31e7969ec.jpeg', kicker: 'EN CUISINE', title: 'L’HUILE PAR 3', sub: 'La qualité au meilleur prix, mutualisée par la centrale.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/60b34b639106d0169fe28bdbc09fff173d69387dcd7e64f67f6e9d3dfeeb177c.jpeg', kicker: 'SAVEURS', title: 'SAUCES EN LOT ×3', sub: 'Vos recettes du quotidien, toujours par 3.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/b4dda9a82e47c6d4403730d0aae0dc145f959666c6acdb6769b7fd7a47e72afc.jpeg', kicker: 'GARDE-MANGER', title: 'LÉGUMES SECS PAR 3', sub: 'Haricots, lentilles, pois chiches : le plein de protéines.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/61ba04fd8e9fb05fbb4448c22bbc58058667b02b3ff4c66ffb3278ac8b745694.jpeg', kicker: 'CRÉMERIE', title: 'LE BEURRE PAR 3', sub: 'Le frais aussi respecte le concept LOLODRIVE.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/b25f7dce889bca0050263779c06a368256b0f795758acb8bad7ec69693c1abab.jpeg', kicker: 'LE FRAIS AUSSI', title: 'YAOURTS EN LOT ×3', sub: 'Laitages et desserts : même concept, mêmes économies.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/d153872f45873abad4877398f43985177b1fe733f28fde31ab273ea7b775f1e4.jpeg', kicker: 'PLAISIR', title: 'FROMAGES PAR 3', sub: 'Les bons produits, accessibles à toutes les familles.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/dde22d047eb8e18530a50d0cbe49d5ae4f2207fe53ef9476933f9528181fece3.jpeg', kicker: 'EN LIGNE', title: 'COMMANDEZ EN 3 CLICS', sub: 'Tout le catalogue à prix mini, depuis votre canapé.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/6e9811861d21f48dfcdfa850de45c4d156576be8fd3a803669bdbaf3db1d500b.jpeg', kicker: 'PRÈS DE CHEZ VOUS', title: 'RETRAIT EN POINT RELAIS', sub: 'Votre relais LOLODRIVE vous attend au coin de la rue.' },
  { img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/2c4c4c0249af14104048ae27f62936bf211c576e43239ccd602020c7c5483ffa.jpeg', kicker: 'LOLODRIVE by O’SCOP', title: 'LA VIE MOINS CHÈRE, ENSEMBLE', sub: 'Le PASS qui change vos courses. Rejoignez la coopérative.', final: true },
];
const SCENE_MS = 2800;

// Spot publicitaire cinématique LOLODRIVE — scènes animées plein écran
export const LolodriveSpot = ({ onClose }) => {
  const navigate = useNavigate();
  const [scene, setScene] = useState(0);
  const [done, setDone] = useState(false);
  const [copied, setCopied] = useState(false);
  const timer = useRef(null);
  useEffect(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/spot/view`, { method: 'POST' }).catch(() => {});
  }, []);
  useEffect(() => {
    if (done) return undefined;
    timer.current = setTimeout(() => {
      if (scene < SCENES.length - 1) setScene(scene + 1);
      else setDone(true);
    }, SCENE_MS);
    return () => clearTimeout(timer.current);
  }, [scene, done]);
  const s = SCENES[scene];
  return (
    <div className="fixed inset-0 z-[120] bg-black flex items-center justify-center overflow-hidden" data-testid="lolodrive-spot">
      <style>{`
        @keyframes spotKbA { 0% { transform: scale(1.18) translate(3%, 1%); } 100% { transform: scale(1.02) translate(-2%, -1%); } }
        @keyframes spotKbB { 0% { transform: scale(1.02) translate(-3%, 0); } 100% { transform: scale(1.16) translate(2%, 1%); } }
        @keyframes spotKbC { 0% { transform: scale(1.2) translateY(3%); } 100% { transform: scale(1.04) translateY(-2%); } }
        @keyframes spotKbD { 0% { transform: scale(1.05) rotate(-1deg); } 100% { transform: scale(1.18) rotate(0.6deg); } }
        @keyframes spotFadeUp { 0% { opacity: 0; transform: translateY(28px); } 100% { opacity: 1; transform: translateY(0); } }
        @keyframes spotWordPop { 0% { opacity: 0; transform: translateY(34px) scale(0.85) rotate(-2deg); } 60% { opacity: 1; transform: translateY(-4px) scale(1.04); } 100% { opacity: 1; transform: translateY(0) scale(1) rotate(0); } }
        @keyframes spotKicker { 0% { opacity: 0; letter-spacing: 0.6em; } 100% { opacity: 1; letter-spacing: 0.28em; } }
        @keyframes spotBar { 0% { width: 0; } 100% { width: 100%; } }
        @keyframes spotGlow { 0%,100% { text-shadow: 0 0 24px rgba(217,179,90,0.55); } 50% { text-shadow: 0 0 48px rgba(217,179,90,0.95); } }
        @keyframes spotFlash { 0% { opacity: 0.9; } 100% { opacity: 0; } }
        @keyframes spotSweep { 0% { transform: translateX(-140%) skewX(-18deg); } 100% { transform: translateX(240%) skewX(-18deg); } }
        @keyframes spotBadgeBounce { 0% { opacity: 0; transform: scale(0.3) rotate(-14deg); } 55% { transform: scale(1.15) rotate(4deg); } 100% { opacity: 1; transform: scale(1) rotate(-6deg); } }
        @keyframes spotBadgePulse { 0%,100% { transform: scale(1) rotate(-6deg); } 50% { transform: scale(1.07) rotate(-4deg); } }
        @keyframes spotFloat { 0% { transform: translateY(105vh) scale(0.6); opacity: 0; } 12% { opacity: 0.9; } 100% { transform: translateY(-8vh) scale(1.15); opacity: 0; } }
        @keyframes spotCtaPulse { 0%,100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(140,198,62,0.55); } 50% { transform: scale(1.05); box-shadow: 0 0 0 14px rgba(140,198,62,0); } }
        @keyframes spotUnderline { 0% { transform: scaleX(0); } 100% { transform: scaleX(1); } }
      `}</style>
      {/* Scène */}
      <div key={scene} className="absolute inset-0">
        <img src={s.img} alt="" className="w-full h-full object-cover"
          style={{ animation: `${['spotKbA', 'spotKbB', 'spotKbC', 'spotKbD'][scene % 4]} ${SCENE_MS + 700}ms ease-in-out forwards` }} />
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, rgba(10,4,20,0.35) 0%, rgba(10,4,20,0.15) 40%, rgba(10,4,20,0.88) 100%)' }} />
        {/* Balayage lumineux qui traverse l'image */}
        <div className="absolute inset-y-0 w-[26%] pointer-events-none"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.32), transparent)', animation: `spotSweep ${SCENE_MS}ms 300ms ease-in-out forwards` }} />
        <div className="absolute inset-0 pointer-events-none bg-white" style={{ animation: 'spotFlash 500ms ease-out forwards' }} />
        {/* Bulles ×3 flottantes */}
        {!s.final && [0, 1, 2].map((k) => (
          <span key={k} className="absolute font-black text-[#8CC63E] pointer-events-none select-none"
            style={{ left: `${14 + k * 32}%`, fontSize: k === 1 ? '2.2rem' : '1.4rem', opacity: 0,
              textShadow: '0 2px 14px rgba(0,0,0,0.5)',
              animation: `spotFloat ${SCENE_MS + 1800}ms ${300 + k * 800}ms linear forwards` }}>×3</span>
        ))}
        {/* Badge LOT ×3 qui rebondit */}
        {!s.final && (
          <div className="absolute top-[11vh] left-[4vw] px-4 py-2 rounded-2xl font-black text-[#1F2A12] text-lg sm:text-2xl"
            style={{ background: 'linear-gradient(135deg, #8CC63E, #D9B35A)', boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
              animation: `spotBadgeBounce 700ms 350ms cubic-bezier(0.34,1.56,0.64,1) backwards, spotBadgePulse 1.6s 1100ms ease-in-out infinite` }}>
            LOT ×3
          </div>
        )}
        {/* Bandes ciné */}
        <div className="absolute top-0 left-0 right-0 h-[6vh] bg-black" />
        <div className="absolute bottom-0 left-0 right-0 h-[6vh] bg-black" />
        {/* Textes */}
        <div className="absolute inset-x-0 bottom-[12vh] px-6 text-center">
          <p className="text-[#8CC63E] font-bold text-xs sm:text-sm uppercase m-0"
            style={{ animation: 'spotKicker 900ms ease-out forwards', letterSpacing: '0.28em' }}>{s.kicker}</p>
          <h2 className="text-white font-black m-0 mt-2 text-3xl sm:text-5xl lg:text-6xl leading-tight"
            style={{ animation: 'spotGlow 2.5s 1s ease-in-out infinite', fontFamily: 'inherit' }}>
            {s.title.split(' ').map((w, wi) => (
              <span key={wi} className="inline-block mr-[0.28em]"
                style={{ animation: `spotWordPop 620ms ${220 + wi * 110}ms cubic-bezier(0.34,1.56,0.64,1) backwards` }}>{w}</span>
            ))}
          </h2>
          <span className="block mx-auto mt-2 h-[3px] w-24 sm:w-40 rounded-full origin-center"
            style={{ background: 'linear-gradient(90deg, #8CC63E, #D9B35A)', animation: `spotUnderline 600ms ${300 + s.title.split(' ').length * 110}ms ease-out backwards` }} />
          <p className="text-white/85 text-sm sm:text-lg m-0 mt-3" style={{ animation: 'spotFadeUp 800ms 650ms ease-out backwards' }}>{s.sub}</p>
          {s.final && (
            <div style={{ animation: 'spotFadeUp 800ms 900ms ease-out backwards' }} className="mt-5 flex items-center justify-center gap-3 flex-wrap">
              <button type="button" data-testid="spot-cta-pass" onClick={() => {
                fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/spot/cta`, { method: 'POST' }).catch(() => {});
                onClose();
                navigate('/pass-lolodrive');
              }}
                className="px-6 h-12 rounded-full font-bold text-sm text-[#1F0A33] hover:brightness-110 transition-[filter]"
                style={{ background: 'linear-gradient(135deg, #D9B35A, #8CC63E)', animation: 'spotCtaPulse 1.8s 1.6s ease-in-out infinite' }}>
                <Ticket className="w-4 h-4 inline mr-2" /> Découvrir le PASS LOLODRIVE
              </button>
            </div>
          )}
        </div>
      </div>
      {/* Progression scènes */}
      <div className="absolute top-[7vh] left-1/2 -translate-x-1/2 flex gap-1.5 z-10">
        {SCENES.map((_, i) => (
          <div key={i} className="h-1 w-5 sm:w-9 rounded-full bg-white/25 overflow-hidden">
            {i < scene || done ? <div className="h-full w-full bg-[#D9B35A]" />
              : i === scene ? <div key={scene} className="h-full bg-[#D9B35A]" style={{ animation: `spotBar ${SCENE_MS}ms linear forwards` }} /> : null}
          </div>
        ))}
      </div>
      {done && (
        <div className="absolute bottom-[8vh] left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 flex-wrap justify-center">
          <button type="button" data-testid="spot-replay" onClick={() => { setScene(0); setDone(false); }}
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
      <button type="button" data-testid="spot-close" onClick={onClose}
        className="absolute top-[8vh] right-4 z-10 p-2 rounded-full text-white bg-white/10 border border-white/25 hover:bg-white/20 transition-colors">
        <X className="w-5 h-5" />
      </button>
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
