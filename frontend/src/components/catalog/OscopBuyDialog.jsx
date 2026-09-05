import { useEffect, useState } from 'react';
import { Loader2, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { API } from '../../services/http';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

const eur = (cents) => `${(cents / 100).toFixed(2).replace('.', ',')} €`;

export const OscopBuyDialog = ({ product, onClose }) => {
  const [offer, setOffer] = useState(null);
  const [includeLogistics, setIncludeLogistics] = useState(false);
  const [qty, setQty] = useState('1');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API}/oscop-checkout/offer/${product.id}`)
      .then((r) => r.json())
      .then((d) => (d.price_ht_cents ? setOffer(d) : toast.error(d.detail || 'Offre indisponible')))
      .catch(() => toast.error('Offre indisponible'));
  }, [product.id]);

  const quantity = Math.max(1, parseInt(qty, 10) || 1);
  const goodsHt = offer ? offer.price_ht_cents * quantity : 0;
  const logiHt = offer && includeLogistics ? offer.logistics_price_ht_cents : 0;
  const vat = offer ? Math.round((goodsHt + logiHt) * offer.vat_rate / 100) : 0;

  const pay = async () => {
    if (!name || !email) { toast.error('Nom et email requis'); return; }
    setBusy(true);
    try {
      const res = await fetch(`${API}/oscop-checkout/session`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: product.id, quantity, include_logistics: includeLogistics,
          customer_email: email, customer_name: name, origin_url: window.location.origin,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Erreur');
      window.location.href = json.checkout_url;
    } catch (e) {
      toast.error(String(e.message || e));
      setBusy(false);
    }
  };

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md bg-[#2A1045] border-white/15 text-white" data-testid="oscop-buy-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-[#D9B35A]" />
            Achat direct O'SCOP
          </DialogTitle>
        </DialogHeader>
        {!offer ? <Loader2 className="w-5 h-5 animate-spin text-[#D9B35A]" /> : (
          <div className="space-y-3">
            <p className="text-sm text-white/80">{offer.name}</p>
            <p className="text-xs text-white/55">
              Votre contrat de vente est conclu avec la <b>SCIC SAS OBJECTIF SCOP OUTREMER</b>.
              O'SCOP émet la facture et reçoit le paiement.
            </p>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-white/60">Quantité</label>
                <Input value={qty} onChange={(e) => setQty(e.target.value)} data-testid="oscop-buy-qty"
                  className="bg-white/5 border-white/15 text-white" />
              </div>
              <div className="flex flex-col justify-end">
                <p className="text-xs text-white/60">Marchandises HT</p>
                <p className="font-semibold text-[#D9B35A]" data-testid="oscop-buy-goods-price">{eur(goodsHt)}</p>
              </div>
            </div>
            {offer.logistics_available && (
              <label className="flex items-center gap-2 p-2.5 rounded-lg bg-sky-500/10 border border-sky-400/25 cursor-pointer">
                <input type="checkbox" checked={includeLogistics} data-testid="oscop-buy-logistics-check"
                  onChange={(e) => setIncludeLogistics(e.target.checked)} />
                <span className="text-xs text-sky-100">
                  Ajouter la logistique intégrée LOGI'SCOP — {eur(offer.logistics_price_ht_cents)} HT
                </span>
              </label>
            )}
            <Input placeholder="Nom / raison sociale" value={name} onChange={(e) => setName(e.target.value)}
              data-testid="oscop-buy-name" className="bg-white/5 border-white/15 text-white" />
            <Input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              data-testid="oscop-buy-email" className="bg-white/5 border-white/15 text-white" />
            <div className="text-xs text-white/70 space-y-0.5 p-2 rounded bg-black/25">
              <div className="flex justify-between"><span>Marchandises HT</span><span>{eur(goodsHt)}</span></div>
              {includeLogistics && <div className="flex justify-between"><span>Logistique LOGI'SCOP HT</span><span>{eur(logiHt)}</span></div>}
              <div className="flex justify-between"><span>TVA ({offer.vat_rate}%)</span><span>{eur(vat)}</span></div>
              <div className="flex justify-between font-bold text-white"><span>Total TTC</span><span data-testid="oscop-buy-total">{eur(goodsHt + logiHt + vat)}</span></div>
            </div>
            <Button onClick={pay} disabled={busy} data-testid="oscop-buy-submit"
              className="w-full bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A] font-semibold">
              {busy && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              Payer à O'SCOP (Stripe)
            </Button>
            <p className="text-[10px] text-white/40">
              Paiement par carte ou moyen bancaire habilité via Stripe. Les CREDI'SCOP-INVEST ne sont jamais
              un moyen de paiement des produits. CGV O'SCOP applicables.
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
