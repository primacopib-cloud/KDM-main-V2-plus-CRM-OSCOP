import { useCallback, useEffect, useState } from 'react';
import { Gavel, Lock, TrendingDown, CheckCircle2, BarChart3 } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;
const L_STYLE = { ROUGE: 'bg-red-100 text-red-700', ORANGE: 'bg-amber-100 text-amber-700', VERT: 'bg-emerald-100 text-emerald-700' };

const ConsultationCard = ({ c, onChanged }) => {
  const [status, setStatus] = useState(null);
  const [amount, setAmount] = useState('');
  const sealed = c.procedure === 'SCELLEE';

  const loadStatus = useCallback(() => {
    if (!c.registered) return;
    fetch(`${API}/api/consultations/${c.id}/my-status`, { credentials: 'include' })
      .then((r) => r.json()).then(setStatus).catch(() => {});
  }, [c.id, c.registered]);
  useEffect(() => { loadStatus(); }, [loadStatus]);

  const register = async () => {
    const ok = window.confirm(
      `Inscription à ${c.ref} — ${c.title}\n\nCoût d'accès : ${c.cpc_cost} CPC (débité une seule fois, ${c.max_rounds} tours d'offres inclus, aucune consommation par offre).\nProcédure : ${sealed ? 'offres scellées' : 'enchère inversée à rang anonyme'}.\nClôture ferme : ${String(c.closes_at).slice(0, 16).replace('T', ' ')} (heure serveur).\nAnnulation par l'organisateur = recrédit intégral.\n\nAccepter le règlement et confirmer ?`);
    if (!ok) return;
    const r = await fetch(`${API}/api/consultations/${c.id}/register`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accept_rules: true }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Inscription confirmée — solde : ${d.balance} CPC`);
    onChanged();
  };

  const bid = async () => {
    const cents = Math.round(parseFloat(String(amount).replace(',', '.')) * 100);
    if (!cents || cents <= 0) return toast.error('Prix en euros HT requis');
    const r = await fetch(`${API}/api/consultations/${c.id}/bid`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount_ht_cents: cents }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(sealed ? 'Offre scellée déposée (chiffrée jusqu\'à la clôture)' : `Offre enregistrée — tour ${d.round}`);
    setAmount('');
    loadStatus();
  };

  const askWinner = async () => {
    const r = await fetch(`${API}/api/consultations/${c.id}/winner-identity`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.info(`Candidat retenu : ${d.winner}`);
  };

  const [report, setReport] = useState(null);
  const buyReport = async () => {
    if (!report && !window.confirm('Rapport d\'analyse détaillé : 10 CPC (débit unique — gratuit si déjà acheté). Continuer ?')) return;
    const r = await fetch(`${API}/api/consultations/${c.id}/report`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setReport(d);
  };

  const roundsUsed = status?.my_bids?.filter((b) => b.status === 'VALIDE' || sealed).length || 0;
  return (
    <Card data-testid={`vendor-cons-${c.id}`}>
      <CardContent className="p-4 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-purple-600">{c.ref}</span>
          <span className="font-semibold text-gray-900 flex-1 min-w-[150px]">{c.title}</span>
          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${L_STYLE[c.legal_status] || 'bg-gray-100 text-gray-500'}`}>{c.legal_status}</span>
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-gray-100 text-gray-600">{sealed ? 'OFFRES SCELLÉES' : 'ENCHÈRE INVERSÉE'}</span>
          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-purple-100 text-purple-700">{c.status.replace(/_/g, ' ')}</span>
        </div>
        <p className="text-xs text-gray-500">
          {(c.products || []).map((p) => p.label).join(', ')} · {(c.territories || []).join(', ')} · Accès {c.cpc_cost} CPC ·
          clôture {String(c.closes_at).slice(0, 16).replace('T', ' ')}
        </p>
        {!c.registered && ['INSCRIPTIONS_OUVERTES', 'EN_COURS'].includes(c.status) && (
          <Button size="sm" onClick={register} className="bg-purple-600 hover:bg-purple-700" data-testid={`cons-register-${c.id}`}>
            S'inscrire ({c.cpc_cost} CPC)
          </Button>
        )}
        {c.registered && c.status === 'EN_COURS' && (
          <div className="flex flex-wrap items-center gap-2">
            <input className="h-9 w-36 rounded-lg border border-gray-200 px-2.5 text-sm" placeholder="Prix € HT"
              value={amount} onChange={(e) => setAmount(e.target.value)} data-testid={`cons-bid-input-${c.id}`} />
            <Button size="sm" onClick={bid} data-testid={`cons-bid-btn-${c.id}`}>
              {sealed ? <><Lock className="w-3.5 h-3.5 mr-1" /> Déposer sous pli scellé</> : <><TrendingDown className="w-3.5 h-3.5 mr-1" /> Enchérir (tour {Math.min(roundsUsed + 1, c.max_rounds)}/{c.max_rounds})</>}
            </Button>
            {!sealed && status?.rank && (
              <span className="text-xs font-semibold text-gray-600" data-testid={`cons-rank-${c.id}`}>
                Rang {status.rank}/{status.participants} · écart meilleure offre : {eur(status.gap_to_best_cents)}
              </span>
            )}
            {sealed && roundsUsed > 0 && <span className="text-xs text-gray-400">Offre scellée déposée (remplaçable avant clôture)</span>}
          </div>
        )}
        {c.registered && c.status === 'ATTRIBUEE' && (
          <Button variant="outline" size="sm" onClick={askWinner} data-testid={`cons-winner-${c.id}`}>
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Identité du candidat retenu
          </Button>
        )}
        {c.registered && ['CLOTUREE', 'EN_EVALUATION', 'ATTRIBUEE', 'ARCHIVEE'].includes(c.status) && (
          <Button variant="outline" size="sm" onClick={buyReport} data-testid={`cons-report-${c.id}`}>
            <BarChart3 className="w-3.5 h-3.5 mr-1" /> {report ? 'Actualiser le rapport' : "Rapport d'analyse (10 CPC)"}
          </Button>
        )}
        {report && (
          <div className="mt-2 p-3 rounded-lg bg-purple-50 border border-purple-100 text-xs space-y-1" data-testid={`cons-report-data-${c.id}`}>
            <p className="font-bold text-purple-700">Rapport d'analyse — {report.ref}</p>
            <p>Participants : <b>{report.participants}</b> · Meilleure offre : <b>{eur(report.best_offer_ht_cents)}</b> · Médiane : <b>{eur(report.median_offer_ht_cents)}</b></p>
            <p>Ma dernière offre : <b>{eur(report.my_last_offer_ht_cents)}</b>{report.my_gap_to_best_cents != null && <> · Écart à la meilleure : <b>{eur(report.my_gap_to_best_cents)}</b></>}</p>
            {report.my_final_rank && <p>Mon classement final : <b>#{report.my_final_rank}</b> (score {report.my_score})</p>}
            <p className="text-gray-400">Pondérations : {Object.entries(report.criteria_weights || {}).map(([k, w]) => `${k} ${w}%`).join(' · ')}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export const VendorConsultationsTab = () => {
  const [items, setItems] = useState([]);
  const load = useCallback(() => {
    fetch(`${API}/api/consultations`, { credentials: 'include' })
      .then((r) => r.json()).then((d) => setItems(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-3" data-testid="vendor-consultations-tab">
      {!items.length && (
        <Card><CardContent className="py-10 text-center">
          <Gavel className="w-10 h-10 mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">Aucune consultation ouverte pour l'instant.</p>
        </CardContent></Card>
      )}
      {items.map((c) => <ConsultationCard key={c.id} c={c} onChanged={load} />)}
      <p className="text-[11px] text-gray-400">
        Les offres sont exprimées exclusivement en euros HT. Le nombre de CPC détenus n'intervient jamais dans le classement.
        L'identité des concurrents reste masquée pendant la procédure. {' '}
        <a href={`${API}/api/cpc/reglement.pdf`} target="_blank" rel="noreferrer" className="text-purple-600 hover:underline font-semibold" data-testid="consultations-reglement-link">
          Règlement des consultations et des CPC (PDF)
        </a>
      </p>
    </div>
  );
};
