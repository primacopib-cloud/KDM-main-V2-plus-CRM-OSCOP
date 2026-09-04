import { useCallback, useEffect, useState } from 'react';
import { ShieldCheck, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

export const StaffRolesPanel = () => {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ email: '', role: 'OSCOP_FINANCE' });

  const load = useCallback(async () => {
    const res = await fetch(`${API}/admin/staff-roles`, { headers: getAuthHeaders() });
    if (res.ok) setData(await res.json());
  }, []);
  useEffect(() => { load(); }, [load]);

  const assign = async () => {
    const res = await fetch(`${API}/admin/staff-roles`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(form),
    });
    const json = await res.json();
    if (!res.ok) { toast.error(typeof json.detail === 'string' ? json.detail : 'Erreur'); return; }
    toast.success(`Rôle ${form.role} attribué`);
    setForm({ ...form, email: '' });
    load();
  };

  const revoke = async (email) => {
    await fetch(`${API}/admin/staff-roles/${encodeURIComponent(email)}`, { method: 'DELETE', headers: getAuthHeaders() });
    toast.success('Rôle révoqué');
    load();
  };

  if (!data) return null;

  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-6" data-testid="staff-roles-panel">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-1">
        <ShieldCheck className="w-5 h-5 text-[#D9B35A]" /> Rôles granulaires achat-revente (contrôle serveur)
      </h3>
      <p className="text-white/50 text-xs mb-3">
        OSCOP_FINANCE : tranches, décaissements, statuts · LOGISCOP_MANAGER : expéditions, stock, POD ·
        AUDITOR_READ_ONLY : lecture seule — les droits sont appliqués côté serveur.
      </p>
      <div className="flex gap-2 mb-3 flex-wrap">
        <Input placeholder="email@exemple.fr" value={form.email} data-testid="staff-role-email"
          onChange={(e) => setForm({ ...form, email: e.target.value })} className="max-w-[260px] h-8 text-xs bg-white/5 border-white/15 text-white" />
        <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}
          data-testid="staff-role-select" className="bg-white/5 border border-white/15 rounded px-2 py-1.5 text-xs text-white">
          {data.available_roles.map((r) => <option key={r} className="bg-[#2A1045]">{r}</option>)}
        </select>
        <Button size="sm" onClick={assign} data-testid="staff-role-assign"
          className="bg-[#D9B35A] text-[#2A1045] hover:bg-[#F2D07A] h-8">Attribuer</Button>
      </div>
      {data.assignments.length === 0 && <p className="text-white/40 text-xs">Aucun rôle attribué.</p>}
      {data.assignments.map((a) => (
        <div key={a.email} className="flex items-center justify-between bg-white/5 rounded px-2.5 py-1.5 mb-1 text-xs">
          <span className="text-white/85">{a.email} — <b className="text-[#D9B35A]">{a.role}</b></span>
          <button onClick={() => revoke(a.email)} data-testid={`revoke-role-${a.email}`}
            className="text-red-300/70 hover:text-red-300"><Trash2 className="w-3.5 h-3.5" /></button>
        </div>
      ))}
    </div>
  );
};
