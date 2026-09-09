import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { X, Send, Plus, Trash2, Info, ImagePlus, Handshake } from 'lucide-react';
import { SearchableCountryDropdown } from '../onboarding/CountryPhoneFields';
import { authAPI } from '../../services/api';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const inputCls = 'h-10 px-3 rounded-xl bg-white/[0.06] border border-white/15 text-white text-sm w-full placeholder:text-white/35';
const emptyItem = () => ({ product: '', quantity: '', budget_eur: '', description: '', images: [] });

// Formulaire visiteur / membre : dépôt d'un ou plusieurs besoins d'achat OU offres produit (une publication PAR produit)
export const PurchaseNeedForm = ({ onClose, initialType = 'DEMANDE' }) => {
  const [f, setF] = useState({ company: '', contact_name: '', email: '', phone: '', territory: 'Guadeloupe', deadline: '' });
  const [countryCode, setCountryCode] = useState('GP');
  const [dial, setDial] = useState('+590');
  const [items, setItems] = useState([emptyItem()]);
  const [listingType, setListingType] = useState(initialType);
  const [fees, setFees] = useState({ demand_fee_eur: 50, offer_fee_eur: 25 });
  const [coopers, setCoopers] = useState([]);
  const [cooperId, setCooperId] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [refs, setRefs] = useState([]);
  const [assignedCooper, setAssignedCooper] = useState(null);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const setItem = (i, k, v) => setItems((prev) => prev.map((it, j) => (j === i ? { ...it, [k]: v } : it)));
  const unitFee = listingType === 'OFFRE' ? fees.offer_fee_eur : fees.demand_fee_eur;

  useEffect(() => {
    fetch(`${API_URL}/api/public/communityplace/fees`).then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setFees(d)).catch(() => {});
    fetch(`${API_URL}/api/public/coopers`).then((r) => (r.ok ? r.json() : { coopers: [] }))
      .then((d) => setCoopers(d.coopers || [])).catch(() => {});
    if (authAPI.isAuthenticated()) {
      authAPI.getMe().then((me) => {
        setF((prev) => ({
          ...prev,
          company: prev.company || me.company_name || '',
          contact_name: prev.contact_name || me.contact_name || '',
          email: prev.email || me.email || '',
          phone: prev.phone || me.phone || '',
        }));
      }).catch(() => {});
    }
  }, []);

  const uploadImage = async (i, file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await fetch(`${API_URL}/api/public/purchase-needs/upload-image`, { method: 'POST', body: fd });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur upload');
      setItems((prev) => prev.map((it, j) => (j === i ? { ...it, images: [...it.images, d.url].slice(0, 2) } : it)));
    } catch (e) { toast.error(e.message); }
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/public/purchase-needs/batch`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...f, phone: `${dial} ${f.phone}`.trim(), country_code: countryCode, deadline: f.deadline || null,
          listing_type: listingType,
          cooper_id: cooperId || null,
          items: items.map((it) => ({
            product: it.product, quantity: it.quantity,
            budget_eur: it.budget_eur ? Number(it.budget_eur) : null,
            description: it.description || null,
            images: it.images.length ? it.images : null,
          })),
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail?.[0]?.msg || 'Envoi impossible — vérifiez les champs');
      const d = await res.json();
      setRefs(d.references || []);
      setAssignedCooper(d.assigned_cooper || null);
      setSent(true);
    } catch (err) { toast.error(typeof err.message === 'string' ? err.message : 'Erreur'); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="purchase-need-modal">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-3xl p-6 bg-[#241243] border border-[#D9B35A]/30">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="text-lg font-bold text-[#E9CF8E] m-0">{listingType === 'OFFRE' ? 'Publier une offre produit' : "Déposer un besoin d'achat"}</h3>
          <button type="button" onClick={onClose} data-testid="purchase-need-close"
            className="ml-auto p-1.5 rounded-lg text-white/60 hover:bg-white/[0.08] transition-colors"><X className="w-4 h-4" /></button>
        </div>
        <div className="flex gap-1.5 mb-3" data-testid="listing-type-toggle">
          {[['DEMANDE', "Besoin d'achat"], ['OFFRE', 'Offre produit']].map(([v, l]) => (
            <button key={v} type="button" onClick={() => setListingType(v)} data-testid={`listing-type-${v}`}
              className={`px-3 py-1.5 rounded-full text-[11px] font-bold border transition-colors ${listingType === v
                ? 'bg-[#D9B35A]/25 border-[#D9B35A]/60 text-[#E9CF8E]'
                : 'bg-white/[0.04] border-white/15 text-white/55 hover:text-white'}`}>
              {l}
            </button>
          ))}
          <span className="text-[10px] text-white/40 self-center ml-1" data-testid="listing-fee-hint">
            Publication payante · {Number(unitFee).toLocaleString('fr-FR')} € par {listingType === 'OFFRE' ? 'offre' : 'demande'}
          </span>
        </div>
        {sent ? (
          <div className="py-8 text-center" data-testid="purchase-need-success">
            <p className="text-[#8CC63E] font-bold text-base m-0">
              ✅ {listingType === 'OFFRE'
                ? (refs.length > 1 ? `${refs.length} offres produit publiées !` : 'Offre produit envoyée !')
                : (refs.length > 1 ? `${refs.length} besoins d'achat envoyés !` : "Besoin d'achat envoyé !")}
            </p>
            <div className="mt-2 space-y-1">
              {refs.map((r) => (
                <p key={r.reference} className="text-white font-mono text-sm m-0" data-testid="need-tracking-ref">{r.reference} — {r.product}</p>
              ))}
            </div>
            {assignedCooper && (
              <p className="text-[#E9CF8E] text-sm mt-2 m-0" data-testid="need-cooper-confirm">
                🤝 Assigné au COOPER'S <b>{assignedCooper}</b> — il vient d'être notifié par email.
              </p>
            )}
            <p className="text-white/60 text-sm mt-3">Un email de confirmation avec vos numéros de suivi vient de vous être envoyé. La Centrale O'SCOP vous recontacte après étude.</p>
          </div>
        ) : (
          <form onSubmit={submit}>
            <p className="text-xs text-white/55 m-0 mb-2">
              {listingType === 'OFFRE'
                ? "Décrivez votre offre de vente : la Centrale l'étudie, l'assigne à un COOPER'S et la publie sur la CommunityPlace."
                : "Décrivez votre besoin : la Centrale l'étudie, l'assigne à un vendeur référencé ou le publie sur la CommunityPlace."}
            </p>
            <div className="flex items-start gap-2 rounded-xl px-3 py-2 mb-3 bg-[#8CC63E]/10 border border-[#8CC63E]/35" data-testid="need-one-product-info">
              <Info className="w-4 h-4 text-[#8CC63E] shrink-0 mt-0.5" />
              <p className="text-[11px] text-white/75 m-0">
                <b>Une publication = un produit.</b> Ajoutez autant de produits que nécessaire ci-dessous : une publication distincte
                sera créée par produit, et le tarif de publication CommunityPlace ({Number(unitFee).toLocaleString('fr-FR')} €) s'applique <b>par publication</b>
                ({Number(unitFee).toLocaleString('fr-FR')} € × nombre de produits).
              </p>
            </div>
            {coopers.length > 0 && (
              <div className="flex items-center gap-2 rounded-xl px-3 py-2 mb-4 bg-white/[0.04] border border-[#D9B35A]/25">
                <Handshake className="w-4 h-4 text-[#D9B35A] shrink-0" />
                <select value={cooperId} onChange={(e) => setCooperId(e.target.value)} data-testid="need-cooper-select"
                  className="h-9 flex-1 px-2 rounded-lg bg-white/[0.06] border border-white/15 text-white text-xs">
                  <option value="" className="bg-[#241243]">Assigner à un COOPER'S (optionnel) — sinon la Centrale assigne</option>
                  {coopers.map((c) => (
                    <option key={c.id} value={c.id} className="bg-[#241243]">{c.name}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="grid gap-2.5 sm:grid-cols-2">
              <input required value={f.company} onChange={set('company')} placeholder="Société / Raison sociale *" className={inputCls} data-testid="need-company" />
              <input required value={f.contact_name} onChange={set('contact_name')} placeholder="Nom du contact *" className={inputCls} data-testid="need-contact" />
              <input required type="email" value={f.email} onChange={set('email')} placeholder="Email *" className={inputCls} data-testid="need-email" />
              <div className="flex gap-1.5">
                <div className="w-24 shrink-0">
                  <SearchableCountryDropdown mode="dial" value={countryCode} display={dial} testId="need-dial-select"
                    buttonClassName={inputCls}
                    onSelect={(c) => { setCountryCode(c.code); setDial(c.dial); }} />
                </div>
                <input required value={f.phone} onChange={set('phone')} placeholder="Téléphone *" className={inputCls} data-testid="need-phone" />
              </div>
              <SearchableCountryDropdown value={countryCode} display={f.territory} testId="need-territory"
                buttonClassName={inputCls}
                onSelect={(c) => { setCountryCode(c.code); setDial(c.dial); setF((prev) => ({ ...prev, territory: c.name })); }} />
              <input type="date" value={f.deadline} onChange={set('deadline')} className={inputCls} data-testid="need-deadline" title="Date limite souhaitée" />
            </div>
            <div className="mt-3 space-y-3">
              {items.map((it, i) => (
                <div key={i} className="rounded-2xl p-3 bg-white/[0.03] border border-white/[0.1]" data-testid={`need-item-${i}`}>
                  <div className="flex items-center mb-2">
                    <span className="text-[11px] font-bold text-[#E9CF8E]">Produit {i + 1}</span>
                    {items.length > 1 && (
                      <button type="button" onClick={() => setItems((prev) => prev.filter((_, j) => j !== i))} data-testid={`need-item-remove-${i}`}
                        className="ml-auto p-1 rounded text-white/50 hover:text-red-300 hover:bg-white/[0.06] transition-colors"><Trash2 className="w-3.5 h-3.5" /></button>
                    )}
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input required value={it.product} onChange={(e) => setItem(i, 'product', e.target.value)} placeholder={listingType === 'OFFRE' ? 'Produit proposé *' : 'Produit recherché *'} className={inputCls} data-testid={`need-product-${i}`} />
                    <input required value={it.quantity} onChange={(e) => setItem(i, 'quantity', e.target.value)} placeholder="Quantité (ex. 2 palettes, 500 unités) *" className={inputCls} data-testid={`need-quantity-${i}`} />
                    <input type="number" min="0" value={it.budget_eur} onChange={(e) => setItem(i, 'budget_eur', e.target.value)} placeholder="Budget estimé € (optionnel)" className={inputCls} data-testid={`need-budget-${i}`} />
                    <input value={it.description} onChange={(e) => setItem(i, 'description', e.target.value)} placeholder="Précisions : marque, normes…" className={inputCls} data-testid={`need-description-${i}`} />
                  </div>
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    {it.images.map((url, k) => (
                      <div key={url} className="relative">
                        <img src={url.startsWith('http') ? url : `${API_URL}${url}`} alt="" className="w-14 h-14 object-cover rounded-lg border border-white/15" />
                        <button type="button" onClick={() => setItem(i, 'images', it.images.filter((_, m) => m !== k))}
                          className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] leading-none">×</button>
                      </div>
                    ))}
                    {it.images.length < 2 && (
                      <label className="inline-flex items-center gap-1.5 px-3 h-9 rounded-lg text-[11px] font-semibold cursor-pointer text-[#E9CF8E] bg-[#D9B35A]/10 border border-[#D9B35A]/35 hover:bg-[#D9B35A]/20 transition-colors">
                        <ImagePlus className="w-3.5 h-3.5" /> Photo produit ({it.images.length}/2)
                        <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" data-testid={`need-image-input-${i}`}
                          onChange={(e) => { uploadImage(i, e.target.files?.[0]); e.target.value = ''; }} />
                      </label>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {items.length < 10 && (
              <button type="button" onClick={() => setItems((prev) => [...prev, emptyItem()])} data-testid="need-add-item"
                className="mt-2.5 inline-flex items-center gap-1.5 px-3 h-9 rounded-lg text-[12px] font-bold text-[#8CC63E] bg-[#8CC63E]/10 border border-[#8CC63E]/40 hover:bg-[#8CC63E]/20 transition-colors">
                <Plus className="w-3.5 h-3.5" /> Ajouter un autre produit
              </button>
            )}
            {items.length > 1 && (
              <p className="text-[11px] text-[#E9CF8E] m-0 mt-2" data-testid="need-fee-multiplier">
                💡 {items.length} produits = {items.length} publications — {Number(unitFee).toLocaleString('fr-FR')} € × {items.length} = {Number(unitFee * items.length).toLocaleString('fr-FR')} € en cas de publication CommunityPlace.
              </p>
            )}
            <button type="submit" disabled={busy} data-testid="purchase-need-submit"
              className="mt-4 w-full h-11 rounded-xl font-bold text-sm text-[#1F0A33] disabled:opacity-60 transition-opacity"
              style={{ background: 'linear-gradient(135deg, #D9B35A 0%, #b8933e 100%)' }}>
              <Send className="w-4 h-4 inline mr-2" /> {busy ? 'Envoi…' : listingType === 'OFFRE'
                ? (items.length > 1 ? `Publier mes ${items.length} offres produit` : 'Publier mon offre produit')
                : (items.length > 1 ? `Envoyer mes ${items.length} besoins d'achat` : "Envoyer mon besoin d'achat")}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
