import { useEffect, useState } from 'react';
import { Scale, Save, Loader2, BookOpen, FileDown, FileSpreadsheet } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { RcrReimbursements } from './RcrReimbursements';
import { AttestationQueue } from './AttestationQueue';
import { RcrStatements } from './RcrStatements';

const FIELDS = [['capital', 'Capital (€)'], ['siege', 'Siège social'], ['rcs', 'RCS'], ['siren', 'SIREN'], ['representant', 'Représentant']];

const download = async (url, filename) => {
  const r = await fetch(url, { credentials: 'include', headers: getAuthHeaders() });
  if (!r.ok) throw new Error('Export impossible');
  const blob = await r.blob();
  const u = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = u; a.download = filename; a.click();
  URL.revokeObjectURL(u);
};

export const ConventionRegistres = () => {
  const [settings, setSettings] = useState(null);
  const [reg, setReg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [open, setOpen] = useState(false);

  const loadReg = () => {
    const h = { credentials: 'include', headers: getAuthHeaders() };
    fetch(`${API}/convention/admin/registres`, h).then((r) => (r.ok ? r.json() : null)).then(setReg).catch(() => {});
  };

  useEffect(() => {
    const h = { credentials: 'include', headers: getAuthHeaders() };
    fetch(`${API}/convention/admin/settings`, h).then((r) => (r.ok ? r.json() : null)).then(setSettings).catch(() => {});
    loadReg();
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/convention/admin/settings`, {
        method: 'PUT', credentials: 'include',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (!r.ok) throw new Error();
      toast.success('Réglages convention enregistrés');
    } catch { toast.error('Enregistrement impossible'); }
    setSaving(false);
  };

  const setParty = (party, k, v) => setSettings({ ...settings, [party]: { ...settings[party], [k]: v } });

  return (
    <div className="space-y-4 mb-6" data-testid="convention-registres">
      <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(217,179,90,0.25)' }}>
        <button type="button" onClick={() => setOpen(!open)} data-testid="legal-settings-toggle"
          className="flex items-center gap-2 text-sm font-semibold text-white/85">
          <Scale className="w-4 h-4 text-[#D9B35A]" /> Réglages Convention cadre (infos légales, RCR)
          <span className="text-white/40 text-xs">{open ? '▲' : '▼'}</span>
        </button>
        {open && settings && (
          <div className="mt-3 space-y-4">
            {['oscop', 'kdmarche'].map((party) => (
              <div key={party}>
                <p className="text-[11px] uppercase tracking-wide text-[#E9CF8E] mb-1.5">{party === 'oscop' ? "O'SCOP (SCIC)" : 'KDMARCHÉ PRO'}</p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {FIELDS.map(([k, label]) => (
                    <label key={k} className="text-[10px] text-white/50">{label}
                      <input value={settings[party]?.[k] || ''} onChange={(e) => setParty(party, k, e.target.value)}
                        data-testid={`legal-${party}-${k}`}
                        className="block mt-0.5 w-full h-8 px-2 rounded-lg text-xs text-white bg-white/[0.06] border border-white/15 focus:outline-none" />
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <div className="flex flex-wrap gap-3 items-end">
              {[['rcr_default_rate', 'Taux RCR défaut (%)'], ['rcr_global_cap_eur', 'Plafond global RCR (€)'], ['tribunal', 'Tribunal de commerce']].map(([k, label]) => (
                <label key={k} className="text-[10px] text-white/50">{label}
                  <input value={settings[k] ?? ''} onChange={(e) => setSettings({ ...settings, [k]: e.target.value })}
                    data-testid={`legal-${k}`}
                    className="block mt-0.5 w-40 h-8 px-2 rounded-lg text-xs text-white bg-white/[0.06] border border-white/15 focus:outline-none" />
                </label>
              ))}
              <button type="button" onClick={save} disabled={saving} data-testid="legal-settings-save"
                className="inline-flex items-center gap-1.5 h-8 px-4 rounded-lg text-xs font-bold disabled:opacity-50"
                style={{ background: '#D9B35A', color: '#070A10' }}>
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />} Enregistrer
              </button>
            </div>
          </div>
        )}
      </div>

      <AttestationQueue onSigned={loadReg} />

      {reg && (
        <div className="rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <p className="flex items-center gap-2 text-sm font-semibold text-white/85">
              <BookOpen className="w-4 h-4 text-[#7BC94E]" /> Registres — Conventions, Attestations & FOGEDOM-RCR
            </p>
            <span className="inline-flex gap-2">
              <button type="button" data-testid="rcr-export-csv-btn"
                onClick={async () => {
                  try { await download(`${API}/convention/admin/registres/export.csv`, 'registre-fogedom-rcr.csv'); toast.success('Export CSV téléchargé'); }
                  catch (e) { toast.error(e.message); }
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-white/[0.06] text-white/75 hover:text-[#E9CF8E] border border-white/15">
                <FileSpreadsheet size={12} /> Export CSV
              </button>
              <button type="button" data-testid="rcr-export-pdf-btn"
                onClick={async () => {
                  try { await download(`${API}/convention/admin/registres/export.pdf`, 'registre-fogedom-rcr.pdf'); toast.success('Export PDF téléchargé'); }
                  catch (e) { toast.error(e.message); }
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold"
                style={{ background: '#D9B35A', color: '#070A10' }}>
                <FileDown size={12} /> Export PDF (double validation)
              </button>
            </span>
          </div>
          <div className="flex flex-wrap gap-2 text-[10px] font-bold mb-3">
            <span className="px-2 py-1 rounded-full text-white/70 bg-white/[0.06]">{reg.totaux.conventions} convention(s)</span>
            <span className="px-2 py-1 rounded-full text-white/70 bg-white/[0.06]">{reg.totaux.attestations} attestation(s)</span>
            <span className="px-2 py-1 rounded-full text-[#E9CF8E] bg-[#D4AF37]/12">Plafond-cible total : {(reg.totaux.plafond_cible_total_cents / 100).toLocaleString('fr-FR')} €</span>
            <span className="px-2 py-1 rounded-full text-[#93C5FD] bg-[#60A5FA]/12">Retenues effectives : {(reg.totaux.retenues_effectives_cents / 100).toLocaleString('fr-FR')} €</span>
            <span className="px-2 py-1 rounded-full text-white/50 bg-white/[0.06]">Cap global : {reg.totaux.rcr_global_cap_eur.toLocaleString('fr-FR')} € / fournisseur</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-left text-white/40 border-b border-white/[0.08]">
                <th className="py-1.5 pr-3">Fournisseur</th><th className="py-1.5 pr-3">Attestations</th>
                <th className="py-1.5 pr-3">Montant agrégé</th><th className="py-1.5 pr-3">Plafond-cible RCR</th>
                <th className="py-1.5">Cap</th></tr></thead>
              <tbody>
                {reg.registre_rcr.map((v) => (
                  <tr key={v.vendor_id} className="border-b border-white/[0.04] text-white/75" data-testid={`rcr-row-${v.vendor_id}`}>
                    <td className="py-1.5 pr-3 font-semibold text-white/90">{v.vendor_name || v.vendor_id}</td>
                    <td className="py-1.5 pr-3">{v.attestations}</td>
                    <td className="py-1.5 pr-3">{(v.montant_agrege_cents / 100).toLocaleString('fr-FR')} €</td>
                    <td className="py-1.5 pr-3 font-bold text-[#E9CF8E]">{(v.plafond_cible_cents / 100).toLocaleString('fr-FR')} €</td>
                    <td className="py-1.5">{v.cap_reached ? <span className="text-red-400 font-bold">Atteint</span> : <span className="text-[#7BC94E]">OK</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-white/35 mt-2">
            Attestations récentes : {reg.attestations.slice(0, 5).map((a) => `${a.ref} (${a.status === 'signed' ? 'signée' : a.status === 'closed' ? 'clôturée' : 'en attente'})`).join(' · ') || 'aucune'}
          </p>
        </div>
      )}

      <RcrReimbursements />

      <RcrStatements />
    </div>
  );
};
