import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Link2, Copy, RefreshCw, Ban, Loader2, Mail } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { API, getAuthHeaders } from '../../services/http';

const TYPES = [
  ['VENDOR_PRO', 'Vendeur Pro'],
  ['BUYER_PRO', 'Acheteur Pro'],
  ['SPONSOR', 'Sponsor'],
];
const STATUS = {
  pending: ['En attente', 'bg-amber-500/15 text-amber-300 border-amber-500/30'],
  paid: ['Payé ✓', 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'],
  deactivated: ['Désactivé', 'bg-white/10 text-white/50 border-white/15'],
};
const eur = (c) => (c / 100).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
const inputCls = 'mt-1 bg-white/[0.04] border-white/10 text-white text-sm h-9';

export const PaymentLinksPanel = () => {
  const [links, setLinks] = useState([]);
  const [form, setForm] = useState({ email: '', amount: '', type: 'VENDOR_PRO', description: '' });
  const [busy, setBusy] = useState(false);

  const headers = { 'Content-Type': 'application/json', ...getAuthHeaders() };

  const load = useCallback(() => {
    fetch(`${API}/admin/payment-links`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setLinks(d.links || []))
      .catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const copy = (url) => { navigator.clipboard.writeText(url); toast.success('Lien copié'); };

  const create = async () => {
    const amount = parseFloat(String(form.amount).replace(',', '.'));
    if (!form.email.includes('@')) { toast.error('Email invalide'); return; }
    if (!amount || amount <= 0) { toast.error('Montant invalide'); return; }
    setBusy(true);
    try {
      const r = await fetch(`${API}/admin/payment-links`, {
        method: 'POST', headers, credentials: 'include',
        body: JSON.stringify({ email: form.email.trim(), amount_eur: amount, account_type: form.type, description: form.description.trim() || null }),
      });
      const d = await r.json();
      if (!r.ok) { toast.error(typeof d.detail === 'string' ? d.detail : 'Erreur'); return; }
      toast.success('Lien de paiement créé');
      copy(d.url);
      setForm({ email: '', amount: '', type: 'VENDOR_PRO', description: '' });
      load();
    } finally { setBusy(false); }
  };

  const refresh = async (id) => {
    const r = await fetch(`${API}/admin/payment-links/${id}/refresh`, { method: 'POST', headers: getAuthHeaders(), credentials: 'include' });
    if (r.ok) { const d = await r.json(); toast.success(d.status === 'paid' ? 'Paiement reçu ✓' : 'Toujours en attente'); load(); }
  };

  const deactivate = async (id) => {
    if (!window.confirm('Désactiver ce lien de paiement ?')) return;
    const r = await fetch(`${API}/admin/payment-links/${id}/deactivate`, { method: 'POST', headers: getAuthHeaders(), credentials: 'include' });
    if (r.ok) { toast.success('Lien désactivé'); load(); } else toast.error('Échec de la désactivation');
  };

  const mailto = (l) => `mailto:${l.email}?subject=${encodeURIComponent('Votre lien de paiement KDMARCHÉ × O\'SCOP')}&body=${encodeURIComponent(`Bonjour,\n\nVoici votre lien de paiement sécurisé (${eur(l.amount_cents)}) :\n${l.url}\n\nCordialement,\nL'équipe KDMARCHÉ × O'SCOP`)}`;

  return (
    <div className="glass-panel-soft rounded-[18px] p-5 mb-6" data-testid="payment-links-panel">
      <div className="flex items-center gap-2 mb-4">
        <Link2 className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm uppercase tracking-wider text-white/75 font-semibold m-0">Liens de paiement Stripe</h3>
      </div>

      <div className="grid md:grid-cols-[1.3fr_0.7fr_1fr_1.3fr_auto] gap-3 items-end mb-5">
        <div>
          <Label className="text-white/70 text-xs">Email du destinataire *</Label>
          <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="client@example.com" data-testid="paylink-email" className={inputCls} />
        </div>
        <div>
          <Label className="text-white/70 text-xs">Montant (€) *</Label>
          <Input value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })}
            placeholder="150.00" data-testid="paylink-amount" className={inputCls} />
        </div>
        <div>
          <Label className="text-white/70 text-xs">Type de compte *</Label>
          <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}
            data-testid="paylink-type"
            className="mt-1 w-full h-9 rounded-md bg-white/[0.04] border border-white/10 text-white text-sm px-2">
            {TYPES.map(([v, l]) => <option key={v} value={v} className="bg-[#2A1045]">{l}</option>)}
          </select>
        </div>
        <div>
          <Label className="text-white/70 text-xs">Description (optionnel)</Label>
          <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Ex : cotisation 2026" data-testid="paylink-description" className={inputCls} />
        </div>
        <button type="button" onClick={create} disabled={busy} data-testid="paylink-create-btn"
          className="h-9 px-4 rounded-lg text-sm font-semibold bg-[#D9B35A] text-black hover:bg-[#c5a04b] inline-flex items-center gap-2 disabled:opacity-50">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Link2 size={14} />} Générer le lien
        </button>
      </div>

      {links.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-[10px] uppercase tracking-wider text-white/45">
                <th className="text-left py-2 pr-3">Email</th>
                <th className="text-left py-2 pr-3">Montant</th>
                <th className="text-left py-2 pr-3">Type</th>
                <th className="text-left py-2 pr-3">Statut</th>
                <th className="text-left py-2 pr-3">Créé le</th>
                <th className="text-right py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {links.map((l) => {
                const [label, cls] = STATUS[l.status] || STATUS.pending;
                return (
                  <tr key={l.id} className="border-b border-white/[0.05]" data-testid={`paylink-row-${l.id}`}>
                    <td className="py-2 pr-3 text-white/80">{l.email}</td>
                    <td className="py-2 pr-3 font-bold text-[#E9CF8E]">{eur(l.amount_cents)}</td>
                    <td className="py-2 pr-3 text-white/60">{(TYPES.find(([v]) => v === l.account_type) || [])[1] || l.account_type}</td>
                    <td className="py-2 pr-3"><span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${cls}`}>{label}</span></td>
                    <td className="py-2 pr-3 text-white/45 text-xs">{new Date(l.created_at).toLocaleDateString('fr-FR')}</td>
                    <td className="py-2">
                      <div className="flex justify-end gap-1.5">
                        <button type="button" title="Copier le lien" onClick={() => copy(l.url)} data-testid={`paylink-copy-${l.id}`}
                          className="p-1.5 rounded-lg bg-white/[0.05] border border-white/10 text-white/60 hover:bg-white/10">
                          <Copy size={13} />
                        </button>
                        <a href={mailto(l)} title="Envoyer par email" data-testid={`paylink-mail-${l.id}`}
                          className="p-1.5 rounded-lg bg-[#5B9BD5]/10 border border-[#5B9BD5]/25 text-[#8fc1ec] hover:bg-[#5B9BD5]/20">
                          <Mail size={13} />
                        </a>
                        {l.status === 'pending' && (
                          <>
                            <button type="button" title="Vérifier le paiement" onClick={() => refresh(l.id)} data-testid={`paylink-refresh-${l.id}`}
                              className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 hover:bg-emerald-500/20">
                              <RefreshCw size={13} />
                            </button>
                            <button type="button" title="Désactiver" onClick={() => deactivate(l.id)} data-testid={`paylink-deactivate-${l.id}`}
                              className="p-1.5 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400 hover:bg-red-500/20">
                              <Ban size={13} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {links.length === 0 && <p className="text-white/40 text-xs m-0">Aucun lien créé pour l&apos;instant. Le lien est copié automatiquement après création.</p>}
    </div>
  );
};
