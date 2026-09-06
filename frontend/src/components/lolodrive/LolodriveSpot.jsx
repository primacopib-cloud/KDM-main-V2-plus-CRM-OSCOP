import { useEffect, useRef, useState } from 'react';
import { X, Play, RotateCcw, Ticket } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const SCENES = [
  {
    img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/e5498487eea15f9539f2ee0e270da835d47df5e649a4a390c866313bf9d0a061.jpeg',
    kicker: 'LE CONCEPT', title: 'ACHETEZ PAR LOT ×3', sub: '3 fois plus malin. 3 fois moins cher à l\u2019unité.',
  },
  {
    img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/6d6384d010a917c8ad9abd345363c11bf463de2a3130fb7099b5b957081244b1.jpeg',
    kicker: 'EN LIGNE', title: 'COMMANDEZ EN 3 CLICS', sub: 'Tout le catalogue à prix mini, depuis votre canapé.',
  },
  {
    img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/c1dfa9a3d673b8eb6195961779888c6538d73ea356f123877722f54be5cc6a6d.jpeg',
    kicker: 'PRÈS DE CHEZ VOUS', title: 'RETRAIT EN POINT RELAIS', sub: 'Votre relais LOLODRIVE vous attend au coin de la rue.',
  },
  {
    img: 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/dac47ad5efe02567caf9c348bfc1e4b949a1959c6aeba549d0b86af0ac7ffcc3.jpeg',
    kicker: 'LOLODRIVE by O\u2019SCOP', title: 'LA VIE MOINS CHÈRE, ENSEMBLE', sub: 'Le PASS qui change vos courses. Rejoignez la coopérative.',
    final: true,
  },
];
const SCENE_MS = 4200;

// Spot publicitaire cinématique LOLODRIVE — scènes animées plein écran
export const LolodriveSpot = ({ onClose }) => {
  const navigate = useNavigate();
  const [scene, setScene] = useState(0);
  const [done, setDone] = useState(false);
  const timer = useRef(null);
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
        @keyframes spotKenBurns { 0% { transform: scale(1.12) translateX(2%); } 100% { transform: scale(1.0) translateX(-2%); } }
        @keyframes spotFadeUp { 0% { opacity: 0; transform: translateY(28px); } 100% { opacity: 1; transform: translateY(0); } }
        @keyframes spotKicker { 0% { opacity: 0; letter-spacing: 0.6em; } 100% { opacity: 1; letter-spacing: 0.28em; } }
        @keyframes spotBar { 0% { width: 0; } 100% { width: 100%; } }
        @keyframes spotGlow { 0%,100% { text-shadow: 0 0 24px rgba(217,179,90,0.55); } 50% { text-shadow: 0 0 48px rgba(217,179,90,0.95); } }
        @keyframes spotFlash { 0% { opacity: 0.9; } 100% { opacity: 0; } }
      `}</style>
      {/* Scène */}
      <div key={scene} className="absolute inset-0">
        <img src={s.img} alt="" className="w-full h-full object-cover"
          style={{ animation: `spotKenBurns ${SCENE_MS + 600}ms ease-out forwards` }} />
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, rgba(10,4,20,0.35) 0%, rgba(10,4,20,0.15) 40%, rgba(10,4,20,0.88) 100%)' }} />
        <div className="absolute inset-0 pointer-events-none bg-white" style={{ animation: 'spotFlash 500ms ease-out forwards' }} />
        {/* Bandes ciné */}
        <div className="absolute top-0 left-0 right-0 h-[6vh] bg-black" />
        <div className="absolute bottom-0 left-0 right-0 h-[6vh] bg-black" />
        {/* Textes */}
        <div className="absolute inset-x-0 bottom-[12vh] px-6 text-center">
          <p className="text-[#8CC63E] font-bold text-xs sm:text-sm uppercase m-0"
            style={{ animation: 'spotKicker 900ms ease-out forwards', letterSpacing: '0.28em' }}>{s.kicker}</p>
          <h2 className="text-white font-black m-0 mt-2 text-3xl sm:text-5xl lg:text-6xl leading-tight"
            style={{ animation: 'spotFadeUp 800ms 250ms ease-out backwards, spotGlow 2.5s 1s ease-in-out infinite', fontFamily: 'inherit' }}>
            {s.title}
          </h2>
          <p className="text-white/85 text-sm sm:text-lg m-0 mt-3" style={{ animation: 'spotFadeUp 800ms 550ms ease-out backwards' }}>{s.sub}</p>
          {s.final && (
            <div style={{ animation: 'spotFadeUp 800ms 900ms ease-out backwards' }} className="mt-5 flex items-center justify-center gap-3 flex-wrap">
              <button type="button" data-testid="spot-cta-pass" onClick={() => { onClose(); navigate('/pass-lolodrive'); }}
                className="px-6 h-12 rounded-full font-bold text-sm text-[#1F0A33] hover:brightness-110 transition-[filter]"
                style={{ background: 'linear-gradient(135deg, #D9B35A, #8CC63E)' }}>
                <Ticket className="w-4 h-4 inline mr-2" /> Découvrir le PASS LOLODRIVE
              </button>
            </div>
          )}
        </div>
      </div>
      {/* Progression scènes */}
      <div className="absolute top-[7vh] left-1/2 -translate-x-1/2 flex gap-1.5 z-10">
        {SCENES.map((_, i) => (
          <div key={i} className="h-1 w-14 sm:w-20 rounded-full bg-white/25 overflow-hidden">
            {i < scene || done ? <div className="h-full w-full bg-[#D9B35A]" />
              : i === scene ? <div key={scene} className="h-full bg-[#D9B35A]" style={{ animation: `spotBar ${SCENE_MS}ms linear forwards` }} /> : null}
          </div>
        ))}
      </div>
      {done && (
        <button type="button" data-testid="spot-replay" onClick={() => { setScene(0); setDone(false); }}
          className="absolute bottom-[8vh] left-1/2 -translate-x-1/2 z-10 inline-flex items-center gap-2 px-4 h-10 rounded-full text-xs font-bold text-white bg-white/10 border border-white/25 hover:bg-white/20 transition-colors">
          <RotateCcw className="w-3.5 h-3.5" /> Revoir le spot
        </button>
      )}
      <button type="button" data-testid="spot-close" onClick={onClose}
        className="absolute top-[8vh] right-4 z-10 p-2 rounded-full text-white bg-white/10 border border-white/25 hover:bg-white/20 transition-colors">
        <X className="w-5 h-5" />
      </button>
    </div>
  );
};

// Bouton déclencheur réutilisable
export const LolodriveSpotButton = ({ className = '' }) => {
  const [open, setOpen] = useState(false);
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
