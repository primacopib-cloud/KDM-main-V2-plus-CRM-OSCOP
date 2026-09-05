import { useState } from 'react';
import { Ship, Plane, Scale, Loader2, FileDown } from 'lucide-react';
import { toast } from 'sonner';
import { API } from '../../services/http';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { FreightToOrder } from './FreightToOrder';

const eur = (v) => `${Number(v || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} €`;
const TERRITORIES = ['Guadeloupe', 'Martinique', 'Guyane', 'La Réunion', 'Mayotte'];

export const ModeComparePanel = () => {
  const [form, setForm] = useState({ territory: 'Guadeloupe', weight_kg: '300', volume_m3: '2' });
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [chosen, setChosen] = useState('sea');

  const body = () => ({
    territory: form.territory,
    weight_kg: parseFloat(String(form.weight_kg).replace(',', '.')) || 1,
    volume_m3: parseFloat(String(form.volume_m3).replace(',', '.')) || 1,
  });

  const downloadPdf = async () => {
    setPdfBusy(true);
    try {
      const res = await fetch(`${API}/public/freight/compare-modes-pdf`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body()),
      });
      if (!res.ok) throw new Error('Génération impossible');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `comparatif-mer-air-${form.territory.toLowerCase()}.pdf`; a.click();
      URL.revokeObjectURL(url);
      toast.success('Comparatif PDF téléchargé ✓');
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setPdfBusy(false);
    }
  };

  const compare = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/public/freight/compare-modes`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body()),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Erreur');
      setResult(json);
    } catch (e) {
      toast.error(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const card = (icon, title, d, highlight) => (
    <div className={`rounded-[16px] p-4 border ${highlight ? 'border-[#D9B35A]/50 bg-[#D9B35A]/[0.06]' : 'border-white/10 bg-white/[0.03]'}`}>
      <h4 className="text-sm font-bold text-white flex items-center gap-2 mb-1.5">{icon} {title}</h4>
      <p className="text-white/80 text-xs m-0">{d.route}</p>
      <p className="text-white/55 text-[11px] m-0">Base : {d.basis}</p>
      <p className="text-[#E9CF8E] text-xl font-bold m-0 mt-1.5">{eur(d.total_ex_vat)} <span className="text-xs font-normal">HT</span></p>
      <p className="text-white/60 text-xs m-0">Délai ≈ {d.transit_days} jour{d.transit_days > 1 ? 's' : ''}</p>
    </div>
  );

  return (
    <div className="grid md:grid-cols-[0.9fr_1.1fr] gap-5" data-testid="mode-compare-panel">
      <div className="glass-panel-soft rounded-[20px] p-5 space-y-3">
        <div>
          <label className="text-xs text-white/60">Territoire de destination</label>
          <select value={form.territory} onChange={(e) => setForm({ ...form, territory: e.target.value })}
            data-testid="compare-territory"
            className="w-full bg-white/5 border border-white/15 rounded-md px-3 py-2 text-sm text-white">
            {TERRITORIES.map((t) => <option key={t} value={t} className="bg-[#2A1045]">{t}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-white/60">Poids (kg)</label>
          <Input value={form.weight_kg} onChange={(e) => setForm({ ...form, weight_kg: e.target.value })}
            data-testid="compare-weight" className="bg-white/5 border-white/15 text-white" />
        </div>
        <div>
          <label className="text-xs text-white/60">Volume (m³)</label>
          <Input value={form.volume_m3} onChange={(e) => setForm({ ...form, volume_m3: e.target.value })}
            data-testid="compare-volume" className="bg-white/5 border-white/15 text-white" />
        </div>
        <Button onClick={compare} disabled={busy} data-testid="compare-modes-btn"
          className="on-gold w-full bg-[#D9B35A] hover:bg-[#F2D07A] font-semibold">
          {busy ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Scale className="w-4 h-4 mr-1" />} Comparer mer / air
        </Button>
      </div>
      <div className="glass-panel-soft rounded-[20px] p-5">
        {!result ? <p className="text-white/40 text-sm">Renseignez l'envoi puis comparez.</p> : (
          <div className="space-y-3" data-testid="compare-modes-result">
            <div className="grid sm:grid-cols-2 gap-3">
              {card(<Ship className="w-4 h-4 text-[#5AA7D9]" />, 'Maritime (le plus économique)', result.sea, result.savings_sea_ex_vat > 0)}
              {card(<Plane className="w-4 h-4 text-[#D9B35A]" />, 'Aérien (le plus rapide)', result.air, result.savings_sea_ex_vat <= 0)}
            </div>
            <p className="text-xs text-white/70 m-0" data-testid="compare-verdict">
              {result.savings_sea_ex_vat > 0
                ? <>La mer économise <b className="text-[#A9D96C]">{eur(result.savings_sea_ex_vat)}</b>, l'avion gagne <b className="text-[#E9CF8E]">{result.days_saved_air} jours</b> — arbitrez selon l'urgence.</>
                : <>L'aérien est ici moins cher ET plus rapide de {result.days_saved_air} jours.</>}
            </p>
            <Button onClick={downloadPdf} disabled={pdfBusy} variant="outline" data-testid="compare-pdf-btn"
              className="border-[#D9B35A]/40 text-[#E9CF8E] hover:bg-[#D9B35A]/10">
              {pdfBusy ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <FileDown className="w-4 h-4 mr-1" />}
              Télécharger le comparatif PDF LOGI'SCOP
            </Button>
            {/* Intégrer l'option choisie à une commande */}
            <div className="pt-2 border-t border-white/10">
              <p className="text-[11px] font-semibold text-white/60 uppercase mb-2">Option à intégrer à la commande</p>
              <div className="flex gap-2 mb-1">
                {[['sea', 'Option maritime'], ['air', 'Option aérienne']].map(([v, l]) => (
                  <button key={v} type="button" onClick={() => setChosen(v)} data-testid={`choose-${v}`}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                      chosen === v ? 'on-gold bg-[#D9B35A]' : 'bg-white/[0.05] text-white/60 hover:text-white border border-white/10'}`}>
                    {l}
                  </button>
                ))}
              </div>
              <FreightToOrder key={chosen} quote={{
                route: result[chosen].route,
                container: `${chosen === 'sea' ? 'Maritime' : 'Aérien'} — ${result[chosen].basis}`,
                quantity: 1,
                total_ex_vat: result[chosen].total_ex_vat,
                transit_days_estimate: result[chosen].transit_days,
              }} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
