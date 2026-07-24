import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Sparkles, X } from 'lucide-react';
import { API, getAuthHeaders, getSessionToken } from '../../services/http';
import { AiGuidePanel } from './AiGuidePanel';
import { GuidedTour } from './GuidedTour';
import { TOUR_STEPS } from './tourSteps';

const spaceFromPath = (p) => {
  if (p.startsWith('/superadmin') || p.startsWith('/admin')) return 'admin';
  if (p.startsWith('/espace-acheteur')) return 'buyer';
  if (p.startsWith('/vendor') || p.startsWith('/vendeur') || p.startsWith('/espace-vendeur')) return 'vendor';
  if (p.startsWith('/logicoop')) return 'operator';
  if (p.startsWith('/pos')) return 'pos';
  if (p.startsWith('/lolo-point')) return 'lolo_point';
  if (p.startsWith('/pass') || p.startsWith('/catalogue-lolodrive') || p.startsWith('/commandes')
    || p.startsWith('/wallet') || p.startsWith('/catalogue')) return 'member';
  return 'general';
};
const HIDDEN = ['/connexion', '/admin/connexion', '/inscription', '/mot-de-passe', '/reinitialiser', '/auth/'];
const getLang = () => {
  const l = localStorage.getItem('i18nextLng') || 'fr';
  return l.startsWith('gcf') ? 'gcf' : l.slice(0, 2);
};
const STUCK_DELAY_MS = 45000;

export const AiGuideWidget = () => {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [welcome, setWelcome] = useState(null);
  const [bootTip, setBootTip] = useState(null);
  const [tourActive, setTourActive] = useState(false);
  const lastSpace = useRef(null);
  const token = getSessionToken();
  const path = location.pathname;
  const space = spaceFromPath(path);
  const tourSteps = TOUR_STEPS[space];
  const tourDone = localStorage.getItem(`guidia_tour_${space}`);

  const startTour = () => {
    setOpen(false);
    setTourActive(true);
  };
  const endTour = () => {
    setTourActive(false);
    localStorage.setItem(`guidia_tour_${space}`, '1');
  };

  useEffect(() => {
    if (!token || lastSpace.current === space || HIDDEN.some((h) => path.startsWith(h)) || path === '/') return;
    lastSpace.current = space;
    fetch(`${API}/ai-guide/welcome?space=${space}&lang=${getLang()}`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setWelcome(d);
        if (!sessionStorage.getItem('guidia_welcomed')) {
          sessionStorage.setItem('guidia_welcomed', '1');
          setOpen(true);
        }
      }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, path]);

  useEffect(() => {
    if (!token || HIDDEN.some((h) => path.startsWith(h)) || path === '/') return undefined;
    let timer = null;
    let lastField = null;
    const fire = async () => {
      const key = `guidia_formhelp_${window.location.pathname}`;
      if (!lastField || sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, '1');
      const hint = lastField.placeholder || lastField.getAttribute('aria-label') || lastField.name
        || lastField.closest('form')?.getAttribute('data-testid') || 'formulaire en cours';
      try {
        const r = await fetch(`${API}/ai-guide/form-help`, {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
          body: JSON.stringify({ form_hint: hint, page: document.title, space, lang: getLang() }),
        });
        const d = await r.json();
        if (r.ok && d.tip) {
          setBootTip({ tip: d.tip.replace(/\*\*/g, ''), suggestions: d.suggestions || [], at: Date.now() });
          setOpen(true);
        }
      } catch { /* silencieux */ }
    };
    const arm = (e) => {
      const el = e.target;
      if (!el.matches || !el.matches('input, textarea, select')) return;
      if (el.closest('[data-testid="ai-guide-panel"]')) return;
      lastField = el;
      clearTimeout(timer);
      timer = setTimeout(fire, STUCK_DELAY_MS);
    };
    const reset = () => { if (lastField) { clearTimeout(timer); timer = setTimeout(fire, STUCK_DELAY_MS); } };
    document.addEventListener('focusin', arm);
    document.addEventListener('input', reset);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('focusin', arm);
      document.removeEventListener('input', reset);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, path, space]);

  if (!token || HIDDEN.some((h) => path.startsWith(h)) || path === '/') return null;

  return (
    <>
      {tourActive && tourSteps && <GuidedTour steps={tourSteps} onFinish={endTour} />}
      {open && welcome && (
        <AiGuidePanel key={space} welcome={welcome} space={space} lang={getLang()} bootTip={bootTip}
          tourAvailable={Boolean(tourSteps && !tourDone)} onStartTour={startTour}
          onClose={() => setOpen(false)} />
      )}
      <button type="button" data-testid="ai-guide-fab" aria-label="Ouvrir Oracle"
        onClick={() => {
          if (!welcome) {
            fetch(`${API}/ai-guide/welcome?space=${space}&lang=${getLang()}`, { credentials: 'include', headers: getAuthHeaders() })
              .then((r) => (r.ok ? r.json() : null)).then((d) => { if (d) { setWelcome(d); setOpen(true); } })
              .catch(() => {});
          } else setOpen(!open);
        }}
        className="fixed bottom-6 right-6 z-[70] w-14 h-14 rounded-full flex items-center justify-center shadow-2xl transition-transform hover:scale-110"
        style={{
          background: 'linear-gradient(135deg, #451F6B 0%, #2A1045 55%, #B8860B 130%)',
          border: '1.5px solid rgba(217,179,90,0.65)',
          boxShadow: '0 0 22px rgba(217,179,90,0.35), 0 8px 24px rgba(0,0,0,0.45)',
        }}>
        {open ? <X size={20} className="text-[#E9CF8E]" /> : <Sparkles size={22} className="text-[#E9CF8E]" />}
        {!open && (
          <span className="absolute inset-0 rounded-full animate-ping opacity-20"
            style={{ background: 'radial-gradient(circle, rgba(217,179,90,0.8), transparent 70%)' }} />
        )}
      </button>
    </>
  );
};
