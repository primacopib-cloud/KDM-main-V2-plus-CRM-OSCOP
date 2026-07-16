import i18n from '@/i18n';
import { CheckCircle2, XCircle, Clock, RotateCcw, Loader2 } from 'lucide-react';

const STATUS_BADGE = {
  SUCCESS: { color: '#6FA82E', icon: CheckCircle2 },
  ERROR: { color: '#E64432', icon: XCircle },
  PENDING: { color: '#D9B35A', icon: Clock },
};

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(i18n.language, {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch (_e) {
    return iso;
  }
};

export const ConnectorSyncTable = ({ events, retryingId, onRetry }) => {
  if (!events.length) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center opacity-60" data-testid="connectors-events-empty">
        {i18n.t('adm.conn_no_events')}
      </div>
    );
  }
  return (
    <div className="glass-panel rounded-2xl overflow-hidden" data-testid="connectors-events-table">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase opacity-60 border-b border-white/10">
            <th className="px-4 py-3">{i18n.t('adm.conn_col_date')}</th>
            <th className="px-4 py-3">{i18n.t('adm.conn_col_connector')}</th>
            <th className="px-4 py-3">{i18n.t('adm.conn_col_action')}</th>
            <th className="px-4 py-3">{i18n.t('adm.conn_col_detail')}</th>
            <th className="px-4 py-3">{i18n.t('adm.conn_col_status')}</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {events.map((e) => {
            const badge = STATUS_BADGE[e.status] || STATUS_BADGE.PENDING;
            const Icon = badge.icon;
            return (
              <tr key={e.id} className="border-b border-white/5" data-testid={`sync-event-row-${e.id}`}>
                <td className="px-4 py-3 whitespace-nowrap opacity-70">{fmtDate(e.created_at)}</td>
                <td className="px-4 py-3">{e.connector}</td>
                <td className="px-4 py-3 opacity-80">{e.action}</td>
                <td className="px-4 py-3 max-w-xs">
                  <span className="block truncate opacity-80">{e.detail || '—'}</span>
                  {e.error && <span className="block text-xs truncate" style={{ color: '#E64432' }}>{e.error}</span>}
                </td>
                <td className="px-4 py-3">
                  <span
                    className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{ color: badge.color, background: `${badge.color}18` }}
                  >
                    <Icon size={12} /> {e.status}
                  </span>
                  {e.attempts > 1 && (
                    <span className="block text-[10px] opacity-50 mt-0.5">×{e.attempts}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {e.status === 'ERROR' && (
                    <button
                      type="button"
                      onClick={() => onRetry(e.id)}
                      disabled={retryingId === e.id}
                      data-testid={`sync-event-retry-${e.id}`}
                      className="btn-ghost h-8 px-3 rounded-lg inline-flex items-center gap-1.5 text-xs"
                    >
                      {retryingId === e.id ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
                      {i18n.t('adm.conn_retry')}
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
