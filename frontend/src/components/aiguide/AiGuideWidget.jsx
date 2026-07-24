import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Sparkles, X } from 'lucide-react';
import { API, getAuthHeaders, getSessionToken } from '../../services/http';
import { AiGuidePanel } from './AiGuidePanel';

const spaceFromPath = (p) => {
  if (p.startsWith('/superadmin') || p.startsWith('/admin')) return 'admin';
  if (p.startsWith('/espace-acheteur')) return 'buyer';
  if (p.startsWith('/vendor') || p.startsWith('/vendeur')) return 'vendor';
  if (p.startsWith('/logicoop')) return 'operator';
  if (p.startsWith('/pos')) return 'pos';
  if (p.startsWith('/lolo-point')) return 'lolo_point';
  if (p.startsWith('/pass') || p.startsWith('/catalogue-lolodrive') || p.startsWith('/commandes')
    || p.startsWith('/wallet') || p.startsWith('/catalogue')) return 'member';
  return 'general';
};
const HIDDEN = ['/connexion', '/admin/connexion', '/inscription', '/mot-de-passe', '/reinitialiser', '/auth/'];

export const AiGuideWidget = () => {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [welcome, setWelcome] = useState(null);
  const lastSpace = useRef(null);
  const token = getSessionToken();
  const path = location.pathname;
  const space = spaceFromPath(path);

  useEffect(() => {
    if (!token || lastSpace.current === space || HIDDEN.some((h) => path.startsWith(h)) || path === '/') return;
    lastSpace.current = space;
    fetch(`${API}/ai-guide/welcome?space=${space}`, { credentials: 'include', headers: getAuthHeaders() })
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

  if (!token || HIDDEN.some((h) => path.startsWith(h)) || path === '/') return null;

  return (
    <>
      {open && welcome && (
        <AiGuidePanel key={space} welcome={welcome} space={space} onClose={() => setOpen(false)} />
      )}
      <button type="button" data-testid="ai-guide-fab" aria-label="Ouvrir GUID'IA"
        onClick={() => {
          if (!welcome) {
            fetch(`${API}/ai-guide/welcome?space=${space}`, { credentials: 'include', headers: getAuthHeaders() })
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
