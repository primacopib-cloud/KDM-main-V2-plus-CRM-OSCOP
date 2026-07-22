import { useCallback, useEffect, useState } from 'react';
import { Megaphone, Rocket, Flame, Loader2, FileBarChart, CalendarPlus, Trash2, Mail } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const KIND_LABELS = { kickoff: ['🚀 Coup d\'envoi', 'text-emerald-300'], boost: ['🔥 Relance classement', 'text-amber-300'], report: ['📊 Bilan mensuel', 'text-sky-300'] };

export const ParrainiaPanel = () => {
  const [log, setLog] = useState(null);
  const [programs, setPrograms] = useState([]);
  const [running, setRunning] = useState('');
  const [reading, setReading] = useState(null);
  const [editing, setEditing] = useState(null);

  const [testSending, setTestSending] = useState('');

  const testSend = async (kind) => {
    setTestSending(kind);
    const r = await fetch(`${API}/admin/parrainia/programs/${editing.id}/test-send`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind }),
    });
    const d = await r.json();
    setTestSending('');
    if (!r.ok) return toast.error(d.detail || 'Envoi du test échoué');
    toast.success(`Email de test envoyé à ${d.to}`);
  };

  const saveProgram = async () => {
    const r = await fetch(`${API}/admin/parrainia/programs/${editing.id}`, {
      method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        theme: editing.theme, kickoff_subject: editing.kickoff_subject, kickoff_body: editing.kickoff_body,
        boost_subject: editing.boost_subject, boost_body: editing.boost_body,
      }),
    });
    const d = await r.json();
    if (!r.ok) return toast.error(d.detail || 'Enregistrement échoué');
    toast.success(`Programme ${d.month} mis à jour`);
    setEditing(null);
    load();
  };

  const load = useCallback(() => {
    fetch(`${API}/admin/parrainia/log`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then((d) => setLog(d?.items || [])).catch(() => {});
    fetch(`${API}/admin/parrainia/programs`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null)).then((d) => setPrograms(d?.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const report = async () => {
    if (!window.confirm("PARRAIN'IA va rédiger et envoyer le bilan du mois en cours à l'équipe admin. Continuer ?")) return;
    setRunning('report');
    const r = await fetch(`${API}/admin/parrainia/report`, { method: 'POST', credentials: 'include' });
    const d = await r.json();
    setRunning('');
    if (!r.ok) return toast.error(d.detail || 'Bilan échoué');
    toast.success(`Bilan envoyé à ${d.sent} admin(s)`);
    load();
  };

  const createProgram = async (months = 1) => {
    setRunning(months > 1 ? 'quarter' : 'program');
    const r = await fetch(`${API}/admin/parrainia/programs/generate`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ months }),
    });
    const d = await r.json();
    setRunning('');
    if (!r.ok) return toast.error(d.detail || 'Création échouée');
    if (d.items) toast.success(`${d.created} programme(s) planifié(s) : ${d.items.map((p) => p.month).join(', ')}`);
    else toast.success(`Programme « ${d.theme} » planifié pour ${d.month}`);
    load();
  };

  const deleteProgram = async (p) => {
    if (!window.confirm(`Supprimer le programme « ${p.theme} » (${p.month}) ?`)) return;
    await fetch(`${API}/admin/parrainia/programs/${p.id}`, { method: 'DELETE', credentials: 'include' });
    load();
  };

  const animate = async (kind) => {
    const label = kind === 'kickoff' ? 'le coup d\'envoi du défi du mois' : 'la relance de classement';
    if (!window.confirm(`PARRAIN'IA va rédiger et envoyer ${label} par email à tous les parrains. Continuer ?`)) return;
    setRunning(kind);
    const r = await fetch(`${API}/admin/parrainia/animate`, {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind }),
    });
    const d = await r.json();
    setRunning('');
    if (!r.ok) return toast.error(d.detail || 'Campagne échouée');
    toast.success(`PARRAIN'IA : ${d.sent} email(s) envoyés${d.launched_challenge ? ' — défi du mois activé automatiquement' : ''}`);
    load();
  };

  return (
    <div className="glass-panel-soft rounded-[18px] p-5 space-y-4" data-testid="parrainia-panel">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-display text-base text-white flex items-center gap-2">
          <Megaphone size={15} style={{ color: '#D9B35A' }} /> PARRAIN'IA — animation du programme de parrainage
        </h3>
        <div className="flex gap-2">
          <button onClick={() => animate('kickoff')} disabled={!!running} data-testid="parrainia-kickoff-btn"
            className="px-3 py-2 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 disabled:opacity-60"
            style={{ background: '#D9B35A', color: '#1F0A33' }}>
            {running === 'kickoff' ? <Loader2 size={12} className="animate-spin" /> : <Rocket size={12} />} Lancer le défi du mois
          </button>
          <button onClick={() => animate('boost')} disabled={!!running} data-testid="parrainia-boost-btn"
            className="px-3 py-2 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 bg-white/[0.06] border border-white/15 text-white/80 disabled:opacity-60">
            {running === 'boost' ? <Loader2 size={12} className="animate-spin" /> : <Flame size={12} />} Animer le classement
          </button>
          <button onClick={report} disabled={!!running} data-testid="parrainia-report-btn"
            className="px-3 py-2 rounded-lg text-xs font-bold inline-flex items-center gap-1.5 bg-white/[0.06] border border-white/15 text-white/80 disabled:opacity-60">
            {running === 'report' ? <Loader2 size={12} className="animate-spin" /> : <FileBarChart size={12} />} Bilan IA du mois
          </button>
        </div>
      </div>
      <p className="text-xs text-white/50">
        En automatique : coup d'envoi en début de mois (active le défi si besoin), relance de mi-mois avec le
        classement personnalisé de chaque parrain, et bilan mensuel envoyé à l'équipe admin.
      </p>

      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07] space-y-2" data-testid="parrainia-programs">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <p className="text-xs font-semibold text-white/70 flex items-center gap-1.5">
            <CalendarPlus size={13} className="text-[#D9B35A]" /> Programmes de parrainage créés par l'IA (programmés pour diffusion)
          </p>
          <button onClick={() => createProgram(1)} disabled={!!running} data-testid="parrainia-create-program-btn"
            className="px-2.5 py-1.5 rounded-lg text-[11px] font-bold inline-flex items-center gap-1 bg-[#D9B35A]/15 border border-[#D9B35A]/30 text-[#E9CF8E] disabled:opacity-60">
            {running === 'program' ? <Loader2 size={11} className="animate-spin" /> : <CalendarPlus size={11} />} Mois prochain
          </button>
          <button onClick={() => createProgram(3)} disabled={!!running} data-testid="parrainia-create-quarter-btn"
            className="px-2.5 py-1.5 rounded-lg text-[11px] font-bold inline-flex items-center gap-1 bg-[#D9B35A]/15 border border-[#D9B35A]/30 text-[#E9CF8E] disabled:opacity-60">
            {running === 'quarter' ? <Loader2 size={11} className="animate-spin" /> : <CalendarPlus size={11} />} Planifier le trimestre
          </button>
        </div>
        {programs.length === 0 ? (
          <p className="text-[11px] text-white/40 italic">Aucun programme planifié — l'IA peut concevoir thème, récompenses et emails de campagne en un clic.</p>
        ) : programs.map((p) => (
          <div key={p.id} className="flex items-center gap-2 text-xs p-2 rounded-lg bg-white/[0.04] border border-white/[0.06]" data-testid={`parrainia-program-${p.id}`}>
            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${p.status === 'SCHEDULED' ? 'bg-sky-500/20 text-sky-300' : 'bg-emerald-500/20 text-emerald-300'}`}>
              {p.status === 'SCHEDULED' ? 'PLANIFIÉ' : 'ACTIF'}
            </span>
            <b className="text-white/85">{p.month}</b>
            <span className="text-white/70 truncate flex-1">« {p.theme} »</span>
            <span className="text-[#E9CF8E] font-bold">🥇{p.reward_credits} 🥈{p.reward_2nd} 🥉{p.reward_3rd}</span>
            {p.status === 'SCHEDULED' && (
              <>
                <button onClick={() => setEditing({ ...p })} data-testid={`parrainia-program-preview-${p.id}`}
                  className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-[#D9B35A]/15 border border-[#D9B35A]/30 text-[#E9CF8E] hover:bg-[#D9B35A]/25 inline-flex items-center gap-1 transition-colors">
                  <Mail size={10} /> Aperçu emails
                </button>
                <button onClick={() => deleteProgram(p)} className="p-1 rounded text-white/40 hover:text-red-400" data-testid={`parrainia-program-delete-${p.id}`}>
                  <Trash2 size={12} />
                </button>
              </>
            )}
          </div>
        ))}
      </div>
      <div className="space-y-1.5" data-testid="parrainia-log">
        {log === null ? null : log.length === 0 ? (
          <p className="text-xs text-white/40 italic">Aucune animation envoyée pour le moment.</p>
        ) : log.map((l) => {
          const [label, cls] = KIND_LABELS[l.kind] || [l.kind, 'text-white/60'];
          return (
            <div key={l.id} className="flex items-center gap-2 text-xs p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <span className={`font-bold ${cls}`}>{label}</span>
              <span className="text-white/70 truncate flex-1">« {l.subject} »</span>
              <span className="text-white/45">{l.sent} envoyé(s)</span>
              <span className="text-white/35">{new Date(l.at).toLocaleDateString('fr-FR')}</span>
              {l.kind === 'report' && l.analysis && (
                <button onClick={() => setReading(l)} data-testid={`parrainia-read-report-${l.id}`}
                  className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-sky-500/15 border border-sky-500/30 text-sky-300 hover:bg-sky-500/25 transition-colors">
                  Lire
                </button>
              )}
              {l.triggered_by === 'parrainia-auto' && <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-white/10 text-white/50">AUTO</span>}
            </div>
          );
        })}
      </div>

      {editing && (
        <div className="fixed inset-0 z-[70] bg-black/70 flex items-center justify-center p-4" onClick={() => setEditing(null)} data-testid="parrainia-program-modal">
          <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl bg-[#1A092D] border border-white/15 p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <Mail size={14} className="text-[#D9B35A]" /> Emails du programme {editing.month}
              </h4>
              <button onClick={() => setEditing(null)} className="text-white/50 hover:text-white text-lg leading-none">✕</button>
            </div>
            <div>
              <label className="text-[11px] font-bold text-white/60 uppercase">Thème</label>
              <input value={editing.theme} onChange={(e) => setEditing({ ...editing, theme: e.target.value })}
                data-testid="parrainia-edit-theme"
                className="w-full h-9 mt-1 px-2.5 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15" />
            </div>
            {[['kickoff', '🚀 Email de coup d\'envoi (début de mois)'], ['boost', '🔥 Email de relance (mi-mois)']].map(([kind, label]) => (
              <div key={kind} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07] space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[11px] font-bold text-white/60 uppercase">{label}</p>
                  <button onClick={() => testSend(kind)} disabled={!!testSending} data-testid={`parrainia-test-send-${kind}`}
                    className="px-2 py-1 rounded-lg text-[10px] font-bold bg-white/[0.06] border border-white/15 text-white/70 hover:text-white inline-flex items-center gap-1 disabled:opacity-60 transition-colors">
                    {testSending === kind ? <Loader2 size={10} className="animate-spin" /> : <Mail size={10} />} M'envoyer un test
                  </button>
                </div>
                <input value={editing[`${kind}_subject`]} onChange={(e) => setEditing({ ...editing, [`${kind}_subject`]: e.target.value })}
                  data-testid={`parrainia-edit-${kind}-subject`} placeholder="Objet"
                  className="w-full h-9 px-2.5 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15" />
                <textarea rows={5} value={editing[`${kind}_body`]} onChange={(e) => setEditing({ ...editing, [`${kind}_body`]: e.target.value })}
                  data-testid={`parrainia-edit-${kind}-body`}
                  className="w-full px-2.5 py-2 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15" />
                <p className="text-[10px] text-white/40 mb-1">Aperçu :</p>
                <div className="p-3 rounded-lg bg-white text-gray-800 text-xs [&_p]:mb-1.5"
                  dangerouslySetInnerHTML={{ __html: (editing[`${kind}_body`] || '')
                    .replaceAll('{prenom}', 'Marie').replaceAll('{classement}', '#2')
                    .replaceAll('{filleuls}', '3').replaceAll('{recompense}', `+${editing.reward_credits} CREDI'SCOP`)
                    .replaceAll('{lien}', '#') }} />
              </div>
            ))}
            <p className="text-[10px] text-white/40">Variables disponibles : {'{prenom} {classement} {filleuls} {recompense} {lien}'} — remplacées pour chaque parrain à l'envoi.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setEditing(null)} className="px-3 py-2 rounded-lg text-xs text-white/60 border border-white/15">Annuler</button>
              <button onClick={saveProgram} data-testid="parrainia-program-save-btn"
                className="px-4 py-2 rounded-lg text-xs font-bold" style={{ background: '#D9B35A', color: '#1F0A33' }}>
                Enregistrer le programme
              </button>
            </div>
          </div>
        </div>
      )}

      {reading && (
        <div className="fixed inset-0 z-[70] bg-black/70 flex items-center justify-center p-4" onClick={() => setReading(null)} data-testid="parrainia-report-modal">
          <div className="w-full max-w-lg max-h-[80vh] overflow-y-auto rounded-2xl bg-[#1A092D] border border-white/15 p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <FileBarChart size={14} className="text-sky-300" /> Bilan PARRAIN'IA — {reading.month}
              </h4>
              <button onClick={() => setReading(null)} data-testid="parrainia-report-modal-close"
                className="text-white/50 hover:text-white text-lg leading-none">✕</button>
            </div>
            <p className="text-[11px] text-white/45 mb-3">{reading.sent} destinataire(s) · {new Date(reading.at).toLocaleString('fr-FR')}</p>
            <div className="text-xs text-white/80 space-y-2 [&_p]:mb-2 [&_ul]:list-disc [&_ul]:pl-4 [&_li]:mb-1"
              dangerouslySetInnerHTML={{ __html: reading.analysis }} />
          </div>
        </div>
      )}
    </div>
  );
};
