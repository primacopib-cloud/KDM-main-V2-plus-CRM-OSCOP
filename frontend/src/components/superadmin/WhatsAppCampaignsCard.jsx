import { useEffect, useState } from 'react';
import { MessageCircle, RefreshCw } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const ST = {
  sent: 'text-emerald-300 bg-emerald-500/15 border-emerald-400/40',
  scheduled: 'text-amber-300 bg-amber-500/15 border-amber-400/40',
  draft: 'text-white/50 bg-white/[0.06] border-white/20',
};

export const WhatsAppCampaignsCard = () => {
  const [items, setItems] = useState([]);
  const [configured, setConfigured] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = () => {
    setBusy(true);
    fetch(`${API}/oracle-admin/whatsapp-campaigns`, { credentials: 'include', headers: getAuthHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { setItems(d?.campaigns || []); setConfigured(d?.configured !== false); })
      .catch(() => {})
      .finally(() => setBusy(false));
  };
  useEffect(load, []);

  return (
    <div className="rounded-2xl border border-[#D9B35A]/25 bg-white/[0.02] p-4 mt-4" data-testid="whatsapp-campaigns-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-[#E9CF8E] flex items-center gap-2">
          <MessageCircle size={15} /> Campagnes WhatsApp — livraison et lecture
        </h3>
        <button type="button" onClick={load} data-testid="whatsapp-campaigns-refresh"
          className="p-1.5 rounded-lg text-white/40 hover:text-[#E9CF8E] transition-colors">
          <RefreshCw size={13} className={busy ? 'animate-spin' : ''} />
        </button>
      </div>
      {!configured ? (
        <p className="text-[11px] text-white/40">WhatsApp (Brevo) non configuré.</p>
      ) : items.length === 0 ? (
        <p className="text-[11px] text-white/40" data-testid="whatsapp-campaigns-empty">
          Aucune campagne WhatsApp pour le moment — la campagne test partira automatiquement dès l'approbation Meta des modèles.
        </p>
      ) : (
        <div className="space-y-1.5 max-h-72 overflow-y-auto">
          {items.map((c) => (
            <div key={c.id} className="rounded-lg border border-white/[0.07] bg-white/[0.02] px-3 py-2"
              data-testid={`whatsapp-campaign-row-${c.id}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border ${ST[(c.status || '').toLowerCase()] || 'text-white/60 border-white/20'}`}>
                  {c.status || '—'}
                </span>
                <span className="text-[11px] font-semibold text-white/80">{c.name}</span>
                <span className="ml-auto text-[9.5px] text-white/35">
                  {c.scheduled_at ? new Date(c.scheduled_at).toLocaleString('fr-FR') : ''}
                </span>
              </div>
              <div className="flex items-center gap-4 mt-1 text-[10.5px] text-white/60">
                <span>Envoyés : <b className="text-white/85">{c.sent}</b></span>
                <span>Livrés : <b className="text-emerald-300">{c.delivered}</b> ({c.delivery_rate} %)</span>
                <span>Lus : <b className="text-[#E9CF8E]">{c.read}</b> ({c.read_rate} %)</span>
                {c.errors > 0 && <span className="text-red-300">Erreurs : {c.errors}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
