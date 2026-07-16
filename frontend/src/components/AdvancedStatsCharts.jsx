import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { 
  TrendingUp, 
  TrendingDown, 
  ShoppingCart, 
  Users, 
  Package, 
  MapPin,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { Button } from './ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Color palette for charts
const COLORS = ['#D9B35A', '#D4AF37', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444', '#EC4899', '#14B8A6'];

// Custom tooltip component
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  
  return (
    <div className="bg-[#0A0F18] border border-white/10 rounded-lg p-3 shadow-xl">
      <p className="text-white/60 text-xs mb-2">{label}</p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2 text-sm">
          <div 
            className="w-2 h-2 rounded-full" 
            style={{ background: entry.color }}
          />
          <span className="text-white/80">{entry.name}:</span>
          <span className="font-semibold text-white">
            {typeof entry.value === 'number' 
              ? entry.value.toLocaleString('fr-FR', { 
                  style: entry.name.includes('CA') || entry.name.includes('revenue') ? 'currency' : 'decimal',
                  currency: 'EUR',
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0
                })
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
};

// Chart Section Component
const ChartSection = ({ title, icon: Icon, color, children, loading }) => (
  <div className="rounded-2xl bg-white/[0.02] border border-white/[0.08] overflow-hidden">
    <div 
      className="px-5 py-3 flex items-center gap-2"
      style={{ background: `${color}08`, borderBottom: `1px solid ${color}15` }}
    >
      <Icon className="w-4 h-4" style={{ color }} />
      <h3 className="font-semibold text-sm" style={{ color }}>{title}</h3>
    </div>
    <div className="p-5">
      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-white/40" />
        </div>
      ) : (
        children
      )}
    </div>
  </div>
);

// Summary Card Component
const SummaryCard = ({ label, value, trend, trendValue, color }) => {
  const isPositive = trend === 'up';
  
  return (
    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
      <p className="text-xs text-white/50 mb-1">{label}</p>
      <p className="text-2xl font-bold" style={{ color }}>{value}</p>
      {trendValue !== undefined && (
        <div className={`flex items-center gap-1 mt-2 text-xs ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          <span>{isPositive ? '+' : ''}{trendValue}%</span>
        </div>
      )}
    </div>
  );
};

export default function AdvancedStatsCharts({ period = 'month' }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/api/superadmin/advanced-stats?period=${period}`);
      if (!response.ok) throw new Error('Failed to fetch stats');
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Error fetching advanced stats:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period]);
  
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value || 0);
  };
  
  if (error) {
    return (
      <div className="rounded-2xl bg-red-500/10 border border-red-500/20 p-6 text-center">
        <p className="text-red-400 mb-4">Erreur de chargement des statistiques</p>
        <Button variant="outline" onClick={fetchStats}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Réessayer
        </Button>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard 
          label="Chiffre d'affaires"
          value={formatCurrency(stats?.summary?.total_revenue)}
          color="#D9B35A"
          trend={stats?.summary?.growth_percent >= 0 ? 'up' : 'down'}
          trendValue={stats?.summary?.growth_percent}
        />
        <SummaryCard 
          label="Commandes"
          value={stats?.summary?.total_orders?.toLocaleString('fr-FR') || '0'}
          color="#3B82F6"
        />
        <SummaryCard 
          label="Panier moyen"
          value={formatCurrency(stats?.summary?.average_basket)}
          color="#D4AF37"
        />
        <SummaryCard 
          label="Nouveaux utilisateurs"
          value={stats?.summary?.total_new_users?.toLocaleString('fr-FR') || '0'}
          color="#8B5CF6"
        />
      </div>
      
      {/* Sales Trend Chart */}
      <ChartSection title="Évolution des ventes" icon={TrendingUp} color="#D9B35A" loading={loading}>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={stats?.charts?.sales_trend || []}>
              <defs>
                <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#D9B35A" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#D9B35A" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis 
                dataKey="period" 
                stroke="rgba(255,255,255,0.3)"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                tickFormatter={(value) => {
                  if (value.includes('-W')) return `S${value.split('-W')[1]}`;
                  if (value.includes('-')) {
                    const parts = value.split('-');
                    return parts.length === 3 ? `${parts[2]}/${parts[1]}` : value;
                  }
                  return value;
                }}
              />
              <YAxis 
                stroke="rgba(255,255,255,0.3)"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                tickFormatter={(value) => `${(value / 1000).toFixed(0)}k€`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey="revenue" 
                stroke="#D9B35A" 
                strokeWidth={2}
                fill="url(#colorRevenue)" 
                name="CA"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </ChartSection>
      
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Products */}
        <ChartSection title="Top 10 Produits" icon={Package} color="#F59E0B" loading={loading}>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={stats?.charts?.top_products || []} 
                layout="vertical"
                margin={{ left: 10, right: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis 
                  type="number" 
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                  tickFormatter={(value) => `${(value / 1000).toFixed(0)}k€`}
                />
                <YAxis 
                  type="category" 
                  dataKey="name" 
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }}
                  width={100}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="revenue" fill="#F59E0B" radius={[0, 4, 4, 0]} name="CA" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartSection>
        
        {/* Sales by Category */}
        <ChartSection title="Ventes par catégorie" icon={ShoppingCart} color="#8B5CF6" loading={loading}>
          <div className="h-72 flex items-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={stats?.charts?.sales_by_category || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="revenue"
                  nameKey="category"
                  label={({ category, percent }) => `${category?.substring(0, 10)} (${(percent * 100).toFixed(0)}%)`}
                  labelLine={{ stroke: 'rgba(255,255,255,0.2)' }}
                >
                  {(stats?.charts?.sales_by_category || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </ChartSection>
      </div>
      
      <div className="grid lg:grid-cols-2 gap-6">
        {/* User Trend */}
        <ChartSection title="Nouveaux utilisateurs" icon={Users} color="#3B82F6" loading={loading}>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats?.charts?.user_trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis 
                  dataKey="period" 
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                  tickFormatter={(value) => {
                    if (value.includes('-W')) return `S${value.split('-W')[1]}`;
                    if (value.includes('-')) {
                      const parts = value.split('-');
                      return parts.length === 3 ? `${parts[2]}/${parts[1]}` : value;
                    }
                    return value;
                  }}
                />
                <YAxis 
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line 
                  type="monotone" 
                  dataKey="new_users" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  dot={{ fill: '#3B82F6', r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Nouveaux"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartSection>
        
        {/* Orders by Zone */}
        <ChartSection title="Commandes par zone" icon={MapPin} color="#D4AF37" loading={loading}>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats?.charts?.orders_by_zone || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis 
                  dataKey="zone_name" 
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis 
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="orders" fill="#D4AF37" radius={[4, 4, 0, 0]} name="Commandes" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartSection>
      </div>
      
      {/* Order Status Distribution */}
      <ChartSection title="Statut des commandes" icon={ShoppingCart} color="#EC4899" loading={loading}>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stats?.charts?.order_status || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis 
                dataKey="status" 
                stroke="rgba(255,255,255,0.3)"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
              />
              <YAxis 
                stroke="rgba(255,255,255,0.3)"
                tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" name="Commandes" radius={[4, 4, 0, 0]}>
                {(stats?.charts?.order_status || []).map((entry, index) => {
                  const statusColors = {
                    'COMPLETED': '#10B981',
                    'DELIVERED': '#10B981',
                    'confirmed': '#3B82F6',
                    'pending': '#F59E0B',
                    'CANCELLED': '#EF4444',
                    'default': '#6B7280'
                  };
                  return (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={statusColors[entry.status] || statusColors.default} 
                    />
                  );
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartSection>
    </div>
  );
}
