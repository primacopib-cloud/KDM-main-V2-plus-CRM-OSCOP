import i18n from '@/i18n';
import { tData } from '@/i18n/tData';
import { Plus, Pencil, Trash2, CheckCircle2, Star, Eye, EyeOff, CalendarClock } from 'lucide-react';
import { Button } from '../../ui/button';
import { formatPrice } from './shared';

const visibilityBadge = (p) => {
  if (p.visible === false) return { label: 'Masqué', bg: 'rgba(255,135,135,0.15)', color: '#FF8787' };
  const now = new Date().toISOString();
  if (p.visible_from && now < p.visible_from) return { label: 'Programmé', bg: 'rgba(122,183,255,0.15)', color: '#7AB7FF' };
  if (p.visible_until && now > p.visible_until) return { label: 'Expiré', bg: 'rgba(255,179,71,0.15)', color: '#FFB347' };
  return null;
};

export const PlansTab = ({ plans, onCreate, onEdit, onDelete, onToggleVisible }) => (
  <div data-testid="plans-tab">
    <div className="flex justify-end mb-4">
      <Button
        onClick={onCreate}
        data-testid="create-plan-btn"
        style={{ background: '#D9B35A', color: '#070A10' }}
      >
        <Plus className="w-4 h-4 mr-2" /> {i18n.t('adm.nouveau_plan')}
      </Button>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {plans.map((p) => (
        <div
          key={p.id}
          className="rounded-2xl p-5 relative"
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: `1px solid ${p.popular ? '#D9B35A' : 'rgba(255,255,255,0.08)'}`,
          }}
          data-testid={`plan-card-${p.slug}`}
        >
          {p.popular && (
            <div
              className="absolute -top-3 right-4 px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1"
              style={{ background: '#D9B35A', color: '#070A10' }}
            >
              <Star className="w-3 h-3" /> {i18n.t('adm.populaire')}
            </div>
          )}
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xs text-white/65">{p.slug}</div>
              <h3 className="text-lg font-bold text-white">{p.name}</h3>
            </div>
            <div
              className="px-2 py-0.5 rounded text-xs"
              style={{
                background: p.active ? 'rgba(154,255,122,0.15)' : 'rgba(255,87,87,0.15)',
                color: p.active ? '#9CFF7A' : '#FF8787',
              }}
            >
              {p.active ? i18n.t('adm.actif') : i18n.t('adm.inactif')}
            </div>
          </div>
          {visibilityBadge(p) && (
            <span
              className="inline-flex items-center gap-1 mt-1.5 px-2 py-0.5 rounded text-[11px]"
              style={{ background: visibilityBadge(p).bg, color: visibilityBadge(p).color }}
              data-testid={`plan-visibility-badge-${p.slug}`}
            >
              <CalendarClock className="w-3 h-3" /> {visibilityBadge(p).label}
              {p.visible !== false && p.visible_from && ` dès le ${p.visible_from.slice(0, 10)}`}
              {p.visible !== false && p.visible_until && ` → ${p.visible_until.slice(0, 10)}`}
            </span>
          )}
          {p.description && (
            <p className="text-white/80 text-sm mt-1">{tData(p.description)}</p>
          )}
          <div className="mt-3">
            <span className="text-3xl font-bold" style={{ color: p.color || '#D9B35A' }}>
              {formatPrice(p.price_cents)}
            </span>
            <span className="text-white/75 text-sm">/ {tData(p.period)}</span>
          </div>
          <div className="text-xs text-white/65 mt-1">
            {i18n.t('adm.plan_meta', { credits: p.default_credits, zones: p.max_zones, users: p.max_users })}
          </div>
          <ul className="space-y-1 mt-3 text-sm text-white/85">
            {(p.features || []).slice(0, 4).map((f) => (
              <li key={`feat-${p.id || p.code}-${f}`} className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" style={{ color: '#D9B35A' }} />
                <span>{tData(f)}</span>
              </li>
            ))}
            {(p.features || []).length > 4 && (
              <li className="text-xs text-white/60">
                {i18n.t('adm.plus_more', { count: p.features.length - 4 })}
              </li>
            )}
          </ul>
          <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-3">
            <div className="text-xs text-white/50">
              {i18n.t('adm.abonnes_count', { count: p.subscribers_count })}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => onToggleVisible(p)}
                data-testid={`toggle-visible-plan-${p.slug}`}
                className="p-2 rounded hover:bg-white/10"
                title={p.visible === false ? 'Afficher sur la page publique' : 'Masquer de la page publique'}
              >
                {p.visible === false
                  ? <EyeOff className="w-4 h-4 text-red-400" />
                  : <Eye className="w-4 h-4 text-white/70" />}
              </button>
              <button
                onClick={() => onEdit(p)}
                data-testid={`edit-plan-${p.slug}`}
                className="p-2 rounded hover:bg-white/10"
                title="Modifier"
              >
                <Pencil className="w-4 h-4 text-white/70" />
              </button>
              <button
                onClick={() => onDelete(p)}
                data-testid={`delete-plan-${p.slug}`}
                className="p-2 rounded hover:bg-white/10"
                title="Supprimer"
              >
                <Trash2 className="w-4 h-4 text-red-400" />
              </button>
            </div>
          </div>
        </div>
      ))}
      {plans.length === 0 && (
        <div className="col-span-full text-center text-white/50 py-12">
          {i18n.t('adm.aucun_plan_cree')}
        </div>
      )}
    </div>
  </div>
);
