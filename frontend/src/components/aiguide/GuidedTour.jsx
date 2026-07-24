import { useEffect, useState } from 'react';

export const GuidedTour = ({ steps, onFinish }) => {
  const [idx, setIdx] = useState(0);
  const [rect, setRect] = useState(null);
  const step = steps[idx];

  useEffect(() => {
    const el = document.querySelector(step.selector);
    if (!el) { setRect(null); return undefined; }
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const update = () => {
      const r = el.getBoundingClientRect();
      setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
    };
    const t = setTimeout(update, 350);
    window.addEventListener('resize', update);
    return () => { clearTimeout(t); window.removeEventListener('resize', update); };
  }, [step.selector]);

  const pad = 8;
  const below = rect && rect.top + rect.height + 190 < window.innerHeight;
  return (
    <div className="fixed inset-0 z-[90]" data-testid="guided-tour">
      <div className="absolute inset-0" onClick={onFinish} style={{ background: 'transparent' }} />
      {rect && (
        <div className="absolute rounded-xl pointer-events-none transition-all duration-300"
          style={{
            top: rect.top - pad, left: rect.left - pad,
            width: rect.width + pad * 2, height: rect.height + pad * 2,
            boxShadow: '0 0 0 9999px rgba(12,4,24,0.78), 0 0 24px rgba(217,179,90,0.55)',
            border: '2px solid #D9B35A',
          }} />
      )}
      <div className="absolute w-[320px] max-w-[calc(100vw-2rem)] rounded-2xl p-4 transition-all duration-300"
        data-testid="guided-tour-tooltip"
        style={{
          top: rect ? (below ? rect.top + rect.height + pad + 14 : Math.max(16, rect.top - 190)) : '40%',
          left: rect ? Math.min(Math.max(16, rect.left + rect.width / 2 - 160), window.innerWidth - 340) : 'calc(50% - 160px)',
          background: 'linear-gradient(180deg, rgba(42,16,69,0.98), rgba(30,12,52,0.99))',
          border: '1px solid rgba(217,179,90,0.5)', boxShadow: '0 20px 50px rgba(0,0,0,0.6)',
        }}>
        <p className="text-[10px] font-bold text-[#D9B35A] uppercase tracking-wider">
          Visite guidée · étape {idx + 1}/{steps.length}
        </p>
        <p className="text-[14px] font-bold text-[#E9CF8E] mt-1">{step.title}</p>
        <p className="text-[12px] text-white/75 mt-1 leading-relaxed">{step.text}</p>
        <div className="flex items-center gap-1.5 mt-3">
          {steps.map((_, i) => (
            <span key={i} className={`w-1.5 h-1.5 rounded-full ${i === idx ? 'bg-[#D9B35A]' : 'bg-white/20'}`} />
          ))}
          <span className="ml-auto flex gap-1.5">
            <button type="button" onClick={onFinish} data-testid="tour-skip"
              className="px-2.5 py-1.5 rounded-lg text-[11px] text-white/45 hover:text-white">Passer</button>
            {idx > 0 && (
              <button type="button" onClick={() => setIdx(idx - 1)} data-testid="tour-prev"
                className="px-2.5 py-1.5 rounded-lg text-[11px] text-white/70 border border-white/15 hover:text-white">Précédent</button>
            )}
            <button type="button" data-testid="tour-next"
              onClick={() => (idx + 1 < steps.length ? setIdx(idx + 1) : onFinish())}
              className="on-light px-3 py-1.5 rounded-lg text-[11px] font-bold text-[#2A1045]"
              style={{ background: 'linear-gradient(90deg, #E9CF8E, #D9B35A)' }}>
              {idx + 1 < steps.length ? 'Suivant' : 'Terminer'}
            </button>
          </span>
        </div>
      </div>
    </div>
  );
};
