import { useCallback, useEffect, useState } from 'react';
import { UserCheck } from 'lucide-react';
import { toast } from 'sonner';
import { API, getAuthHeaders } from '../../services/http';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';

export const InvestorApplicationsPanel = () => {
  const [apps, setApps] = useState(null);

  const load = useCallback(async () => {
    const res = await fetch(`${API}/investor/applications`, { headers: getAuthHeaders() });
    if (res.ok) setApps((await res.json()).applications);
  }, []);
  useEffect(() => { load(); }, [load]);

  const decide = async (id, decision) => {
    const res = await fetch(`${API}/investor/applications/${id}/decision`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ decision }),
    });
    if (!res.ok) { toast.error('Action impossible'); return; }
    toast.success(decision === 'approve' ? 'Compte investisseur créé' : 'Candidature rejetée');
    load();
  };

  if (!apps) return null;

  return (
    <div className="glass-panel-soft rounded-[18px] p-4 mt-5" data-testid="investor-applications-panel">
      <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-2">
        <UserCheck className="w-5 h-5 text-[#D9B35A]" /> Candidatures investisseurs
      </h3>
      {apps.length === 0 && <p className="text-white/40 text-xs">Aucune candidature.</p>}
      {apps.map((a) => (
        <div key={a.id} className="flex items-center justify-between gap-2 bg-white/5 rounded px-2.5 py-2 mb-1 text-xs flex-wrap" data-testid={`investor-app-${a.email}`}>
          <span className="text-white/85">{a.name} — {a.email}{a.phone ? ` · ${a.phone}` : ''}</span>
          <div className="flex items-center gap-1.5">
            <Badge className={`border-0 text-[9px] ${a.status === 'approved' ? 'bg-emerald-500/20 text-emerald-300' : a.status === 'rejected' ? 'bg-red-500/20 text-red-300' : 'bg-white/10 text-white/60'}`}>{a.status}</Badge>
            {a.status === 'pending' && (
              <>
                <Button size="sm" data-testid={`approve-investor-${a.email}`} className="h-6 text-[10px] bg-emerald-600/40 hover:bg-emerald-600/60 text-white"
                  onClick={() => decide(a.id, 'approve')}>Approuver</Button>
                <Button size="sm" data-testid={`reject-investor-${a.email}`} className="h-6 text-[10px] bg-red-600/30 hover:bg-red-600/50 text-white"
                  onClick={() => decide(a.id, 'reject')}>Rejeter</Button>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
