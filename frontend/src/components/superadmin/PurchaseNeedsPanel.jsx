import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ShoppingCart, UserPlus, Globe, Loader2 } from 'lucide-react';
import { getAuthHeaders } from '../../services/http';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const STATUS = {
  NEW: ['Nouveau', 'text-amber-300 bg-amber-500/10 border-amber-400/40'],
  ASSIGNED: ['Assigné', 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/30'],
  VENDOR_ACCEPTED: ['Accepté vendeur', 'text-[#8CC63E] bg-[#8CC63E]/15 border-[#8CC63E]/50'],
  VENDOR_DECLINED: ['Décliné vendeur', 'text-red-300 bg-red-500/10 border-red-400/40'],
  OFFER_ACCEPTED: ['Offre acceptée client', 'text-[#8CC63E] bg-[#8CC63E]/20 border-[#8CC63E]/60'],
};

// Superadmin : besoins d'achat déposés par les visiteurs
export const PurchaseNeedsPanel = () => {
  const [needs, setNeeds] = useState([]);
  const [stats, setStats] = useState(null);
  const load = () => {
    fetch(`${API_URL}/api/admin/purchase-needs`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { needs: [] })).then((d) => setNeeds(d.needs || [])).catch(() => {});
    fetch(`${API_URL}/api/admin/purchase-needs/stats`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then(setStats).catch(() => {});
  };
  useEffect(load, []);

  const post = async (url, body, okMsg) => {
    try {
      const res = await fetch(url, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: body ? JSON.stringify(body) : undefined,
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || 'Erreur');
      toast.success(okMsg);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const [assignNeed, setAssignNeed] = useState(null);
  const [assignees, setAssignees] = useState(null);
  const [assignEmail, setAssignEmail] = useState('');

  const assign = (n) => {
    setAssignNeed(n);
    setAssignEmail(n.assigned_vendor || '');
    if (!assignees) {
      fetch(`${API_URL}/api/admin/spaces/assignees`, { headers: getAuthHeaders(), credentials: 'include' })
        .then((r) => (r.ok ? r.json() : { vendors: [], coopers: [] })).then(setAssignees).catch(() => setAssignees({ vendors: [], coopers: [] }));
    }
  };

  const confirmAssign = async () => {
    if (!assignEmail.trim()) return;
    await post(`${API_URL}/api/admin/purchase-needs/${assignNeed.id}/assign`,
      { vendor_email: assignEmail.trim() }, 'Besoin assigné — notifié par email');
    setAssignNeed(null);
  };

  return (
    <div className="rounded-2xl p-5 mt-6 bg-white/[0.03] border border-white/[0.08]" data-testid="purchase-needs-panel">
      <div className="flex items-center gap-2 mb-3">
        <ShoppingCart className="w-4 h-4 text-[#D9B35A]" />
        <h3 className="text-sm font-bold text-[#E9CF8E] m-0">Besoins d'achat visiteurs ({needs.length})</h3>
      </div>
      {stats && stats.count > 0 && (
        <div className="mb-3 rounded-xl p-3 bg-white/[0.04] border border-white/[0.08]" data-testid="communityplace-revenue-stats">
          <p className="text-[11px] font-bold text-[#E9CF8E] m-0 mb-1.5">
            Revenus frais de publication CommunityPlace — {Number(stats.total_eur).toFixed(2)} € encaissés ({stats.count} paiement{stats.count > 1 ? 's' : ''})
            <button type="button" data-testid="communityplace-csv-btn"
              onClick={async () => {
                const r = await fetch(`${API_URL}/api/admin/purchase-needs/stats/csv`, { headers: getAuthHeaders(), credentials: 'include' });
                const blob = await r.blob();
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = 'revenus_communityplace.csv';
                a.click();
                URL.revokeObjectURL(a.href);
              }}
              className="ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold text-[#1F2A12] bg-[#D9B35A] hover:brightness-110">
              Export CSV
            </button>
          </p>
          <div className="flex flex-wrap gap-2">
            {stats.months.map((m) => (
              <span key={m.month} className="px-2 py-0.5 rounded-full text-[10px] text-white/80 bg-white/[0.05] border border-white/15">
                {m.month} · {Number(m.revenue_eur).toFixed(2)} €
              </span>
            ))}
          </div>
        </div>
      )}
      {!needs.length ? (
        <p className="text-[11px] text-white/40 m-0">Aucun besoin d'achat déposé pour le moment.</p>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {needs.map((n) => {
            const [label, cls] = STATUS[n.status] || STATUS.NEW;
            return (
              <div key={n.id} className="rounded-xl px-3 py-2.5 bg-white/[0.02] border border-white/[0.06] text-[11px] text-white/70" data-testid={`need-row-${n.id}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-white font-semibold">{n.reference ? `${n.reference} · ` : ''}{n.product}</span>
                  <span className="text-white/40">qté {n.quantity} · {n.territory}</span>
                  {n.budget_eur ? <span className="font-mono text-[#D9B35A]">{Number(n.budget_eur).toLocaleString('fr-FR')} €</span> : null}
                  {n.vendor_price_eur ? <span className="font-mono text-[#8CC63E]">offre {Number(n.vendor_price_eur).toLocaleString('fr-FR')} €</span> : null}
                  <span className={`px-2 py-0.5 rounded-full border font-semibold ${cls}`}>{label}</span>
                  {n.communityplace && (
                    <span className={`px-2 py-0.5 rounded-full border font-semibold ${n.communityplace_payment_status === 'PAID' ? 'text-[#8CC63E] bg-[#8CC63E]/10 border-[#8CC63E]/30' : 'text-sky-300 bg-sky-500/10 border-sky-400/40'}`}>
                      CommunityPlace {n.communityplace_payment_status === 'PAID' ? '· payé ✓' : n.communityplace_payment_status === 'PENDING' ? `· paiement ${Number(n.communityplace_fee_eur || 0).toLocaleString('fr-FR')} € en attente` : ''}
                    </span>
                  )}
                  <span className="ml-auto flex gap-1.5">
                    <button type="button" onClick={() => assign(n)} data-testid={`need-assign-${n.id}`}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-bold text-black bg-[#8CC63E] hover:bg-[#7ab52f] transition-colors">
                      <UserPlus className="w-3 h-3" /> Assigner
                    </button>
                    {!n.communityplace && (
                      <button type="button" data-testid={`need-community-${n.id}`}
                        onClick={() => {
                          const fee = window.prompt('Frais de publication CommunityPlace (€) facturés au demandeur :', '50');
                          if (fee && Number(fee) > 0) post(`${API_URL}/api/admin/purchase-needs/${n.id}/communityplace`, { fee_eur: Number(fee) }, 'Publié — lien de paiement Stripe envoyé au demandeur');
                        }}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-semibold text-[#E9CF8E] bg-white/[0.05] border border-[#D9B35A]/30 hover:bg-white/[0.1] transition-colors">
                        <Globe className="w-3 h-3" /> CommunityPlace
                      </button>
                    )}
                    {n.communityplace && !n.grouping_closed && (
                      <button type="button" data-testid={`need-close-grouping-${n.id}`}
                        onClick={() => {
                          if (window.confirm(`Clôturer le groupage de ${n.reference} ? Tous les participants seront notifiés par email.`)) {
                            post(`${API_URL}/api/admin/purchase-needs/${n.id}/close-grouping`, {}, 'Groupage clôturé — participants notifiés');
                          }
                        }}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-md font-semibold text-orange-300 bg-orange-500/10 border border-orange-400/40 hover:bg-orange-500/20 transition-colors">
                        🔒 Clôturer groupage
                      </button>
                    )}
                    {n.grouping_closed && (
                      <span className="px-2 py-1 rounded-md text-white/45 bg-white/[0.04] border border-white/10" data-testid={`need-grouping-closed-${n.id}`}>
                        Groupage clôturé ✓
                      </span>
                    )}
                  </span>
                </div>
                <p className="m-0 mt-1 text-white/45">
                  {n.company} — {n.contact_name} · {n.email} · {n.phone}
                  {n.deadline ? ` · échéance ${n.deadline}` : ''}
                  {n.assigned_vendor ? ` · vendeur : ${n.assigned_vendor}` : ''}
                </p>
                {n.description && <p className="m-0 mt-0.5 text-white/50 italic">{n.description}</p>}
                {(n.images || []).length > 0 && (
                  <div className="flex gap-1.5 mt-1.5" data-testid={`need-photos-${n.id}`}>
                    {n.images.map((u) => (
                      <a key={u} href={u.startsWith('http') ? u : `${API_URL}${u}`} target="_blank" rel="noreferrer">
                        <img src={u.startsWith('http') ? u : `${API_URL}${u}`} alt="photo produit"
                          className="w-14 h-14 object-cover rounded-lg border border-white/15 hover:border-[#D9B35A]/60 transition-colors" />
                      </a>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
      <Dialog open={!!assignNeed} onOpenChange={(v) => !v && setAssignNeed(null)}>
        <DialogContent className="bg-[#1F0A33] border-white/15 text-white max-w-md" data-testid="assign-dialog">
          <DialogHeader>
            <DialogTitle className="text-white">Assigner « {assignNeed?.product} »</DialogTitle>
          </DialogHeader>
          {!assignees ? (
            <div className="py-6 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-white/40" /></div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-white/60">Vendeur ou COOPER'S</label>
                <select value={assignEmail} onChange={(e) => setAssignEmail(e.target.value)} data-testid="assign-select"
                  className="w-full mt-1 h-9 px-2.5 rounded-md text-sm text-white bg-white/[0.05] border border-white/15">
                  <option value="" className="bg-[#1F0A33]">— Choisir —</option>
                  <optgroup label="Vendeurs" className="bg-[#1F0A33]">
                    {assignees.vendors.map((v) => (
                      <option key={v.email} value={v.email} className="bg-[#1F0A33]">{v.name} — {v.email}</option>
                    ))}
                  </optgroup>
                  <optgroup label="COOPER'S" className="bg-[#1F0A33]">
                    {assignees.coopers.length === 0 && <option disabled className="bg-[#1F0A33]">Aucun COOPER'S</option>}
                    {assignees.coopers.map((c) => (
                      <option key={c.email} value={c.email} className="bg-[#1F0A33]">{c.name} — {c.email}</option>
                    ))}
                  </optgroup>
                </select>
              </div>
              <div>
                <label className="text-xs text-white/60">Ou saisir un email directement</label>
                <input value={assignEmail} onChange={(e) => setAssignEmail(e.target.value)} data-testid="assign-email-input"
                  placeholder="email@exemple.com"
                  className="w-full mt-1 h-9 px-2.5 rounded-md text-sm text-white bg-white/[0.05] border border-white/15" />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAssignNeed(null)} className="text-white/60">Annuler</Button>
            <Button onClick={confirmAssign} disabled={!assignEmail.trim()} data-testid="assign-confirm"
              style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>
              Assigner
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
