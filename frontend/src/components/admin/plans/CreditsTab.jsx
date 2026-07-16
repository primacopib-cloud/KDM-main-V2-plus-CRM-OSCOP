import { Search, Coins } from 'lucide-react';
import { Input } from '../../ui/input';
import { Button } from '../../ui/button';

export const CreditsTab = ({ users, creditSearch, setCreditSearch, onSearch, onAdjust }) => (
  <div data-testid="credits-tab">
    <div className="flex gap-2 mb-4">
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
        <Input
          value={creditSearch}
          onChange={(e) => setCreditSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
          placeholder="Rechercher par email, nom, société..."
          className="pl-9 bg-white/5 border-white/10 text-white"
          data-testid="credit-search-input"
        />
      </div>
      <Button
        onClick={onSearch}
        data-testid="credit-search-btn"
        style={{ background: '#D9B35A', color: '#070A10' }}
      >
        Rechercher
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
            <th className="p-3">Utilisateur</th>
            <th className="p-3">Société</th>
            <th className="p-3">Rôle</th>
            <th className="p-3">Solde crédits</th>
            <th className="p-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.users.map((u) => (
            <tr
              key={u.user_id}
              className="border-t border-white/5 text-white/80"
              data-testid={`user-credit-row-${u.user_id}`}
            >
              <td className="p-3">
                <div className="text-white">{u.email}</div>
                <div className="text-xs text-white/50">
                  {u.first_name || ''} {u.last_name || ''}
                </div>
              </td>
              <td className="p-3">{u.company_name || '—'}</td>
              <td className="p-3">
                <span
                  className="px-2 py-0.5 rounded text-xs"
                  style={{
                    background: 'rgba(217,179,90,0.15)',
                    color: '#D9B35A',
                  }}
                >
                  {u.role || 'buyer'}
                </span>
              </td>
              <td className="p-3">
                <span
                  className="text-lg font-bold"
                  style={{ color: '#D9B35A' }}
                >
                  {u.credits_balance}
                </span>{' '}
                <span className="text-xs text-white/40">crédits</span>
              </td>
              <td className="p-3 text-right">
                <Button
                  onClick={() => onAdjust(u)}
                  data-testid={`adjust-credits-${u.user_id}`}
                  size="sm"
                  variant="outline"
                  className="bg-white/5 border-white/10 text-white hover:bg-white/10"
                >
                  <Coins className="w-3.5 h-3.5 mr-1" /> Ajuster
                </Button>
              </td>
            </tr>
          ))}
          {users.users.length === 0 && (
            <tr>
              <td colSpan={5} className="p-8 text-center text-white/50">
                Aucun utilisateur trouvé
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
    <div className="text-xs text-white/40 mt-2">
      Total: {users.total} utilisateur(s)
    </div>
  </div>
);
