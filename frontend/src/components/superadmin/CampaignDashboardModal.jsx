import { useEffect, useState } from 'react';
import { BarChart3, Megaphone, X } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';

const S_STYLE = {
  BROUILLON: 'bg-white/10 text-white/60', EN_VALIDATION: 'bg-[#60A5FA]/15 text-[#60A5FA]',
  VALIDEE: 'bg-[#60A5FA]/15 text-[#60A5FA]', PUBLIEE: 'bg-[#7BC94E]/15 text-[#7BC94E]',
  INSCRIPTIONS_OUVERTES: 'bg-[#7BC94E]/15 text-[#7BC94E]', EN_COURS: 'bg-[#D9B35A]/20 text-[#E9CF8E]',
  CLOTUREE: 'bg-white/10 text-white/60', EN_EVALUATION: 'bg-[#60A5FA]/15 text-[#60A5FA]',
  ATTRIBUEE: 'bg-[#7BC94E]/15 text-[#7BC94E]', SANS_SUITE: 'bg-white/10 text-white/40',
  ANNULEE: 'bg-red-500/15 text-red-400', ARCHIVEE: 'bg-white/10 text-white/40',
};

const Kpi = ({ label, value, testid }) => (
  <div className="flex-1 min-w-[110px] p-3 rounded-xl bg-white/[0.04] border border-white/[0.08] text-center" data-testid={testid}>
    <p className="text-2xl font-bold text-[#E9CF8E]">{value}</p>
    <p className="text-[10px] text-white/50 uppercase font-semibold">{label}</p>
  </div>
);

export const CampaignDashboardModal = ({ campaign, onClose }) => {
  const [data, setData] = useState(null);
  const [reminding, setReminding] = useState(false);

  useEffect(() => {
    fetch(`${API}/admin/campaigns/${campaign.id}/dashboard`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => r.json())
      .then((d) => (d.detail ? toast.error(d.detail) : setData(d)))
      .catch(() => toast.error('Chargement impossible'));
  }, [campaign.id]);

  const ACTIVE = ['PUBLIEE', 'INSCRIPTIONS_OUVERTES', 'EN_COURS'];
  const lotsNoOffer = (data?.lots || []).filter((l) => ACTIVE.includes(l.status) && l.valid_bids === 0);

  const remindVendors = async () => {
    if (!window.confirm(`Relancer par email les vendeurs des catégories des ${lotsNoOffer.length} lot(s) sans offre ?`)) return;
    setReminding(true);
    try {
      const r = await fetch(`${API}/admin/campaigns/${campaign.id}/remind-vendors`, {
        method: 'POST', headers: getAuthHeaders(), credentials: 'include',
      });
      const d = await r.json();
      if (!r.ok) return toast.error(d.detail || 'Erreur');
      toast.success(`${d.sent} vendeur(s) relancé(s) — lots : ${(d.lots || []).join(', ')}${d.targeted_by_category ? ' (ciblage par catégorie)' : ''}`);
    } finally {
      setReminding(false);
    }
  };

  const t = data?.totals;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(15,5,25,0.75)' }} data-testid="campaign-dashboard-modal">
      <div className="w-full max-w-2xl rounded-[18px] p-5 max-h-[90vh] overflow-y-auto" style={{ background: '#2A1045', border: '1px solid rgba(217,179,90,0.3)' }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-[#D9B35A]" /> Tableau de bord — {campaign.name}
          </h3>
          <button type="button" onClick={onClose} className="text-white/50 hover:text-white" data-testid="campaign-dashboard-close">
            <X className="w-4 h-4" />
          </button>
        </div>
        {!data && <p className="text-xs text-white/45">Chargement…</p>}
        {data && (
          <>
            <div className="flex flex-wrap gap-2 mb-4">
              <Kpi label="Lots" value={t.lots} testid="camp-kpi-lots" />
              <Kpi label="Inscriptions" value={t.inscriptions} testid="camp-kpi-entries" />
              <Kpi label="Offres valides" value={t.offres_valides} testid="camp-kpi-bids" />
              <Kpi label="Lots attribués" value={t.attribues} testid="camp-kpi-awarded" />
            </div>
            {t.lots > 0 && (
              <div className="mb-4">
                <div className="flex justify-between text-[10px] text-white/50 mb-1">
                  <span>Avancement des attributions</span>
                  <span>{Math.round((t.attribues / t.lots) * 100)} %</span>
                </div>
                <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${(t.attribues / t.lots) * 100}%`, background: 'linear-gradient(90deg, #D9B35A, #b8933e)' }} />
                </div>
              </div>
            )}
            {lotsNoOffer.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 mb-4 p-2.5 rounded-xl bg-red-500/10 border border-red-500/20" data-testid="campaign-no-offer-warning">
                <p className="flex-1 min-w-[200px] text-[11px] text-red-300 font-semibold">
                  {lotsNoOffer.length} lot(s) actif(s) sans aucune offre : {lotsNoOffer.map((l) => l.ref).join(', ')}
                </p>
                <button type="button" onClick={remindVendors} disabled={reminding} data-testid="campaign-remind-vendors-btn"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10.5px] font-bold hover:brightness-110 transition-all disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #D9B35A, #b8933e)', color: '#1F0A33' }}>
                  <Megaphone className="w-3.5 h-3.5" /> {reminding ? 'Envoi…' : 'Relancer les vendeurs'}
                </button>
              </div>
            )}
            <div className="space-y-1.5">
              {!data.lots.length && <p className="text-xs text-white/45">Aucun lot rattaché à cette campagne.</p>}
              {data.lots.map((l) => (
                <div key={l.id} className="flex flex-wrap items-center gap-2 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs" data-testid={`camp-lot-${l.id}`}>
                  <span className="font-bold text-[#E9CF8E]">{l.ref}</span>
                  <span className="flex-1 min-w-[140px] text-white/85 font-semibold">{l.title}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${S_STYLE[l.status] || 'bg-white/10 text-white/50'}`}>{l.status.replace(/_/g, ' ')}</span>
                  <span className="text-white/50">{l.entries} inscrit(s)</span>
                  <span className="text-white/50">{l.valid_bids} offre(s)</span>
                  {l.awarded && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#7BC94E]/15 text-[#7BC94E]">ATTRIBUÉ</span>}
                </div>
              ))}
            </div>
            {(data.campaign?.vendor_reminders || []).length > 0 && (
              <div className="mt-4" data-testid="campaign-reminders-history">
                <p className="text-[10px] font-bold text-white/50 uppercase mb-1.5">Relevé des relances vendeurs</p>
                <div className="space-y-1">
                  {data.campaign.vendor_reminders.slice().reverse().map((r, i) => (
                    <div key={i} className="flex flex-wrap items-center gap-2 text-[11px] p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]" data-testid={`campaign-reminder-${i}`}>
                      <span className="text-white/70">{String(r.at).slice(0, 16).replace('T', ' à ')}</span>
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#D9B35A]/20 text-[#E9CF8E]">{r.sent} vendeur(s) relancé(s)</span>
                      <span className="text-white/45 flex-1">Lots : {(r.lots || []).join(', ')}</span>
                      {r.by && <span className="text-white/35">par {r.by}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
