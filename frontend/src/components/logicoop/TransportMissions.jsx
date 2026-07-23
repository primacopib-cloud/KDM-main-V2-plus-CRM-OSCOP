import { useCallback, useEffect, useRef, useState } from 'react';
import { Truck, PackageCheck, Camera, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const eur = (c) => `${((c || 0) / 100).toFixed(2).replace('.', ',')} €`;

const MediaUpload = ({ m, onDone }) => {
  const fileRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const stage = m.execution?.status === 'LIVREE' || m.status !== 'ACCEPTE' ? 'LIVRAISON'
    : m.execution?.status === 'PRISE_EN_CHARGE' ? 'TRANSIT' : 'PRISE_EN_CHARGE';

  const pick = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 9 * 1024 * 1024) { toast.error('Fichier trop volumineux (9 Mo max)'); return; }
    setBusy(true);
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const r = await fetch(`${API}/logicoop/transport-missions/${m.ot_id}/media`, {
          method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage, name: f.name, mime: f.type || 'application/octet-stream',
            content_b64: String(reader.result).split(',')[1] }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Envoi impossible');
        toast.success(`« ${f.name} » transmis (${stage.replace('_', ' ').toLowerCase()}) — archivage avec le bon de livraison`);
        onDone();
      } catch (err) { toast.error(err.message); }
      setBusy(false);
    };
    reader.readAsDataURL(f);
    e.target.value = '';
  };

  return (
    <>
      <input ref={fileRef} type="file" className="hidden" accept="image/*,video/*" onChange={pick}
        data-testid={`media-input-${m.ot_id}`} />
      <button type="button" disabled={busy} onClick={() => fileRef.current?.click()}
        data-testid={`media-upload-${m.ot_id}`} title={`Photo/vidéo cargaison — étape : ${stage}`}
        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold bg-[#60A5FA]/15 border border-[#60A5FA]/35 text-[#93C5FD] hover:bg-[#60A5FA]/25 disabled:opacity-50">
        {busy ? <Loader2 size={11} className="animate-spin" /> : <Camera size={11} />} Photo/vidéo
      </button>
    </>
  );
};

const STATUS = {
  ACCEPTE: ['À EXÉCUTER', 'bg-[#D9B35A]/20 text-[#E9CF8E]'],
  LIVRE_CONFORME: ['✓ LIVRÉ CONFORME', 'bg-emerald-500/15 text-emerald-400'],
  LIVRE_AVEC_RESERVES: ['LIVRÉ AVEC RÉSERVES', 'bg-amber-500/15 text-amber-400'],
  PARTIEL: ['PARTIEL', 'bg-fuchsia-500/15 text-fuchsia-300'],
};

export const TransportMissions = () => {
  const [items, setItems] = useState(null);
  const [earnings, setEarnings] = useState(null);

  const load = useCallback(() => {
    fetch(`${API}/logicoop/transport-missions`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => { setItems(d.items || []); setEarnings(d.earnings || null); })
      .catch(() => setItems([]));
  }, []);
  useEffect(() => { load(); }, [load]);

  const setStatus = async (m, status) => {
    try {
      const r = await fetch(`${API}/logicoop/transport-missions/${m.ot_id}/status`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Erreur');
      toast.success(status === 'PRISE_EN_CHARGE'
        ? `OT ${m.ref} pris en charge — l'acheteur est informé`
        : `OT ${m.ref} livré — l'acheteur peut clôturer l'ePOD`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  if (!items) return null;

  return (
    <div className="glass-panel-soft rounded-[18px] p-5 mb-4" data-testid="logicoop-transport-missions">
      <h2 className="font-display text-lg text-white flex items-center gap-2 mb-1">
        <Truck className="w-4 h-4 text-[#D9B35A]" /> Missions Transport LOGI'SCOP ({items.length})
      </h2>
      <p className="text-xs text-white/45 mb-3">
        Ordres de Transport Mode D acceptés par LOGI'SCOP dans vos zones (enlèvement EXW / livraison CIF).
      </p>
      {earnings && earnings.base_ht_cents > 0 && (
        <p className="text-xs mb-3 px-3 py-2 rounded-xl bg-emerald-500/[0.08] border border-emerald-500/25 text-emerald-300"
          data-testid="operator-earnings-line">
          Rémunération sur vos OT livrés : <b>{eur(earnings.share_cents)}</b> ({earnings.rate_percent} % de {eur(earnings.base_ht_cents)} HT transporté)
        </p>
      )}
      <div className="space-y-1.5">
        {items.map((m) => {
          const [label, cls] = STATUS[m.status] || [m.status, 'bg-white/10 text-white/60'];
          const exec = m.execution?.status;
          return (
            <div key={m.ot_id} className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs"
              data-testid={`transport-mission-${m.ot_id}`}>
              <div className="flex flex-wrap items-center gap-2">
                {m.missions.map((t) => (
                  <span key={t} className={`px-2 py-0.5 rounded-lg text-[9px] font-bold ${t === 'ENLEVEMENT' ? 'bg-[#D9B35A]/20 text-[#E9CF8E]' : 'bg-[#60A5FA]/20 text-[#60A5FA]'}`}>
                    {t === 'ENLEVEMENT' ? 'ENLÈVEMENT' : 'LIVRAISON'}
                  </span>
                ))}
                <span className="font-bold text-white">{m.ref}</span>
                <span className="text-white/50 flex-1 min-w-[120px]">{m.company_name}</span>
                <span className={`px-2 py-0.5 rounded-lg text-[9px] font-bold ${cls}`}>{label}</span>
                {m.price_ht_cents ? <span className="font-bold text-[#E9CF8E]">{eur(m.price_ht_cents)} HT</span> : null}
                {m.status === 'ACCEPTE' && <MediaUpload m={m} onDone={load} />}
                {m.status === 'ACCEPTE' && (
                  exec === 'LIVREE' ? (
                    <span className="px-2 py-0.5 rounded-lg text-[9px] font-bold bg-emerald-500/15 text-emerald-400"
                      data-testid={`mission-exec-${m.ot_id}`}>✓ LIVRÉ — ePOD acheteur en attente</span>
                  ) : exec === 'PRISE_EN_CHARGE' ? (
                    <>
                      <span className="px-2 py-0.5 rounded-lg text-[9px] font-bold bg-[#60A5FA]/20 text-[#60A5FA]"
                        data-testid={`mission-exec-${m.ot_id}`}>EN ACHEMINEMENT</span>
                      <button type="button" onClick={() => setStatus(m, 'LIVREE')} data-testid={`mission-ot-deliver-${m.ot_id}`}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold bg-emerald-500/15 border border-emerald-500/35 text-emerald-400 hover:bg-emerald-500/25">
                        <PackageCheck size={11} /> Marquer livré
                      </button>
                    </>
                  ) : (
                    <button type="button" onClick={() => setStatus(m, 'PRISE_EN_CHARGE')} data-testid={`mission-ot-take-${m.ot_id}`}
                      className="px-2 py-1 rounded-lg text-[10px] font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
                      Prendre en charge
                    </button>
                  )
                )}
              </div>
              <p className="mt-1 text-white/50">
                <b className="text-white/70">Enlèvement :</b> {m.pickup?.address} ({m.pickup?.zone_code})
                {m.pickup?.date ? ` · ${m.pickup.date}${m.pickup.slot ? ' ' + m.pickup.slot : ''}` : ''}
                {m.pickup?.contact ? ` · ${m.pickup.contact}` : ''}
              </p>
              <p className="text-white/50">
                <b className="text-white/70">Livraison :</b> {m.delivery?.address} ({m.delivery?.zone_code})
                {m.delivery?.date ? ` · ${m.delivery.date}${m.delivery.slot ? ' ' + m.delivery.slot : ''}` : ''}
              </p>
              {m.goods_summary && <p className="text-white/40">Marchandises : {m.goods_summary}</p>}
            </div>
          );
        })}
        {!items.length && <p className="text-sm text-white/45">Aucun Ordre de Transport dans vos zones.</p>}
      </div>
    </div>
  );
};
