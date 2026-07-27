import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Users, Plus, Pencil, Archive, ArchiveRestore, Loader2, FileClock, Download } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { lolodriveAPI } from '../../services/api';
import { printHoursSheet } from './hoursSheetPrint';

export const PosOperatorsPanel = () => {
  const [operators, setOperators] = useState(null);
  const [breaks, setBreaks] = useState({});
  const [hours, setHours] = useState({});
  const [dialog, setDialog] = useState(null);
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [saving, setSaving] = useState(false);
  const [accountant, setAccountant] = useState('');
  const [sendingReport, setSendingReport] = useState(false);

  const load = () => {
    lolodriveAPI.managerOperators().then((d) => {
      setOperators(d.operators || []);
      setAccountant(d.accountant_email || '');
    }).catch(() => setOperators(null));
    lolodriveAPI.managerOperatorBreaks(7).then((d) => {
      const map = {};
      (d.operators || []).forEach((o) => { map[o.operator_name] = o; });
      setBreaks(map);
    }).catch(() => {});
    lolodriveAPI.managerOperatorHours(7).then((d) => {
      const map = {};
      (d.operators || []).forEach((o) => { map[o.operator_id] = o; });
      setHours(map);
    }).catch(() => {});
  };
  useEffect(() => { load(); }, []);
  if (operators === null) return null;

  const openCreate = () => { setForm({ name: '', email: '', password: '' }); setDialog({ mode: 'create' }); };
  const openEdit = (op) => { setForm({ name: op.contact_name || '', email: op.email, password: '' }); setDialog({ mode: 'edit', op }); };

  const save = async () => {
    setSaving(true);
    try {
      if (dialog.mode === 'create') {
        await lolodriveAPI.managerCreateOperator(form);
        toast.success(`Opérateur "${form.name}" créé — il peut se connecter avec ${form.email} ✓`);
      } else {
        await lolodriveAPI.managerUpdateOperator(dialog.op.id, { ...form, password: form.password || undefined });
        toast.success(`Opérateur "${form.name}" modifié ✓`);
      }
      setDialog(null);
      load();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  const exportHoursCsv = async () => {
    try {
      const month = new Date().toISOString().slice(0, 7);
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/lolodrive/manager/operator-hours-export?month=${month}`,
        { credentials: 'include' });
      if (!r.ok) { toast.error('Export impossible'); return; }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `heures-${month}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Relevés d\'heures exportés en CSV ✓');
    } catch { toast.error('Erreur de connexion'); }
  };

  const saveAccountant = async () => {
    try {
      const r = await lolodriveAPI.managerSetAccountantEmail(accountant);
      toast.success(r.accountant_email
        ? `Comptable enregistré : ${r.accountant_email} — rapport automatique chaque 1er du mois ✓`
        : 'Envoi comptable désactivé');
    } catch (e) { toast.error(e.message); }
  };

  const sendReportNow = async () => {
    setSendingReport(true);
    try {
      const r = await lolodriveAPI.managerSendAccountantReport(new Date().toISOString().slice(0, 7));
      toast.success(`Rapport ${r.month} (caisse + heures) envoyé à ${r.sent_to} ✓`);
    } catch (e) { toast.error(e.message); } finally { setSendingReport(false); }
  };

  const hoursSheet = async (op) => {
    try {
      const data = await lolodriveAPI.managerOperatorHoursSheet(op.id, new Date().toISOString().slice(0, 7));
      printHoursSheet(data);
    } catch (e) { toast.error(e.message); }
  };

  const toggleArchive = async (op) => {
    try {
      await lolodriveAPI.managerArchiveOperator(op.id, !op.is_archived);
      toast.success(op.is_archived ? `"${op.contact_name}" réactivé ✓` : `"${op.contact_name}" archivé — connexion bloquée`);
      load();
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="mt-6 rounded-2xl bg-white/[0.025] border border-white/[0.07] p-5" data-testid="pos-operators-panel">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="font-semibold flex items-center gap-2">
          <Users className="w-4 h-4 text-emerald-400" /> Opérateurs POS ({operators.length})
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={exportHoursCsv} data-testid="export-hours-csv-btn"
            title="Export CSV des relevés d'heures du mois (comptable)"
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold text-[#22d3ee] bg-[#22d3ee]/10 border border-[#22d3ee]/30 hover:bg-[#22d3ee]/20">
            <Download className="w-3 h-3" /> Export heures CSV
          </button>
          <Button size="sm" onClick={openCreate} data-testid="create-operator-btn"
            className="bg-emerald-600 hover:bg-emerald-500 text-white">
            <Plus className="w-3 h-3 mr-1" /> Créer un opérateur
          </Button>
        </div>
      </div>
      <p className="text-[11px] text-white/40 mb-3">Vos employés se connectent sur /connexion avec leurs identifiants et accèdent au POS de votre relais. Leur nom et l'horodatage de connexion s'affichent en caisse.</p>
      <div className="mb-4 flex flex-wrap items-center gap-2 p-2.5 rounded-lg bg-[#22d3ee]/[0.05] border border-[#22d3ee]/20 text-xs"
        data-testid="accountant-block">
        <span className="font-bold text-[#22d3ee]">Comptable :</span>
        <input type="email" placeholder="email@cabinet-comptable.fr" value={accountant} data-testid="accountant-email-input"
          onChange={(e) => setAccountant(e.target.value)}
          className="flex-1 min-w-[200px] px-2 py-1 rounded bg-white/5 border border-white/15 text-white text-xs" />
        <button type="button" onClick={saveAccountant} data-testid="accountant-save-btn"
          className="px-2.5 py-1 rounded-lg font-bold text-black bg-[#22d3ee] hover:bg-[#06b6d4]">Enregistrer</button>
        <button type="button" onClick={sendReportNow} disabled={sendingReport || !accountant} data-testid="accountant-send-now-btn"
          className="px-2.5 py-1 rounded-lg font-bold text-[#22d3ee] bg-[#22d3ee]/10 border border-[#22d3ee]/35 hover:bg-[#22d3ee]/20 disabled:opacity-40">
          {sendingReport ? 'Envoi…' : 'Envoyer le rapport maintenant'}
        </button>
        <span className="w-full text-[10px] text-white/35">Rapport automatique (caisse + relevés d'heures du mois écoulé) envoyé chaque 1er du mois.</span>
      </div>
      {operators.length === 0 && <p className="text-xs text-white/40" data-testid="no-operators">Aucun opérateur pour le moment.</p>}
      <div className="space-y-1.5">
        {operators.map((op) => (
          <div key={op.id} className="flex flex-wrap items-center gap-3 text-xs p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06]"
            data-testid={`operator-row-${op.id}`}>
            <span className="flex-1 min-w-[180px]">
              <b className={op.is_archived ? 'text-white/40 line-through' : ''}>{op.contact_name}</b>
              <span className="text-white/40"> · {op.email}</span>
              {op.last_login_at && (
                <span className="block text-[10px] text-white/35">
                  Dernière connexion : {new Date(op.last_login_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
              {breaks[op.contact_name] && (
                <span className="block text-[10px] text-amber-200/70" data-testid={`operator-breaks-${op.id}`}>
                  Pauses 7 j : {breaks[op.contact_name].count} ({breaks[op.contact_name].total_min} min)
                  {breaks[op.contact_name].on_break && <b className="ml-1 text-amber-300">· En pause actuellement ☕</b>}
                </span>
              )}
              {hours[op.id] && hours[op.id].total_presence_min > 0 && (
                <span className="block text-[10px] text-emerald-200/70" data-testid={`operator-hours-${op.id}`}>
                  Présence en caisse 7 j : ~{Math.floor(hours[op.id].total_presence_min / 60)}h{String(hours[op.id].total_presence_min % 60).padStart(2, '0')} (pauses déduites)
                </span>
              )}
            </span>
            <span className={`px-2 py-0.5 rounded-full font-semibold ${op.is_archived ? 'text-white/40 bg-white/[0.05]' : 'text-emerald-300 bg-emerald-400/10'}`}
              data-testid={`operator-status-${op.id}`}>
              {op.is_archived ? 'Archivé' : 'Actif'}
            </span>
            <span className="flex gap-1.5 shrink-0">
              <button type="button" onClick={() => hoursSheet(op)} data-testid={`hours-sheet-${op.id}`}
                title="Relevé d'heures mensuel imprimable (paie)"
                className="flex items-center gap-1 px-2 py-1 rounded-lg font-bold text-[#22d3ee] bg-[#22d3ee]/10 border border-[#22d3ee]/30 hover:bg-[#22d3ee]/20">
                <FileClock className="w-3 h-3" /> Relevé d'heures
              </button>
              <button type="button" onClick={() => openEdit(op)} data-testid={`edit-operator-${op.id}`}
                className="flex items-center gap-1 px-2 py-1 rounded-lg font-bold text-[#D9B35A] bg-[#D9B35A]/10 border border-[#D9B35A]/30 hover:bg-[#D9B35A]/20">
                <Pencil className="w-3 h-3" /> Modifier
              </button>
              <button type="button" onClick={() => toggleArchive(op)} data-testid={`archive-operator-${op.id}`}
                className={`flex items-center gap-1 px-2 py-1 rounded-lg font-bold border ${
                  op.is_archived ? 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30 hover:bg-emerald-400/20'
                    : 'text-red-300 bg-red-500/10 border-red-400/30 hover:bg-red-500/20'}`}>
                {op.is_archived ? <><ArchiveRestore className="w-3 h-3" /> Réactiver</> : <><Archive className="w-3 h-3" /> Archiver</>}
              </button>
            </span>
          </div>
        ))}
      </div>

      {dialog && (
        <Dialog open onOpenChange={(v) => { if (!v) setDialog(null); }}>
          <DialogContent className="bg-[#15151c] border-white/10 text-white max-w-sm" data-testid="operator-dialog">
            <DialogHeader>
              <DialogTitle className="text-base">{dialog.mode === 'create' ? 'Créer un opérateur POS' : `Modifier ${dialog.op.contact_name}`}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <Input placeholder="Nom de l'employé *" value={form.name} data-testid="operator-name-input"
                onChange={(e) => setForm({ ...form, name: e.target.value })} className="bg-white/5 border-white/10" />
              <Input type="email" placeholder="Email de connexion *" value={form.email} data-testid="operator-email-input"
                onChange={(e) => setForm({ ...form, email: e.target.value })} className="bg-white/5 border-white/10" />
              <Input type="password" value={form.password} data-testid="operator-password-input"
                placeholder={dialog.mode === 'create' ? 'Mot de passe * (8 car. min)' : 'Nouveau mot de passe (laisser vide pour conserver)'}
                onChange={(e) => setForm({ ...form, password: e.target.value })} className="bg-white/5 border-white/10" />
              <Button onClick={save} disabled={saving} data-testid="operator-save-btn"
                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : dialog.mode === 'create' ? "Créer l'opérateur" : 'Enregistrer'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};
