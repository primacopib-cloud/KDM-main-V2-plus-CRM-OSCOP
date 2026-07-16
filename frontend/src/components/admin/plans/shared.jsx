export const formatPrice = (cents) => `${(cents / 100).toFixed(2)} €`;

export const StatsCard = ({ icon: Icon, label, value, color = '#D9B35A' }) => (
  <div
    className="p-4 rounded-xl"
    style={{
      background: 'rgba(255,255,255,0.06)',
      border: '1px solid rgba(255,255,255,0.14)',
    }}
  >
    <div className="flex items-center gap-3">
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center"
        style={{ background: `${color}22` }}
      >
        <Icon className="w-5 h-5" style={{ color }} />
      </div>
      <div>
        <div className="text-xs text-white/75">{label}</div>
        <div className="text-2xl font-bold text-white">{value}</div>
      </div>
    </div>
  </div>
);
