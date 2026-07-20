import { useEffect, useState } from 'react';
import { Send, Loader2, Euro, RefreshCw, Save, ExternalLink, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Switch } from '../ui/switch';

const PUSH_STATUS = {
  PUSHED: { color: '#7BC94E', icon: CheckCircle2, label: 'Transmise' },
  ERROR: { color: '#F87171', icon: XCircle, label: 'Erreur' },
};

const inputCls = 'w-24 rounded-lg px-2 py-1.5 text-sm text-white bg-white/[0.06] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60';

const TarifRow = ({ tarif, onSave, onToggle }) => {
  const [prix, setPrix] = useState(tarif.prix_base);
  const [credits, setCredits] = useState(tarif.prix_credits);
  const [saving, setSaving] = useState(false);
  const dirty = Number(prix) !== tarif.prix_base || Number(credits) !== tarif.prix_credits;
  return (
    <div className="flex flex-wrap items-center gap-3 px-3 py-2.5 rounded-xl bg-white/[0.04] text-sm" data-testid={`demandes-tarif-${tarif.id}`}>
      <div className="min-w-[160px] flex-1">
        <p className="text-white/90 font-medium">{tarif.nom}</p>
        <p className="text-[11px] text-white/45">{tarif.code} · {tarif.type_demande} · {tarif.territoire}</p>
      </div>
      <label className="flex items-center gap-1.5 text-xs text-white/60">
        Prix € HT
        <input type="number" min="0" step="0.01" value={prix} onChange={(e) => setPrix(e.target.value)} className={inputCls} />
      </label>
      <label className="flex items-center gap-1.5 text-xs text-white/60">
        Crédits
        <input type="number" min="0" value={credits} onChange={(e) => setCredits(e.target.value)} className={inputCls} />
      </label>
      <Switch checked={!!tarif.is_active} onCheckedChange={(v) => onToggle(tarif, v)} title="Actif" />
      {dirty && (
        <button
          type="button" disabled={saving}
          onClick={async () => { setSaving(true); await onSave(tarif, { prix_base: Number(prix), prix_credits: Number(credits) }); setSaving(false); }}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold disabled:opacity-50"
          style={{ background: '#D4AF37', color: '#1F0A33' }}
          data-testid={`demandes-tarif-save-${tarif.id}`}
        >
          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />} Enregistrer
        </button>
      )}
    </div>
  );
};

export const DemandesAdminTab = () => {
  const [data, setData] = useState(null);
  const [pushes, setPushes] = useState([]);
  const [loading, setLoading] = useState(true);
  const opts = { headers: getAuthHeaders(), credentials: 'include' };

  const load = () => {
    fetch(`${API}/admin/demandes/remote-tarifs`, opts)
      .then((r) => (r.ok ? r.json() : r.json().then((d) => Promise.reject(new Error(d.detail)))))
      .then(setData)
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
    fetch(`${API}/admin/demandes/pushes`, opts).then((r) => r.json()).then((d) => setPushes(d.quotes || []));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, []);

  const saveTarif = async (tarif, payload) => {
    try {
      const r = await fetch(`${API}/admin/demandes/remote-tarifs/${tarif.id}`, {
        method: 'PUT', ...opts, headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...tarif, ...payload }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
      toast.success('Tarif mis à jour sur la plateforme O\'SCOP');
      load();
    } catch (e) { toast.error(e.message); }
  };

  const toggleTarif = async (tarif, active) => {
    try {
      const r = await fetch(`${API}/admin/demandes/remote-tarifs/${tarif.id}/toggle`, {
        method: 'PATCH', ...opts, headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: active }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || 'Erreur');
      toast.success(active ? 'Tarif activé' : 'Tarif désactivé');
      load();
    } catch (e) { toast.error(e.message); }
  };

  const retry = async (id) => {
    const r = await fetch(`${API}/admin/demandes/pushes/${id}/retry`, { method: 'POST', ...opts });
    const d = await r.json();
    if (d.oscop_status === 'PUSHED') toast.success('Demande transmise à Communityplace Demandes');
    else toast.error(d.oscop_error || 'Échec de la transmission');
    load();
  };

  const setQuoteStatus = async (id, status) => {
    const r = await fetch(`${API}/admin/quotes/${id}/status?new_status=${status}`, {
      method: 'PUT', ...opts, headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    });
    if (!r.ok) return toast.error('Mise à jour impossible');
    toast.success(status === 'processed' ? 'Demande marquée comme traitée' : 'Demande rouverte');
    load();
  };

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" /></div>;

  const achat = data?.tarif_achat || {};
  const tarifs = data?.tarifs?.tarifs_generaux || [];

  return (
    <div className="space-y-5" data-testid="demandes-admin-tab">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Send className="w-5 h-5 text-[#D9B35A]" /> Communityplace Demandes
          </h2>
          <p className="text-white/55 text-sm mt-1">
            Développez votre portefeuille clients — chaque demande de devis du site est transmise à la plateforme O'SCOP.
            Les coûts et conditions sont gérés ici.
          </p>
        </div>
        <button type="button" onClick={load} className="p-2 rounded-lg border border-white/15 text-white/60 hover:text-white" title="Rafraîchir">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="demandes-tarif-achat">
        {[
          { label: 'Prix par demande TTC', value: `${achat.prix_ttc ?? '—'} €` },
          { label: 'Prix HT', value: `${achat.prix_ht ?? '—'} €` },
          { label: 'Prix en crédits', value: achat.prix_credits ?? '—' },
          { label: 'TVA / FOGEDOM / Solidaire', value: `${achat.montant_tva ?? 0} / ${achat.montant_fogedom ?? 0} / ${achat.montant_contribution_solidaire ?? 0} €` },
        ].map((s) => (
          <div key={s.label} className="rounded-xl px-4 py-3 bg-white/[0.05] border border-white/10">
            <p className="text-lg font-bold text-[#E9CF8E] flex items-center gap-1.5"><Euro className="w-4 h-4 text-[#D9B35A]" />{s.value}</p>
            <p className="text-[10px] text-white/50 uppercase tracking-wide mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="glass-panel-soft rounded-[18px] p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-[#D9B35A]">Tarifs des demandes (plateforme O'SCOP)</h3>
          <a href="https://objectifscopoutremer.com/cooper/achats-demandes" target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-white/50 hover:text-white">
            <ExternalLink className="w-3 h-3" /> Voir la marketplace
          </a>
        </div>
        <div className="space-y-2" data-testid="demandes-tarifs-list">
          {tarifs.length === 0 && <p className="text-xs text-white/40">Aucun tarif configuré sur la plateforme.</p>}
          {tarifs.map((t) => <TarifRow key={t.id} tarif={t} onSave={saveTarif} onToggle={toggleTarif} />)}
        </div>
      </div>

      <div className="glass-panel-soft rounded-[18px] p-4" data-testid="demandes-pushes-log">
        <h3 className="text-sm font-semibold text-[#D9B35A] mb-3">Demandes de devis reçues</h3>
        {pushes.length === 0 ? (
          <p className="text-xs text-white/40">Aucune demande de devis reçue pour le moment.</p>
        ) : (
          <div className="space-y-1.5 max-h-96 overflow-y-auto">
            {pushes.map((q) => {
              const st = PUSH_STATUS[q.oscop_status] || { color: '#9CA3AF', icon: Clock, label: 'En attente' };
              const Icon = st.icon;
              const processed = q.status === 'processed';
              return (
                <div key={q.id} className="px-3 py-2 rounded-lg bg-white/[0.04] text-xs" data-testid={`quote-row-${q.id}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-white/85 font-medium min-w-[140px]">
                      {q.company}
                      {q.legal_status && <span className="ml-1.5 px-1.5 py-0.5 rounded bg-[#D9B35A]/15 text-[#E9CF8E] text-[10px]">{q.legal_status}</span>}
                    </span>
                    <span className="text-white/50 truncate">
                      {(q.first_name || q.last_name) ? `${q.first_name || ''} ${q.last_name || ''}`.trim() : q.contact_name} · {q.email}
                      {q.phone && ` · ${q.phone_country || ''} ${q.phone}`}
                    </span>
                    {q.lang && <span className="text-white/40 uppercase">{q.lang}</span>}
                    <span className="inline-flex items-center gap-1 font-semibold px-1.5 py-0.5 rounded-full"
                      style={{ color: st.color, background: `${st.color}1c` }} title={q.oscop_error || ''}>
                      <Icon size={10} /> {st.label}
                    </span>
                    <button type="button" onClick={() => setQuoteStatus(q.id, processed ? 'pending' : 'processed')}
                      data-testid={`quote-status-${q.id}`}
                      className="px-2 py-1 rounded-md text-[10px] font-bold"
                      style={processed
                        ? { background: 'rgba(123,201,78,0.16)', color: '#7BC94E', border: '1px solid rgba(123,201,78,0.45)' }
                        : { background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.7)', border: '1px solid rgba(255,255,255,0.2)' }}>
                      {processed ? 'Traitée ✓' : 'Marquer traitée'}
                    </button>
                    {q.oscop_status !== 'PUSHED' && (
                      <button type="button" onClick={() => retry(q.id)} data-testid={`demandes-retry-${q.id}`}
                        className="px-2 py-1 rounded-md text-[10px] font-bold"
                        style={{ background: 'rgba(217,179,90,0.16)', color: '#E9CF8E', border: '1px solid rgba(217,179,90,0.45)' }}>
                        Renvoyer
                      </button>
                    )}
                  </div>
                  {q.message && <p className="text-white/40 mt-1 truncate">{q.message}</p>}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
