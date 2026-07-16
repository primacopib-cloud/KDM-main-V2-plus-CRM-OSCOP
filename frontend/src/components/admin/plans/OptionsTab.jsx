import i18n from '@/i18n';
import { Plus, Pencil, Trash2, CheckCircle2, XCircle } from 'lucide-react';
import { Button } from '../../ui/button';
import { formatPrice } from './shared';

export const OptionsTab = ({ options, onCreate, onEdit, onDelete }) => (
  <div data-testid="options-tab">
    <div className="flex justify-end mb-4">
      <Button
        onClick={onCreate}
        data-testid="create-option-btn"
        style={{ background: '#D9B35A', color: '#070A10' }}
      >
        <Plus className="w-4 h-4 mr-2" /> {i18n.t('adm.nouvelle_option')}
      </Button>
    </div>
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.08)',
      }}
    >
      <table className="w-full text-sm">
        <thead style={{ background: 'rgba(255,255,255,0.05)' }}>
          <tr className="text-left text-white/60">
            <th className="p-3">{i18n.t('adm.nom')}</th>
            <th className="p-3">{i18n.t('adm.prix_2')}</th>
            <th className="p-3">{i18n.t('adm.credits_inclus')}</th>
            <th className="p-3">{i18n.t('adm.plans_compatibles')}</th>
            <th className="p-3">{i18n.t('adm.statut')}</th>
            <th className="p-3 text-right">{i18n.t('adm.actions')}</th>
          </tr>
        </thead>
        <tbody>
          {options.map((o) => (
            <tr
              key={o.id}
              className="border-t border-white/5 text-white/80"
              data-testid={`option-row-${o.id}`}
            >
              <td className="p-3">
                <div className="font-medium text-white">{o.name}</div>
                {o.description && (
                  <div className="text-xs text-white/50">{o.description}</div>
                )}
              </td>
              <td className="p-3">
                {formatPrice(o.price_cents)} <span className="text-white/40">/ {o.period}</span>
              </td>
              <td className="p-3">{o.credits_included}</td>
              <td className="p-3 text-xs">
                {(o.compatible_plans || []).length === 0
                  ? 'Tous les plans'
                  : o.compatible_plans.join(', ')}
              </td>
              <td className="p-3">
                {o.active ? (
                  <span className="text-[#9CFF7A] flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Active
                  </span>
                ) : (
                  <span className="text-red-400 flex items-center gap-1">
                    <XCircle className="w-3.5 h-3.5" /> Inactive
                  </span>
                )}
              </td>
              <td className="p-3 text-right">
                <button
                  onClick={() => onEdit(o)}
                  data-testid={`edit-option-${o.id}`}
                  className="p-2 rounded hover:bg-white/10 inline-flex"
                >
                  <Pencil className="w-4 h-4 text-white/70" />
                </button>
                <button
                  onClick={() => onDelete(o)}
                  data-testid={`delete-option-${o.id}`}
                  className="p-2 rounded hover:bg-white/10 inline-flex"
                >
                  <Trash2 className="w-4 h-4 text-red-400" />
                </button>
              </td>
            </tr>
          ))}
          {options.length === 0 && (
            <tr>
              <td colSpan={6} className="p-8 text-center text-white/50">
                {i18n.t('adm.aucune_option_creee')}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  </div>
);
