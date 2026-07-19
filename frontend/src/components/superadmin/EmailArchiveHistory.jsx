import { useEffect, useState } from 'react';
import { Archive, Loader2, CheckCircle2, XCircle, MinusCircle } from 'lucide-react';
import { API, getAuthHeaders } from '../../services/http';

const RUN_STATUS = {
  SUCCESS: { color: '#7BC94E', icon: CheckCircle2, label: 'Archivé' },
  ERROR: { color: '#F87171', icon: XCircle, label: 'Erreur' },
  EMPTY: { color: '#9CA3AF', icon: MinusCircle, label: 'Vide' },
  GED_DISABLED: { color: '#9CA3AF', icon: MinusCircle, label: 'GED off' },
};

export const EmailArchiveHistory = ({
  refreshKey,
  endpoint = '/admin/email-previews/archive-ged/runs',
  title = 'Archivages GEDESS (auto le 1er du mois)',
  testId = 'email-archive-history',
  unitLabel = 'envois',
}) => {
  const [runs, setRuns] = useState(null);

  useEffect(() => {
    fetch(`${API}${endpoint}`, { headers: getAuthHeaders(), credentials: 'include' })
      .then((r) => (r.ok ? r.json() : { runs: [] }))
      .then((d) => setRuns(d.runs || []))
      .catch(() => setRuns([]));
  }, [refreshKey, endpoint]);

  return (
    <div className="mb-3 pb-3 border-b border-white/10" data-testid={testId}>
      <p className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-white/50 mb-1.5">
        <Archive className="w-3.5 h-3.5" /> {title}
      </p>
      {runs === null ? (
        <div className="flex justify-center py-2"><Loader2 className="w-4 h-4 animate-spin text-[#D9B35A]" /></div>
      ) : runs.length === 0 ? (
        <p className="text-[11px] text-white/40" data-testid={`${testId}-empty`}>
          Aucun archivage effectué pour le moment.
        </p>
      ) : (
        <div className="space-y-1 max-h-36 overflow-y-auto">
          {runs.map((run) => {
            const st = RUN_STATUS[run.status] || RUN_STATUS.ERROR;
            const Icon = st.icon;
            return (
              <div
                key={run.month}
                className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg bg-white/[0.04] text-[11px]"
                data-testid={`${testId}-run-${run.month}`}
                title={run.status === 'ERROR' ? run.error : run.ged_filename || ''}
              >
                <span className="text-white/85 font-medium">{run.month}</span>
                <span className="text-white/45">{run.rows != null ? `${run.rows} ${unitLabel}` : 'PDF'}</span>
                <span
                  className="inline-flex items-center gap-1 font-semibold px-1.5 py-0.5 rounded-full shrink-0"
                  style={{ color: st.color, background: `${st.color}1c` }}
                >
                  <Icon size={10} /> {st.label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
