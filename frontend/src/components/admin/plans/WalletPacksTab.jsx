import { Plus, Pencil, Trash2, Eye, EyeOff, Star } from 'lucide-react';
import { Button } from '../../ui/button';
import { ZoneAddonPricingCard } from './ZoneAddonPricingCard';

export const WalletPacksTab = ({ packs, onCreate, onEdit, onDelete, onToggleActive }) => (
  <div data-testid="wallet-packs-tab">
    <ZoneAddonPricingCard />
    <div className="flex items-center justify-between mb-4">
      <p className="text-white/60 text-sm">
        Packs proposés dans « Acheter des crédits » (CREDI&rsquo;SCOP) — achetables par carte via Stripe.
      </p>
      <Button
        onClick={onCreate}
        data-testid="create-wallet-pack-btn"
        style={{ background: '#D9B35A', color: '#070A10' }}
      >
        <Plus className="w-4 h-4 mr-2" /> Nouveau pack
      </Button>
    </div>
    <div
      className="rounded-xl overflow-hidden"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
    >
      <table className="w-full text-sm">
        <thead style={{ background: 'rgba(255,255,255,0.05)' }}>
          <tr className="text-left text-white/60">
            <th className="p-3">Nom</th>
            <th className="p-3">Crédits</th>
            <th className="p-3">Prix</th>
            <th className="p-3">Achats</th>
            <th className="p-3">Statut</th>
            <th className="p-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {packs.map((p) => (
            <tr key={p.id} className="border-t border-white/5 text-white/80" data-testid={`wallet-pack-row-${p.id}`}>
              <td className="p-3">
                <div className="font-medium text-white flex items-center gap-2">
                  {p.name}
                  {p.popular && <Star className="w-3.5 h-3.5 text-[#D9B35A]" />}
                </div>
                {p.description && <div className="text-xs text-white/50">{p.description}</div>}
              </td>
              <td className="p-3 font-semibold text-[#D9B35A]">{p.credits}</td>
              <td className="p-3">{Number(p.price).toFixed(2).replace('.', ',')} €</td>
              <td className="p-3">{p.purchases_count ?? 0}</td>
              <td className="p-3">
                {p.active ? (
                  <span className="text-[#9CFF7A] flex items-center gap-1">
                    <Eye className="w-3.5 h-3.5" /> Visible
                  </span>
                ) : (
                  <span className="text-red-400 flex items-center gap-1">
                    <EyeOff className="w-3.5 h-3.5" /> Masqué
                  </span>
                )}
              </td>
              <td className="p-3 text-right">
                <button
                  onClick={() => onToggleActive(p)}
                  data-testid={`toggle-wallet-pack-${p.id}`}
                  title={p.active ? 'Masquer' : 'Afficher'}
                  className="p-2 rounded hover:bg-white/10 inline-flex"
                >
                  {p.active
                    ? <EyeOff className="w-4 h-4 text-amber-400" />
                    : <Eye className="w-4 h-4 text-[#9CFF7A]" />}
                </button>
                <button
                  onClick={() => onEdit(p)}
                  data-testid={`edit-wallet-pack-${p.id}`}
                  className="p-2 rounded hover:bg-white/10 inline-flex"
                >
                  <Pencil className="w-4 h-4 text-white/70" />
                </button>
                <button
                  onClick={() => onDelete(p)}
                  data-testid={`delete-wallet-pack-${p.id}`}
                  className="p-2 rounded hover:bg-white/10 inline-flex"
                >
                  <Trash2 className="w-4 h-4 text-red-400" />
                </button>
              </td>
            </tr>
          ))}
          {packs.length === 0 && (
            <tr>
              <td colSpan={6} className="p-8 text-center text-white/50">Aucun pack créé</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  </div>
);
