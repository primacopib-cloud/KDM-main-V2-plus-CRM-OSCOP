import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Link2, Copy, RefreshCw, Ban, Loader2, Mail, MessageSquare } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { API, getAuthHeaders } from '../../services/http';
import { PaymentLinkSmsDialog } from './PaymentLinkSmsDialog';

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

// Parse un montant saisi à la française ou à l'anglaise : "1 000", "1.000,50", "1,000.50", "1000.5", "150,00 €"
export const parseAmount = (raw) => {
  let s = String(raw).replace(/[\s\u00a0€]/g, '');
  if (!s) return NaN;
  const lastComma = s.lastIndexOf(',');
  const lastDot = s.lastIndexOf('.');
  if (lastComma > -1 && lastDot > -1) {
    if (lastComma > lastDot) {
      s = s.replace(/\./g, '');
      const c = s.lastIndexOf(',');
      s = `${s.slice(0, c).replace(/,/g, '')}.${s.slice(c + 1)}`;
    } else {
      s = s.replace(/,/g, '');
    }
  } else if (lastComma > -1) {
    const decimals = s.length - lastComma - 1;
    const manyCommas = (s.match(/,/g) || []).length > 1;
    s = manyCommas || decimals === 3 ? s.replace(/,/g, '') : s.replace(',', '.');
  } else if (lastDot > -1) {
    const decimals = s.length - lastDot - 1;
    const manyDots = (s.match(/\./g) || []).length > 1;
    if (manyDots || decimals === 3) s = s.replace(/\./g, '');
  }
  if (!/^\d+(\.\d+)?$/.test(s)) return NaN;
  return Math.round(parseFloat(s) * 100) / 100;
};

export const PaymentLinksPanel = () => {
  const [links, setLinks] = useState([]);
  const [form, setForm] = useState({ email: '', amount: '', type: 'VENDOR_PRO', description: '', installments: 1 });
  const [busy, setBusy] = useState(false);
  const [smsLink, setSmsLink] = useState(null);

  const headers = { 'Content-Type': 'application/json', ...getAuthHeaders() };

  const load = useCallback(() => {
    fetch(`${API}/admin/payment-links`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setLinks(d.links || []))
      .catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const copy = (url) => {
    try {
      const p = navigator.clipboard?.writeText(url);
      if (p?.then) {
        p.then(() => toast.success('Lien copié'))
          .catch(() => toast.info('Copie automatique impossible — utilisez le bouton copier'));
      } else {
        toast.info('Copie automatique impossible — utilisez le bouton copier');
      }
    } catch {
      toast.info('Copie automatique impossible — utilisez le bouton copier');
    }
  };

  const create = async () => {
    const amount = parseAmount(form.amount);
    const n = Number(form.installments) || 1;
    if (!form.email.includes('@')) { toast.error('Email invalide'); return; }
    if (!Number.isFinite(amount) || amount <= 0) { toast.error('Montant invalide'); return; }
    if (amount / n > 999999.99) { toast.error(`Chaque échéance dépasse le plafond Stripe (999 999,99 €). Augmentez le nombre d'échéances.`); return; }
    if (n === 1 && amount > 999999.99) { toast.error('Maximum Stripe : 999 999,99 € par lien. Utilisez plusieurs échéances.'); return; }
    setBusy(true);
    try {
      const isSplit = n > 1;
      const body = isSplit
        ? { email: form.email.trim(), total_eur: amount, installments: n, account_type: form.type, description: form.description.trim() || null }
        : { email: form.email.trim(), amount_eur: amount, account_type: form.type, description: form.description.trim() || null };
      const r = await fetch(`${API}/admin/payment-links${isSplit ? '/split' : ''}`, {
        method: 'POST', headers, credentials: 'include',
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) {
        const msg = typeof d.detail === 'string' ? d.detail
          : Array.isArray(d.detail) ? d.detail.map((e) => e.msg || '').join(' — ') : 'Erreur';
        toast.error(msg);
        return;
      }
      if (isSplit) {
        toast.success(`${n} liens d'échéance créés (total ${eur(d.total_cents)})`);
      } else {
        toast.success('Lien de paiement créé');
        copy(d.url);
      }
      setForm({ email: '', amount: '', type: 'VENDOR_PRO', description: '', installments: 1 });
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

      <div className="grid md:grid-cols-[1.2fr_0.7fr_0.9fr_0.6fr_1.1fr_auto] gap-3 items-end mb-5">
        <div>
          <Label className="text-white/70 text-xs">Email du destinataire *</Label>
          <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="client@example.com" data-testid="paylink-email" className={inputCls} />
        </div>
        <div>
          <Label className="text-white/70 text-xs">Montant (€) *</Label>
          <Input value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })}
            placeholder="150.00" data-testid="paylink-amount" className={inputCls} />
          {form.amount && (
            <p className="text-[10.5px] m-0 mt-0.5" data-testid="paylink-amount-preview">
              {Number.isFinite(parseAmount(form.amount)) && parseAmount(form.amount) > 0
                ? (Number(form.installments) > 1
                  ? <span className="text-[#8CC63E]">= {form.installments} × {eur(Math.round(parseAmount(form.amount) * 100 / Number(form.installments)))}</span>
                  : <span className="text-[#8CC63E]">= {eur(Math.round(parseAmount(form.amount) * 100))}</span>)
                : <span className="text-red-400">Montant invalide</span>}
            </p>
          )}
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
          <Label className="text-white/70 text-xs">Échéances</Label>
          <select value={form.installments} onChange={(e) => setForm({ ...form, installments: Number(e.target.value) })}
            data-testid="paylink-installments" title="Découpe le montant total en plusieurs liens"
            className="mt-1 w-full h-9 rounded-md bg-white/[0.04] border border-white/10 text-white text-sm px-2">
            {[1, 2, 3, 4, 5, 6, 8, 10, 12].map((k) => (
              <option key={k} value={k} className="bg-[#2A1045]">{k === 1 ? '1 (unique)' : `${k}×`}</option>
            ))}
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
                    <td className="py-2 pr-3 text-white/80">
                      {l.email}
                      {l.description && <span className="block text-[10px] text-white/40">{l.description}</span>}
                    </td>
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
                          <button type="button" title={l.sms_sent_at ? `SMS déjà envoyé au ${l.sms_to}` : 'Envoyer par SMS'}
                            onClick={() => setSmsLink(l)} data-testid={`paylink-sms-${l.id}`}
                            className={`p-1.5 rounded-lg border ${l.sms_sent_at
                              ? 'bg-[#8CC63E]/20 border-[#8CC63E]/50 text-[#b5e07a]'
                              : 'bg-[#8CC63E]/10 border-[#8CC63E]/25 text-[#b5e07a] hover:bg-[#8CC63E]/20'}`}>
                            <MessageSquare size={13} />
                          </button>
                        )}
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
      {smsLink && <PaymentLinkSmsDialog link={smsLink} onClose={() => setSmsLink(null)} onSent={load} />}
    </div>
  );
};
