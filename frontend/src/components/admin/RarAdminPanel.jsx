import { useEffect, useState } from 'react';
import { ShieldCheck, Eye, EyeOff, Trash2, Plus, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import { rarAPI } from '../../services/api.rar';

const fmt = (c) => `${((c || 0) / 100).toLocaleString('fr-FR')} €`;

// Super Admin — Règlement à Réception Pro : comptes/plafonds, options de paiement, produits éligibles
export const RarAdminPanel = () => {
  const [accounts, setAccounts] = useState([]);
  const [options, setOptions] = useState([]);
  const [products, setProducts] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [reserves, setReserves] = useState([]);
  const [ceilInput, setCeilInput] = useState({});
  const [newOpt, setNewOpt] = useState('');

  const load = () => {
    rarAPI.adminAccounts().then((d) => setAccounts(d.accounts)).catch(() => {});
    rarAPI.adminPaymentOptions().then((d) => setOptions(d.options)).catch(() => {});
    rarAPI.adminProducts().then((d) => setProducts(d.products)).catch(() => {});
    rarAPI.adminDeliveries().then((d) => setDeliveries(d.orders || [])).catch(() => {});
    rarAPI.adminReserves().then((d) => setReserves(d.orders || [])).catch(() => {});
  };

  const resolve = async (o, action) => {
    const note = window.prompt(action === 'RELEASE'
      ? 'Note de levée de réserve (le montant redevient exigible) :'
      : 'Note d\'avoir (le montant est crédité et le plafond libéré) :') ?? '';
    try {
      await rarAPI.resolveReserve(o.id, action, note);
      toast.success(action === 'RELEASE' ? 'Réserve levée — montant exigible' : 'Avoir accordé — plafond libéré');
      load();
    } catch (e) { toast.error(e.message); }
  };
  useEffect(() => { load(); }, []);

  const decide = async (orgId, approve) => {
    try {
      await rarAPI.adminDecide({ org_id: orgId, approve, ceiling_cents: Math.round(parseFloat(ceilInput[orgId] || '0') * 100) });
      toast.success(approve ? 'Compte validé avec plafond' : 'Demande refusée');
      load();
    } catch (e) { toast.error(e.message); }
  };

  const updateAccount = async (orgId, payload) => {
    try { await rarAPI.adminUpdate({ org_id: orgId, ...payload }); toast.success('Compte mis à jour'); load(); }
    catch (e) { toast.error(e.message); }
  };

  const toggleOption = async (o) => {
    try { await rarAPI.adminUpdateOption(o.code, { visible: !o.visible }); load(); }
    catch (e) { toast.error(e.message); }
  };

  const addOption = async () => {
    if (!newOpt.trim()) return;
    try { await rarAPI.adminAddOption({ label: newOpt.trim() }); setNewOpt(''); toast.success('Option ajoutée'); load(); }
    catch (e) { toast.error(e.message); }
  };

  const deleteOption = async (code) => {
    try { await rarAPI.adminDeleteOption(code); toast.success('Option supprimée'); load(); }
    catch (e) { toast.error(e.message); }
  };

  const toggleProduct = async (p) => {
    try {
      await rarAPI.adminSetProduct(p.id, { rar_eligible: !p.rar_eligible });
      toast.success(!p.rar_eligible ? `${p.name} éligible RàR` : `${p.name} repassé EXW`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="rar-admin-panel">
      <h3 className="font-semibold flex items-center gap-2 mb-4">
        <ShieldCheck className="w-4 h-4 text-[#D9B35A]" /> Règlement à Réception Pro — comptes, options & produits
      </h3>

      {/* Comptes & plafonds */}
      <h4 className="text-xs uppercase tracking-wider text-white/50 font-bold mb-2">Comptes & plafonds</h4>
      {accounts.length === 0 && <p className="text-xs text-white/40 mb-3">Aucune demande pour le moment.</p>}
      <div className="space-y-2 mb-5">
        {accounts.map((a) => (
          <div key={a.org_id} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.07] flex flex-wrap items-center gap-2 justify-between" data-testid={`rar-account-${a.org_id}`}>
            <div className="text-xs">
              <b className="text-white">{a.org_name}</b>
              <span className={`ml-2 px-1.5 py-0.5 rounded text-[9px] font-bold ${a.status === 'APPROVED' ? 'text-emerald-300 bg-emerald-400/10' : a.status === 'PENDING' ? 'text-amber-300 bg-amber-400/10' : 'text-red-300 bg-red-400/10'}`}>{a.status}</span>
              {a.source === 'CREDISCOP_PACK' && <span className="ml-1.5 text-[9px] text-[#D9B35A]">via pack CREDI'SCOP</span>}
              {a.status === 'APPROVED' && (
                <span className="ml-2 text-white/50">plafond {fmt(a.ceiling_cents)} · mobilisé {fmt(a.in_use_cents)} · dispo <b className="text-emerald-300">{fmt(a.available_cents)}</b></span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              {a.status === 'PENDING' && (
                <>
                  <input type="number" placeholder="Plafond €" value={ceilInput[a.org_id] || ''}
                    onChange={(e) => setCeilInput({ ...ceilInput, [a.org_id]: e.target.value })}
                    className="w-24 px-2 py-1 rounded bg-black/30 border border-white/15 text-xs text-white"
                    data-testid={`rar-ceiling-input-${a.org_id}`} />
                  <button type="button" onClick={() => decide(a.org_id, true)} data-testid={`rar-approve-${a.org_id}`}
                    className="px-2 py-1 rounded text-[10px] font-bold text-emerald-300 bg-emerald-400/10 border border-emerald-400/30 flex items-center gap-1"><Check className="w-3 h-3" /> Valider</button>
                  <button type="button" onClick={() => decide(a.org_id, false)}
                    className="px-2 py-1 rounded text-[10px] font-bold text-red-300 bg-red-400/10 border border-red-400/30 flex items-center gap-1"><X className="w-3 h-3" /> Refuser</button>
                </>
              )}
              {a.status === 'APPROVED' && (
                <button type="button" onClick={() => updateAccount(a.org_id, { status: 'SUSPENDED' })}
                  className="px-2 py-1 rounded text-[10px] text-red-300 border border-red-400/30">Suspendre</button>
              )}
              {a.status === 'SUSPENDED' && (
                <button type="button" onClick={() => updateAccount(a.org_id, { status: 'APPROVED' })}
                  className="px-2 py-1 rounded text-[10px] text-emerald-300 border border-emerald-400/30">Réactiver</button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Options de paiement panier */}
      <h4 className="text-xs uppercase tracking-wider text-white/50 font-bold mb-2">Options de paiement au panier (ajouter / masquer / supprimer)</h4>
      <div className="space-y-1.5 mb-2">
        {options.map((o) => (
          <div key={o.code} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.07] text-xs" data-testid={`payment-option-${o.code}`}>
            <span className={o.visible ? 'text-white' : 'text-white/35 line-through'}>
              <b>{o.label}</b> <span className="text-white/40">({o.code}{o.builtin ? ' · native' : ''})</span>
            </span>
            <span className="flex items-center gap-1.5">
              <button type="button" onClick={() => toggleOption(o)} data-testid={`payment-option-toggle-${o.code}`}
                className="p-1 rounded text-white/60 hover:text-white border border-white/15" title={o.visible ? 'Masquer' : 'Afficher'}>
                {o.visible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
              </button>
              {!o.builtin && (
                <button type="button" onClick={() => deleteOption(o.code)} className="p-1 rounded text-red-300 border border-red-400/30">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </span>
          </div>
        ))}
      </div>
      <div className="flex gap-1.5 mb-5">
        <input value={newOpt} onChange={(e) => setNewOpt(e.target.value)} placeholder="Nouvelle option (libellé)"
          className="flex-1 px-2 py-1.5 rounded bg-black/30 border border-white/15 text-xs text-white" data-testid="payment-option-new-input" />
        <button type="button" onClick={addOption} data-testid="payment-option-add-btn"
          className="px-2.5 py-1.5 rounded text-[10px] font-bold text-black bg-[#D9B35A] flex items-center gap-1"><Plus className="w-3 h-3" /> Ajouter</button>
      </div>

      {/* Produits éligibles */}
      <h4 className="text-xs uppercase tracking-wider text-white/50 font-bold mb-2">Produits éligibles au règlement à réception</h4>
      <div className="grid md:grid-cols-2 gap-1.5 max-h-[300px] overflow-y-auto pr-1">
        {products.map((p) => (
          <label key={p.id} className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.02] border border-white/[0.07] text-xs cursor-pointer" data-testid={`rar-product-${p.sku}`}>
            <input type="checkbox" checked={!!p.rar_eligible} onChange={() => toggleProduct(p)}
              className="accent-[#D9B35A]" data-testid={`rar-product-toggle-${p.sku}`} />
            <span className="flex-1 truncate text-white/80">{p.name}</span>
            {p.rar_eligible
              ? <span className="text-[9px] text-emerald-300">✓ Éligible · {p.rar_delivery_mode || "LOGI'SCOP"}</span>
              : <span className="text-[9px] text-sky-300">EXW — à l'enlèvement</span>}
          </label>
        ))}
      </div>
      {/* Livraisons RàR (Lot E) */}
      <h4 className="text-xs uppercase tracking-wider text-white/50 font-bold mb-2 mt-5">Livraisons LOGI'SCOP — commandes sans acompte</h4>
      {deliveries.length === 0 && <p className="text-xs text-white/40 mb-3">Aucune commande RàR.</p>}
      <div className="space-y-1.5">
        {deliveries.map((o) => (
          <div key={o.id} className="flex flex-wrap items-center justify-between gap-2 p-2 rounded-lg bg-white/[0.02] border border-white/[0.07] text-xs" data-testid={`rar-admin-delivery-${o.order_number}`}>
            <span>
              <b className="text-white">{o.order_number}</b> · {fmt(o.total_ttc_cents)}
              {o.rar_disputed_cents > 0 && <span className="ml-1.5 text-amber-300">({fmt(o.rar_disputed_cents)} sous réserves)</span>}
              <span className="ml-1.5 text-[9px] px-1.5 py-0.5 rounded-full text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/30">{o.rar_status}</span>
              {o.payment_status === 'succeeded' && <span className="ml-1 text-[9px] text-emerald-300">✓ encaissé</span>}
            </span>
            <span className="flex gap-1.5">
              {o.payment_status !== 'succeeded' && o.rar_status === 'Commande acceptée sous plafond' && (
                <button type="button" data-testid={`rar-start-delivery-${o.order_number}`}
                  onClick={async () => { try { await rarAPI.adminStartDelivery(o.id, "LOGI'SCOP"); toast.success('OTP envoyé au client'); load(); } catch (e) { toast.error(e.message); } }}
                  className="px-2 py-1 rounded text-[10px] font-bold text-sky-300 bg-sky-400/10 border border-sky-400/30">
                  🚚 Livrer (envoyer OTP)
                </button>
              )}
              {o.payment_status !== 'succeeded' && ['Règlement déclenché', 'Réserves en cours de traitement'].includes(o.rar_status) && (
                <button type="button" data-testid={`rar-collect-${o.order_number}`}
                  onClick={async () => { try { await rarAPI.adminMarkCollected(o.id); toast.success('Encaissement confirmé — plafond rétabli'); load(); } catch (e) { toast.error(e.message); } }}
                  className="px-2 py-1 rounded text-[10px] font-bold text-emerald-300 bg-emerald-400/10 border border-emerald-400/30">
                  💶 Paiement encaissé
                </button>
              )}
              {['Règlement déclenché', 'Réserves en cours de traitement', 'Plafond rétabli'].includes(o.rar_status) && (
                <button type="button" data-testid={`rar-admin-proof-pdf-${o.order_number}`}
                  onClick={() => rarAPI.downloadProofPdf(o.id, o.order_number).catch((e) => toast.error(e.message))}
                  className="px-2 py-1 rounded text-[10px] text-white/60 border border-white/20 hover:text-white">
                  📄 BL PDF
                </button>
              )}
            </span>
          </div>
        ))}
      </div>

      {/* Réserves à instruire */}
      <h4 className="text-xs uppercase tracking-wider text-white/50 font-bold mb-2 mt-5">Réserves en cours d'instruction</h4>
      {reserves.length === 0 && <p className="text-xs text-white/40">Aucune réserve en attente.</p>}
      <div className="space-y-1.5">
        {reserves.map((o) => (
          <div key={o.id} className="p-2.5 rounded-lg bg-amber-400/[0.04] border border-amber-400/25 text-xs" data-testid={`rar-reserve-${o.order_number}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <b className="text-white">{o.order_number}</b>
                <span className="ml-2 text-amber-300 font-bold">{fmt(o.rar_disputed_cents)} suspendus</span>
                <span className="ml-1.5 text-white/45">· exigible {fmt(o.cod_amount_due_cents)} / {fmt(o.total_ttc_cents)}</span>
                {o.receiver_name && <span className="ml-1.5 text-white/40">· signé par {o.receiver_name}</span>}
              </span>
              <span className="flex gap-1.5">
                <button type="button" onClick={() => resolve(o, 'RELEASE')} data-testid={`rar-release-${o.order_number}`}
                  className="px-2 py-1 rounded text-[10px] font-bold text-emerald-300 bg-emerald-400/10 border border-emerald-400/30">
                  ✓ Lever la réserve
                </button>
                <button type="button" onClick={() => resolve(o, 'CREDIT')} data-testid={`rar-credit-${o.order_number}`}
                  className="px-2 py-1 rounded text-[10px] font-bold text-sky-300 bg-sky-400/10 border border-sky-400/30">
                  💳 Accorder un avoir
                </button>
              </span>
            </div>
            {(o.reserves || []).map((r, i) => (
              <p key={i} className="mt-1 text-[10px] text-amber-200/70">• {r.product_name} — qté {r.qty} : {r.reason || 'sans motif'}</p>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};
