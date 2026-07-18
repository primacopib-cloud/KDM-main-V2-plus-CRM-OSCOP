import i18n from '@/i18n';
import { CheckCircle2, XCircle, Loader2, Activity, PowerOff } from 'lucide-react';

const STATUS_STYLE = {
  OK: { color: '#6FA82E', icon: CheckCircle2 },
  ERROR: { color: '#E64432', icon: XCircle },
  DISABLED: { color: '#9CA3AF', icon: PowerOff },
};

export const ConnectorCard = ({ connector, health, checking, onCheck }) => {
  const status = health?.status;
  const style = STATUS_STYLE[status] || { color: 'var(--kdm-or-metallise)', icon: Activity };
  const Icon = style.icon;

  return (
    <div className="glass-panel rounded-2xl p-5" data-testid={`connector-card-${connector.name}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-lg" style={{ color: '#F7F2E9' }}>
            {connector.label}
          </h3>
          <p className="text-xs opacity-60 mt-1 break-all">{connector.base_url || '—'}</p>
        </div>
        <span
          className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full"
          style={{ color: style.color, background: `${style.color}18`, border: `1px solid ${style.color}40` }}
          data-testid={`connector-status-${connector.name}`}
        >
          <Icon size={13} />
          {status || (connector.enabled ? i18n.t('adm.conn_not_tested') : 'DISABLED')}
        </span>
      </div>
      <p className="text-sm opacity-75 mt-3">{connector.description}</p>
      {health?.error && (
        <p className="text-xs mt-2 p-2 rounded-lg" style={{ color: '#E64432', background: '#E6443212' }}>
          {health.error}
        </p>
      )}
      <button
        type="button"
        onClick={() => onCheck(connector.name)}
        disabled={checking}
        data-testid={`connector-health-btn-${connector.name}`}
        className="btn-ghost h-9 px-4 rounded-lg inline-flex items-center gap-2 mt-4 text-sm"
      >
        {checking ? <Loader2 size={14} className="animate-spin" /> : <Activity size={14} />}
        {i18n.t('adm.conn_test_health')}
      </button>
    </div>
  );
};
