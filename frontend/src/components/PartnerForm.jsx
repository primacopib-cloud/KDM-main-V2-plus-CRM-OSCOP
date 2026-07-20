import { useEffect, useState } from 'react';
import { ChevronDown, Handshake, Send } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const inp = 'h-10 px-3 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35 w-full';

export const PartnerForm = () => {
  const [open, setOpen] = useState(false);
  const [types, setTypes] = useState([]);
  const [sent, setSent] = useState(false);
  const [f, setF] = useState({ type: '', name: '', company: '', email: '', phone: '', message: '' });

  useEffect(() => {
    if (!open || types.length) return;
    fetch(`${API}/partners/types`)
      .then((r) => r.json())
      .then((d) => { setTypes(d.items || []); if (d.items?.length) setF((p) => ({ ...p, type: d.items[0].code })); })
      .catch(() => {});
  }, [open, types.length]);

  const submit = async (e) => {
    e.preventDefault();
    const r = await fetch(`${API}/partners/apply`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(f),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur lors de l\'envoi');
    setSent(true);
    toast.success('Candidature envoyée — nous revenons vers vous rapidement');
  };

  return (
    <div className="mt-4">
      <button type="button" onClick={() => setOpen(!open)} data-testid="footer-partner-toggle"
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg bg-[#D9B35A]/10 border border-[#D9B35A]/30 text-[#E9CF8E] text-sm font-semibold hover:bg-[#D9B35A]/20 transition-colors">
        <span className="inline-flex items-center gap-2"><Handshake className="w-4 h-4" /> Devenir partenaire</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="mt-3 p-4 rounded-xl bg-white/[0.04] border border-white/[0.08]" data-testid="footer-partner-form">
          {sent ? (
            <p className="text-sm text-emerald-400 font-semibold" data-testid="partner-form-success">Merci ! Votre candidature a bien été transmise à la coopérative.</p>
          ) : (
            <form onSubmit={submit} className="space-y-2.5">
              <select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })} data-testid="partner-form-type"
                className={inp} style={{ colorScheme: 'dark' }} required>
                {types.map((t) => <option key={t.code} value={t.code} style={{ background: '#2A1045' }}>{t.label}</option>)}
              </select>
              <div className="grid grid-cols-2 gap-2.5">
                <input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Nom complet *" data-testid="partner-form-name" className={inp} required />
                <input value={f.company} onChange={(e) => setF({ ...f, company: e.target.value })} placeholder="Société" data-testid="partner-form-company" className={inp} />
              </div>
              <div className="grid grid-cols-2 gap-2.5">
                <input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} placeholder="Email *" data-testid="partner-form-email" className={inp} required />
                <input value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} placeholder="Téléphone" data-testid="partner-form-phone" className={inp} />
              </div>
              <textarea value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} placeholder="Votre projet en quelques mots…" data-testid="partner-form-message"
                className="px-3 py-2 rounded-lg bg-white/[0.06] border border-white/15 text-sm text-white placeholder:text-white/35 w-full h-20 resize-none" />
              <button type="submit" data-testid="partner-form-submit"
                className="w-full h-10 rounded-lg text-sm font-bold inline-flex items-center justify-center gap-2 hover:brightness-110 transition-all"
                style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>
                <Send className="w-4 h-4" /> Envoyer ma candidature
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
};
