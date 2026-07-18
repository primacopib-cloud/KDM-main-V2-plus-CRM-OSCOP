import i18n from '@/i18n';
import {
  AlertTriangle, AlertCircle, Info, Clock, ShoppingCart, FileSignature,
  Building2, Package, ArrowUpRight, ArrowDownRight,
} from 'lucide-react';

export const formatCurrency = (amount) =>
  new Intl.NumberFormat(i18n.language, { style: 'currency', currency: 'EUR' }).format(amount || 0);

export const StatCard = ({ title, value, subtitle, icon: Icon, trend, trendValue, color = '#D9B35A', size = 'normal' }) => {
  const isPositive = trend === 'up';

  return (
    <div className={`rounded-2xl p-5 bg-white border border-[#E9DCC0] shadow-[0_4px_16px_rgba(76,42,110,0.06)] hover:bg-[#FBF4E4] transition-all ${size === 'large' ? 'col-span-2' : ''}`}>
      <div className="flex justify-between items-start mb-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: `${color}15` }}
        >
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full ${isPositive ? 'bg-green-500/10 text-green-700' : 'bg-red-500/10 text-red-600'}`}>
            {isPositive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {trendValue}
          </div>
        )}
      </div>
      <div className="text-2xl font-bold text-[#4C2A6E] mb-1">{value}</div>
      <div className="text-sm text-[#8A785F]">{title}</div>
      {subtitle && <div className="text-xs text-[#A8977C] mt-1">{subtitle}</div>}
    </div>
  );
};

export const AlertCard = ({ alert }) => {
  const icons = {
    error: AlertTriangle,
    warning: AlertCircle,
    info: Info
  };
  const colors = {
    error: '#EF4444',
    warning: '#F59E0B',
    info: '#3B82F6'
  };
  const Icon = icons[alert.type] || Info;
  const color = colors[alert.type] || '#3B82F6';

  return (
    <div
      className="flex items-start gap-3 p-3 rounded-xl"
      style={{ background: `${color}10`, border: `1px solid ${color}20` }}
    >
      <Icon className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color }} />
      <div>
        <p className="text-sm font-medium text-[#3D2E1E]">{alert.title}</p>
        <p className="text-xs text-[#7A6850]">{alert.message}</p>
      </div>
    </div>
  );
};

export const ActivityItem = ({ activity }) => {
  const icons = {
    order: ShoppingCart,
    signature: FileSignature,
    organization: Building2,
    product: Package
  };
  const colors = {
    order: '#D9B35A',
    signature: '#8B5CF6',
    organization: '#D4AF37',
    product: '#3B82F6'
  };
  const Icon = icons[activity.type] || Clock;
  const color = colors[activity.type] || '#D9B35A';

  return (
    <div className="flex items-center gap-3 py-3 border-b border-[#EDE1C6] last:border-0">
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center"
        style={{ background: `${color}15` }}
      >
        <Icon className="w-4 h-4" style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[#3D2E1E] truncate">{activity.action}</p>
        <p className="text-xs text-[#8A785F]">{activity.details}</p>
      </div>
      <div className="text-xs text-[#A8977C]">
        {activity.timestamp ? new Date(activity.timestamp).toLocaleTimeString(i18n.language, { hour: '2-digit', minute: '2-digit' }) : ''}
      </div>
    </div>
  );
};

export const KPISection = ({ title, icon: Icon, color, children }) => (
  <div className="rounded-2xl bg-white border border-[#E9DCC0] shadow-[0_4px_16px_rgba(76,42,110,0.06)] overflow-hidden">
    <div
      className="px-5 py-3 flex items-center gap-2"
      style={{ background: `${color}08`, borderBottom: `1px solid ${color}15` }}
    >
      <Icon className="w-4 h-4" style={{ color }} />
      <h3 className="font-semibold text-sm" style={{ color }}>{title}</h3>
    </div>
    <div className="p-5">
      {children}
    </div>
  </div>
);
