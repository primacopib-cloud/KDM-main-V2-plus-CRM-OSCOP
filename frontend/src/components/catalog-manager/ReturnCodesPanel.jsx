import { useState, useEffect } from 'react';
import { Gift } from 'lucide-react';
import { toast } from 'sonner';
import { getAuthHeaders } from '../../services/http';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—');

// Génération manuelle de bons de retour pour un client précis
export const ReturnCodesPanel = () => {
  const [open, setOpen] = useState(false);
  const [orgs, setOrgs] = useState([]);
  const [codes, setCodes] = useState([]);
  const [form, setForm] = useState({ org_id: '', discount_percent: '', validity_hours: '', send_email: true });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    fetch(`${API_URL}/api/catalog/admin/return-codes/orgs`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => setOrgs(d.orgs || [])).catch(() => {});
    loadCodes();
  }, [open]);

  const loadCodes = () => {
    fetch(`${API_URL}/api/catalog/admin/return-codes`, { headers: getAuthHeaders() })
      .then((r) => r.json()).then((d) => setCodes(d.codes || [])).catch(() => {});
  };

  const generate = async () => {
    if (!form.org_id) { toast.error('Sélectionnez une organisation'); return; }
    setBusy(true);
    try {
      const payload = { org_id: form.org_id, send_email: form.send_email };
      if (form.discount_percent) payload.discount_percent = Number(form.discount_percent);
      if (form.validity_hours) payload.validity_hours = Number(form.validity_hours);
      const res = await fetch(`${API_URL}/api/catalog/admin/return-codes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(payload),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(`Bon ${d.code} (−${d.discount_percent} % HT) généré pour ${d.org_name}${d.email_sent ? ' — email envoyé' : ''}`);
      loadCodes();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (c) => {
    if (!window.confirm(`Révoquer le bon ${c.code} (${c.org_name}) ?`)) return;
    try {
      const res = await fetch(`${API_URL}/api/catalog/admin/return-codes/${c.id}/revoke`, {
        method: 'POST', headers: getAuthHeaders(),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(`Bon ${c.code} révoqué`);
      loadCodes();
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <div className="rounded-xl bg-white/[0.02] border border-white/[0.08] mb-4" data-testid="return-codes-panel">
      <button type="button" onClick={() => setOpen(!open)} data-testid="return-codes-panel-toggle"
        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm font-semibold text-[#E9CF8E] hover:bg-white/[0.03] rounded-xl transition-colors">
        <Gift className="w-4 h-4" /> Bons de retour manuels (client précis)
        <span className="ml-auto text-xs text-white/40">{open ? 'Réduire' : 'Ouvrir'}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3">
          <div className="flex items-center gap-2 flex-wrap">
            <select value={form.org_id} onChange={(e) => setForm({ ...form, org_id: e.target.value })}
              data-testid="manual-code-org-select"
              className="h-8 px-2 rounded-md bg-[#2B1548] border border-white/15 text-white text-xs max-w-[260px]">
              <option value="">— Choisir une organisation —</option>
              {orgs.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
            <input type="number" min="1" max="50" placeholder="% (défaut)" value={form.discount_percent}
              onChange={(e) => setForm({ ...form, discount_percent: e.target.value })}
              data-testid="manual-code-percent"
              className="h-8 w-24 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" />
            <input type="number" min="1" max="720" placeholder="h (défaut)" value={form.validity_hours}
              onChange={(e) => setForm({ ...form, validity_hours: e.target.value })}
              data-testid="manual-code-hours"
              className="h-8 w-24 px-2 rounded-md bg-white/[0.05] border border-white/15 text-white text-xs" />
            <label className="flex items-center gap-1.5 text-[11px] text-white/60">
              <input type="checkbox" checked={form.send_email}
                onChange={(e) => setForm({ ...form, send_email: e.target.checked })}
                data-testid="manual-code-send-email" />
              Envoyer par email
            </label>
            <button type="button" onClick={generate} disabled={busy} data-testid="manual-code-generate"
              className="h-8 px-3 rounded-md text-[11px] font-bold text-black bg-[#D9B35A] hover:bg-[#c9a34a] transition-colors disabled:opacity-50">
              {busy ? '…' : 'Générer le bon'}
            </button>
          </div>
          {codes.length > 0 && (
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-white/40">
                  <th className="py-1.5 pr-2">Code</th><th className="py-1.5 pr-2">Organisation</th>
                  <th className="py-1.5 pr-2 text-center">Remise</th><th className="py-1.5 pr-2">Expire</th>
                  <th className="py-1.5 pr-2">Origine</th><th className="py-1.5 pr-2">Statut</th><th className="py-1.5">Action</th>
                </tr>
              </thead>
              <tbody>
                {codes.map((c) => (
                  <tr key={c.id} className="border-t border-white/[0.06] text-xs" data-testid="return-code-row">
                    <td className="py-2 pr-2 font-mono text-[#E9CF8E]">{c.code}</td>
                    <td className="py-2 pr-2 text-white/80">{c.org_name}</td>
                    <td className="py-2 pr-2 text-center text-white/70">−{c.discount_percent} %</td>
                    <td className="py-2 pr-2 text-white/50 font-mono">{fmtDate(c.expires_at)}</td>
                    <td className="py-2 pr-2 text-white/50">{c.manual ? `Manuel (${c.created_by || 'admin'})` : 'Relance auto'}</td>
                    <td className="py-2 pr-2">
                      {c.used
                        ? <span className="px-1.5 py-0.5 rounded text-[9px] font-bold text-emerald-300 bg-emerald-500/10 border border-emerald-400/30">UTILISÉ</span>
                        : c.revoked
                          ? <span className="px-1.5 py-0.5 rounded text-[9px] font-bold text-red-300 bg-red-500/15 border border-red-400/40" title={`Révoqué par ${c.revoked_by || 'admin'}`}>RÉVOQUÉ</span>
                          : new Date(c.expires_at) < new Date()
                            ? <span className="px-1.5 py-0.5 rounded text-[9px] font-bold text-white/40 bg-white/[0.05] border border-white/10">EXPIRÉ</span>
                            : <span className="px-1.5 py-0.5 rounded text-[9px] font-bold text-[#8CC63E] bg-[#8CC63E]/10 border border-[#8CC63E]/30">ACTIF</span>}
                    </td>
                    <td className="py-2">
                      {!c.used && !c.revoked && new Date(c.expires_at) >= new Date() && (
                        <button type="button" onClick={() => revoke(c)} data-testid={`revoke-code-${c.code}`}
                          className="px-2 py-1 rounded-md text-[9px] font-bold text-red-300 bg-red-500/10 border border-red-400/30 hover:bg-red-500/20 transition-colors">
                          Révoquer
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
};
