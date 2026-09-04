import { useEffect, useState } from 'react';
import { Loader2, Ship, Anchor } from 'lucide-react';
import { toast } from 'sonner';
import { API } from '../services/http';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import Header from '../components/Header';
import Footer from '../components/Footer';
import { FreightToOperation } from '../components/freight/FreightToOperation';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;

export default function FreightCalculatorPage() {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ route_id: '', container_type: '20DV', quantity: '1', insurance: false, goods_value: '' });
  const [quote, setQuote] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API}/public/freight/routes`).then((r) => r.json()).then((d) => {
      setData(d);
      if (d.routes?.length) setForm((f) => ({ ...f, route_id: d.routes[0].id }));
    }).catch(() => {});
  }, []);

  const compute = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/public/freight/quote`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          route_id: form.route_id, container_type: form.container_type,
          quantity: parseFloat(String(form.quantity).replace(',', '.')) || 1,
          insurance: form.insurance,
          goods_value_ex_vat: parseFloat(String(form.goods_value).replace(',', '.')) || 0,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Erreur');
      setQuote(json);
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}>
      <Header />
      <main className="max-w-[880px] mx-auto px-5 py-12" data-testid="freight-calculator-page">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2 flex items-center gap-3">
          <Ship className="w-8 h-8 text-[#D9B35A]" /> Calculateur de fret maritime LOGI'SCOP
        </h1>
        <p className="text-white/60 text-sm mb-6 max-w-[70ch]">
          Estimez le coût du fret principal vers les Outre-mer pour sécuriser votre coût de revient
          et garantir la rentabilité de chaque opération. {data?.note}
        </p>
        {!data ? <Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" /> : (
          <div className="grid md:grid-cols-2 gap-5">
            <div className="glass-panel-soft rounded-[20px] p-5 space-y-3">
              <div>
                <label className="text-xs text-white/60">Route maritime</label>
                <select value={form.route_id} onChange={(e) => setForm({ ...form, route_id: e.target.value })}
                  data-testid="freight-route-select"
                  className="w-full bg-white/5 border border-white/15 rounded-md px-3 py-2 text-sm text-white">
                  {data.routes.map((r) => (
                    <option key={r.id} value={r.id} className="bg-[#2A1045]">
                      {r.origin} → {r.destination} (~{r.transit_days} j)
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-white/60">Type d'unité</label>
                <select value={form.container_type} onChange={(e) => setForm({ ...form, container_type: e.target.value })}
                  data-testid="freight-container-select"
                  className="w-full bg-white/5 border border-white/15 rounded-md px-3 py-2 text-sm text-white">
                  {Object.entries(data.containers).map(([v, l]) => <option key={v} value={v} className="bg-[#2A1045]">{l}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-white/60">{form.container_type === 'LCL' ? 'Volume (m³)' : 'Nombre de conteneurs'}</label>
                <Input value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                  data-testid="freight-quantity" className="bg-white/5 border-white/15 text-white" />
              </div>
              <label className="flex items-center gap-2 text-xs text-white/70 cursor-pointer">
                <input type="checkbox" checked={form.insurance} data-testid="freight-insurance-check"
                  onChange={(e) => setForm({ ...form, insurance: e.target.checked })} />
                Assurance transport (0,6 % de la valeur marchandises, min. 45 €)
              </label>
              {form.insurance && (
                <Input placeholder="Valeur marchandises HT (€)" value={form.goods_value} data-testid="freight-goods-value"
                  onChange={(e) => setForm({ ...form, goods_value: e.target.value })} className="bg-white/5 border-white/15 text-white" />
              )}
              <Button onClick={compute} disabled={busy} data-testid="freight-compute-btn"
                className="w-full bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A] font-semibold">
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Calculer le tarif'}
              </Button>
            </div>
            <div className="glass-panel-soft rounded-[20px] p-5">
              <p className="text-xs font-semibold text-white/70 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                <Anchor className="w-4 h-4 text-[#D9B35A]" /> Estimation
              </p>
              {!quote ? <p className="text-white/40 text-sm">Renseignez les paramètres puis calculez.</p> : (
                <div className="space-y-1.5 text-sm" data-testid="freight-quote-result">
                  <p className="text-white/85 font-semibold">{quote.route}</p>
                  <p className="text-white/55 text-xs">{quote.container} × {quote.quantity} · transit ≈ {quote.transit_days_estimate} jours</p>
                  <div className="pt-2 space-y-1 text-xs">
                    <div className="flex justify-between text-white/70"><span>Fret de base</span><span>{eur(quote.breakdown.base_freight)}</span></div>
                    <div className="flex justify-between text-white/70"><span>Surcharge BAF</span><span>{eur(quote.breakdown.baf_surcharge)}</span></div>
                    <div className="flex justify-between text-white/70"><span>THC / manutention</span><span>{eur(quote.breakdown.thc_handling)}</span></div>
                    {quote.breakdown.transport_insurance > 0 && (
                      <div className="flex justify-between text-white/70"><span>Assurance transport</span><span>{eur(quote.breakdown.transport_insurance)}</span></div>
                    )}
                    <div className="flex justify-between font-bold text-[#D9B35A] text-base pt-1 border-t border-white/10">
                      <span>Total HT</span><span data-testid="freight-total">{eur(quote.total_ex_vat)}</span>
                    </div>
                  </div>
                  <p className="text-white/40 text-[10px] pt-2">{quote.note}</p>
                  <Button
                    size="sm"
                    data-testid="freight-pdf-btn"
                    className="mt-2 w-full bg-white/10 hover:bg-white/20 text-white text-xs"
                    onClick={async () => {
                      try {
                        const res = await fetch(`${API}/public/freight/quote-pdf`, {
                          method: 'POST', headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            route_id: form.route_id, container_type: form.container_type,
                            quantity: parseFloat(String(form.quantity).replace(',', '.')) || 1,
                            insurance: form.insurance,
                            goods_value_ex_vat: parseFloat(String(form.goods_value).replace(',', '.')) || 0,
                          }),
                        });
                        if (!res.ok) throw new Error('PDF indisponible');
                        const blob = await res.blob();
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = (res.headers.get('Content-Disposition') || '').split('"')[1] || 'devis-fret.pdf';
                        a.click();
                        URL.revokeObjectURL(url);
                      } catch (e) { toast.error(String(e.message || e)); }
                    }}
                  >
                    Télécharger le devis PDF LOGI'SCOP
                  </Button>
                  <FreightToOperation quote={quote} />
                </div>
              )}
            </div>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
