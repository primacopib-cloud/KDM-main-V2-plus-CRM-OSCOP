import i18n from '@/i18n';
import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { TreePine, RefreshCw, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(i18n.language, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (_e) { return iso; }
};

export const IaboisProjectsPanel = () => {
  const [projects, setProjects] = useState([]);
  const [syncing, setSyncing] = useState(false);

  const fetchProjects = useCallback(async () => {
    const r = await fetch(`${API}/connectors/iabois/projects`, { credentials: 'include' });
    if (r.ok) setProjects((await r.json()).projects || []);
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const syncNow = async () => {
    setSyncing(true);
    try {
      const r = await fetch(`${API}/connectors/oscop-ia-bois/sync`, { method: 'POST', credentials: 'include' });
      const data = await r.json();
      toast[data.status === 'SUCCESS' ? 'success' : 'error'](
        data.status === 'SUCCESS'
          ? i18n.t('adm.iabois_sync_ok', { total: data.total, new: data.new })
          : (data.error || 'ERROR')
      );
      await fetchProjects();
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-5 mb-8" data-testid="iabois-panel">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-display text-lg flex items-center gap-2" style={{ color: 'var(--kdm-bleu-logistique)' }}>
          <TreePine size={18} style={{ color: '#6FA82E' }} />
          {i18n.t('adm.iabois_title')}
        </h2>
        <button
          type="button"
          onClick={syncNow}
          disabled={syncing}
          data-testid="iabois-sync-btn"
          className="btn-ghost h-9 px-4 rounded-lg inline-flex items-center gap-2 text-sm"
        >
          {syncing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          {i18n.t('adm.iabois_sync')}
        </button>
      </div>
      <p className="text-xs opacity-60 mb-4">{i18n.t('adm.iabois_subtitle')}</p>
      {projects.length === 0 ? (
        <p className="text-sm opacity-50 text-center py-4" data-testid="iabois-empty">{i18n.t('adm.iabois_empty')}</p>
      ) : (
        <div className="divide-y divide-white/5">
          {projects.map((p) => (
            <div key={p.id} className="flex items-center justify-between gap-3 py-2.5" data-testid={`iabois-project-${p.id}`}>
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{p.title}</p>
                <p className="text-xs opacity-50">{p.client || '—'} · {fmtDate(p.imported_at)}</p>
              </div>
              {p.status === 'NEW' && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0" style={{ color: '#6FA82E', background: '#6FA82E18' }}>
                  {i18n.t('adm.iabois_new')}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
