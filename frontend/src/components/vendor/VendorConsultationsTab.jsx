import { useCallback, useEffect, useState } from 'react';
import { Gavel, Lock, TrendingDown, CheckCircle2, BarChart3, LineChart } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;
const panel = 'bg-white/[0.04] border border-white/[0.08] rounded-2xl';
const gold = { background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' };
const L_STYLE = { ROUGE: 'bg-red-500/15 text-red-400', ORANGE: 'bg-amber-500/15 text-amber-400', VERT: 'bg-emerald-500/15 text-emerald-400' };

const ConsultationCard = ({ c, onChanged }) => {
  const [status, setStatus] = useState(null);
  const [amount, setAmount] = useState('');
  const [report, setReport] = useState(null);
  const sealed = c.procedure === 'SCELLEE';

  const loadStatus = useCallback(() => {
    if (!c.registered) return;
    fetch(`${API}/api/consultations/${c.id}/my-status`, { credentials: 'include' })
      .then((r) => r.json()).then(setStatus).catch(() => {});
  }, [c.id, c.registered]);
  useEffect(() => { loadStatus(); }, [loadStatus]);

  const register = async () => {
    const ok = window.confirm(
      `Inscription à ${c.ref} — ${c.title}\n\nCoût d'accès : ${c.cpc_cost} CREDI'SCOP (débité une seule fois, ${c.max_rounds} tours d'offres inclus, aucune consommation par offre).\nProcédure : ${sealed ? 'offres scellées' : 'enchère inversée à rang anonyme'}.\nClôture ferme : ${String(c.closes_at).slice(0, 16).replace('T', ' ')} (heure serveur).\nAnnulation par l'organisateur = recrédit intégral.\n\nAccepter le règlement et confirmer ?`);
    if (!ok) return;
    const r = await fetch(`${API}/api/consultations/${c.id}/register`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accept_rules: true }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    toast.success(`Inscription confirmée — solde : ${d.balance} CREDI'SCOP`);
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

  const buyReport = async () => {
    if (!report && !window.confirm('Rapport d\'analyse détaillé : 10 CREDI\'SCOP (débit unique — gratuit si déjà acheté). Continuer ?')) return;
    const r = await fetch(`${API}/api/consultations/${c.id}/report`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setReport(d);
  };

  const roundsUsed = status?.my_bids?.filter((b) => b.status === 'VALIDE' || sealed).length || 0;
  const btn = 'px-2.5 py-1.5 rounded-lg text-[11px] font-bold inline-flex items-center gap-1 transition-all hover:brightness-110';
  return (
    <div className={`${panel} p-4 space-y-2`} data-testid={`vendor-cons-${c.id}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold text-[#E9CF8E]">{c.ref}</span>
        <span className="font-semibold text-white flex-1 min-w-[150px]">{c.title}</span>
        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${L_STYLE[c.legal_status] || 'bg-white/10 text-white/50'}`}>{c.legal_status}</span>
        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/60">{sealed ? 'OFFRES SCELLÉES' : 'ENCHÈRE INVERSÉE'}</span>
        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#D9B35A]/20 text-[#E9CF8E]">{c.status.replace(/_/g, ' ')}</span>
      </div>
      <p className="text-xs text-white/50">
        {(c.products || []).map((p) => p.label).join(', ')} · {(c.territories || []).join(', ')} · Accès {c.cpc_cost} CREDI'SCOP ·
        clôture {String(c.closes_at).slice(0, 16).replace('T', ' ')}
      </p>
      {!c.registered && ['INSCRIPTIONS_OUVERTES', 'EN_COURS'].includes(c.status) && (
        <button type="button" onClick={register} className={btn} style={gold} data-testid={`cons-register-${c.id}`}>
          S'inscrire ({c.cpc_cost} CREDI'SCOP)
        </button>
      )}
      {c.registered && c.status === 'EN_COURS' && (
        <div className="flex flex-wrap items-center gap-2">
          <input className="h-9 w-36 rounded-lg px-2.5 text-sm text-white bg-white/[0.05] border border-white/15" placeholder="Prix € HT"
            value={amount} onChange={(e) => setAmount(e.target.value)} data-testid={`cons-bid-input-${c.id}`} />
          <button type="button" onClick={bid} className={btn} style={gold} data-testid={`cons-bid-btn-${c.id}`}>
            {sealed ? <><Lock className="w-3.5 h-3.5" /> Déposer sous pli scellé</> : <><TrendingDown className="w-3.5 h-3.5" /> Enchérir (tour {Math.min(roundsUsed + 1, c.max_rounds)}/{c.max_rounds})</>}
          </button>
          {!sealed && status?.rank && (
            <span className="text-xs font-semibold text-white/60" data-testid={`cons-rank-${c.id}`}>
              Rang {status.rank}/{status.participants} · écart meilleure offre : {eur(status.gap_to_best_cents)}
            </span>
          )}
          {sealed && roundsUsed > 0 && <span className="text-xs text-white/40">Offre scellée déposée (remplaçable avant clôture)</span>}
        </div>
      )}
      {c.registered && c.status === 'ATTRIBUEE' && (
        <button type="button" onClick={askWinner} className={`${btn} bg-white/10 text-white/70 hover:text-white`} data-testid={`cons-winner-${c.id}`}>
          <CheckCircle2 className="w-3.5 h-3.5" /> Identité du candidat retenu
        </button>
      )}
      {c.registered && ['CLOTUREE', 'EN_EVALUATION', 'ATTRIBUEE', 'ARCHIVEE'].includes(c.status) && (
        <button type="button" onClick={buyReport} className={`${btn} bg-white/10 text-white/70 hover:text-white`} data-testid={`cons-report-${c.id}`}>
          <BarChart3 className="w-3.5 h-3.5" /> {report ? 'Actualiser le rapport' : "Rapport d'analyse (10 CREDI'SCOP)"}
        </button>
      )}
      {report && (
        <div className="mt-2 p-3 rounded-xl bg-[#D9B35A]/10 border border-[#D9B35A]/25 text-xs space-y-1 text-white/75" data-testid={`cons-report-data-${c.id}`}>
          <p className="font-bold text-[#E9CF8E]">Rapport d'analyse — {report.ref}</p>
          <p>Participants : <b className="text-white">{report.participants}</b> · Meilleure offre : <b className="text-white">{eur(report.best_offer_ht_cents)}</b> · Médiane : <b className="text-white">{eur(report.median_offer_ht_cents)}</b></p>
          <p>Ma dernière offre : <b className="text-white">{eur(report.my_last_offer_ht_cents)}</b>{report.my_gap_to_best_cents != null && <> · Écart à la meilleure : <b className="text-white">{eur(report.my_gap_to_best_cents)}</b></>}</p>
          {report.my_final_rank && <p>Mon classement final : <b className="text-white">#{report.my_final_rank}</b> (score {report.my_score})</p>}
          <p className="text-white/40">Pondérations : {Object.entries(report.criteria_weights || {}).map(([k, w]) => `${k} ${w}%`).join(' · ')}</p>
        </div>
      )}
    </div>
  );
};

const BenchmarkPanel = () => {
  const [category, setCategory] = useState('');
  const [data, setData] = useState(null);

  const buy = async () => {
    if (!category.trim()) return toast.error('Indiquez une catégorie');
    if (!data && !window.confirm(`Benchmark anonymisé « ${category} » : 15 CREDI'SCOP (débit unique par mois et par catégorie). Continuer ?`)) return;
    const r = await fetch(`${API}/api/consultations-benchmark/${encodeURIComponent(category.trim().toLowerCase())}`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Erreur');
    setData(d);
  };

  return (
    <div className={`${panel} p-4 space-y-2`} data-testid="benchmark-panel">
      <h3 className="text-sm font-semibold text-white flex items-center gap-2">
        <LineChart className="w-4 h-4 text-[#D9B35A]" /> Benchmark catégorie (anonymisé)
      </h3>
      <div className="flex flex-wrap items-center gap-2">
        <input className="h-9 flex-1 min-w-[180px] rounded-lg px-2.5 text-sm text-white bg-white/[0.05] border border-white/15"
          placeholder="Catégorie (ex : boissons)" value={category} onChange={(e) => setCategory(e.target.value)} data-testid="benchmark-input" />
        <button type="button" onClick={buy} data-testid="benchmark-btn"
          className="px-3 py-2 rounded-lg text-[11px] font-bold hover:brightness-110 transition-all" style={gold}>
          Débloquer (15 CREDI'SCOP)
        </button>
      </div>
      {data && (
        <div className="p-3 rounded-xl bg-[#D9B35A]/10 border border-[#D9B35A]/25 text-xs space-y-1 text-white/75" data-testid="benchmark-data">
          <p className="font-bold text-[#E9CF8E]">Benchmark « {data.category} » — {data.period}</p>
          <p>Consultations clôturées : <b className="text-white">{data.consultations}</b> · Offres analysées : <b className="text-white">{data.offers}</b> · Participants moyens : <b className="text-white">{data.avg_participants}</b></p>
          <p>Prix moyen : <b className="text-white">{eur(data.avg_offer_ht_cents)}</b> · Médiane : <b className="text-white">{eur(data.median_offer_ht_cents)}</b> · Min : <b className="text-white">{eur(data.min_offer_ht_cents)}</b> · Max : <b className="text-white">{eur(data.max_offer_ht_cents)}</b></p>
          <p className="text-white/40">Données agrégées et anonymisées — aucun secret commercial individuel n'est divulgué.</p>
        </div>
      )}
    </div>
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
        <div className={`${panel} py-10 text-center`}>
          <Gavel className="w-10 h-10 mx-auto text-white/20 mb-3" />
          <p className="text-white/50">Aucune consultation ouverte pour l'instant.</p>
        </div>
      )}
      {items.map((c) => <ConsultationCard key={c.id} c={c} onChanged={load} />)}
      <BenchmarkPanel />
      <p className="text-[11px] text-white/40">
        Les offres sont exprimées exclusivement en euros HT. Le nombre de CREDI'SCOP détenus n'intervient jamais dans le classement.
        L'identité des concurrents reste masquée pendant la procédure. {' '}
        <a href={`${API}/api/cpc/reglement.pdf`} target="_blank" rel="noreferrer" className="text-[#E9CF8E] hover:underline font-semibold" data-testid="consultations-reglement-link">
          Règlement des consultations et des crédits (PDF)
        </a>
      </p>
    </div>
  );
};
