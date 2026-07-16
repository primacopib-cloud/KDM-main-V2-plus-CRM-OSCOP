import {
  Wallet, MapPin, Plus, CreditCard, CheckCircle2, History,
  Lock, Unlock, ChevronRight,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { formatCredits, formatDate, TX_TYPES, ZONE_TYPES } from './walletUtils';

export const WalletOrgTabs = ({
  wallet, ledger, allZones, entitledZones, availableZones,
  onTopupOpen, onZoneClick, onOpenZoneDialog,
}) => (
  <Tabs defaultValue="wallet" className="space-y-6">
    <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1">
      <TabsTrigger
        value="wallet"
        className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
      >
        <Wallet className="w-4 h-4 mr-2" />
        Wallet Org
      </TabsTrigger>
      <TabsTrigger
        value="zones"
        className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
      >
        <MapPin className="w-4 h-4 mr-2" />
        Zones ({entitledZones.length})
      </TabsTrigger>
    </TabsList>

    {/* Wallet Tab */}
    <TabsContent value="wallet" className="space-y-6">
      <div className="grid md:grid-cols-3 gap-4">
        <div className="glass-panel-soft rounded-[18px] p-6 md:col-span-2">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-white/60 mb-2">Solde disponible</p>
              <p className="text-4xl font-bold text-[#D9B35A]">
                {formatCredits(wallet?.balance)}
                <span className="text-lg font-normal text-white/50 ml-2">crédits</span>
              </p>
              {wallet?.pending_balance > 0 && (
                <p className="text-sm text-white/50 mt-1">
                  + {formatCredits(wallet?.pending_balance)} en attente
                </p>
              )}
            </div>
            <Button
              onClick={onTopupOpen}
              className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
            >
              <Plus className="w-4 h-4 mr-2" />
              Recharger
            </Button>
          </div>
        </div>

        <div className="glass-panel-soft rounded-[18px] p-6">
          <p className="text-sm text-white/60 mb-4">Statistiques</p>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-white/70 text-sm">Total crédité</span>
              <span className="font-semibold text-green-400">
                +{formatCredits(wallet?.total_credited || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-white/70 text-sm">Total débité</span>
              <span className="font-semibold text-red-400">
                -{formatCredits(wallet?.total_debited || 0)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Transaction History */}
      <div className="glass-panel-soft rounded-[18px] p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold flex items-center gap-2">
            <History className="w-4 h-4 text-white/50" />
            Historique des transactions
          </h3>
          <Badge variant="outline" className="text-white/50 border-white/20">
            {ledger.length} transactions
          </Badge>
        </div>

        {ledger.length === 0 ? (
          <div className="text-center py-8 text-white/50">
            <CreditCard className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Aucune transaction</p>
          </div>
        ) : (
          <div className="space-y-2">
            {ledger.map((tx, idx) => {
              const typeConfig = TX_TYPES[tx.type] || TX_TYPES.CREDIT;
              const Icon = typeConfig.icon;
              const isCredit = tx.amount > 0;

              return (
                <div
                  key={tx.id || idx}
                  className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isCredit ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                      <Icon className={`w-4 h-4 ${typeConfig.color}`} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white/90">{tx.description || typeConfig.label}</p>
                      <p className="text-xs text-white/50">{formatDate(tx.created_at)}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`font-semibold ${isCredit ? 'text-green-400' : 'text-red-400'}`}>
                      {isCredit ? '+' : ''}{formatCredits(tx.amount)}
                    </p>
                    <p className="text-xs text-white/40">
                      Solde: {formatCredits(tx.balance_after)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </TabsContent>

    {/* Zones Tab */}
    <TabsContent value="zones" className="space-y-6">
      <div className="glass-panel-soft rounded-[18px] p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold flex items-center gap-2">
            <Unlock className="w-4 h-4 text-[#D4AF37]" />
            Zones activées
          </h3>
          <Badge className="bg-[#D4AF37]/20 text-[#D4AF37]">
            {entitledZones.length} zone{entitledZones.length > 1 ? 's' : ''}
          </Badge>
        </div>

        {entitledZones.length === 0 ? (
          <div className="text-center py-8 text-white/50">
            <MapPin className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Aucune zone activée</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4 border-white/10"
              onClick={onOpenZoneDialog}
            >
              <Plus className="w-4 h-4 mr-2" />
              Ajouter une zone
            </Button>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3">
            {entitledZones.map((entitlement, idx) => {
              const zone = allZones.find(z => z.id === entitlement.zone_id) || {};
              const typeConfig = ZONE_TYPES[zone.zone_type] || ZONE_TYPES.OM;

              return (
                <div
                  key={entitlement.id || idx}
                  className="p-4 rounded-xl bg-[#D4AF37]/5 border border-[#D4AF37]/20"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-white/90">{zone.name || entitlement.zone_id}</p>
                      <p className="text-xs text-white/50 mt-1">{zone.code}</p>
                    </div>
                    <Badge className={typeConfig.color}>
                      {typeConfig.label}
                    </Badge>
                  </div>
                  <div className="mt-3 flex items-center gap-2 text-xs text-white/50">
                    <CheckCircle2 className="w-3 h-3 text-[#D4AF37]" />
                    <span>Activée le {formatDate(entitlement.created_at)}</span>
                  </div>
                  {zone.exw_only && (
                    <p className="text-xs text-amber-400 mt-2">
                      ⚠️ EXW uniquement
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {availableZones.length > 0 && (
        <div className="glass-panel-soft rounded-[18px] p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2">
              <Lock className="w-4 h-4 text-white/50" />
              Zones disponibles
            </h3>
            <Badge variant="outline" className="text-white/50 border-white/20">
              {availableZones.length} zone{availableZones.length > 1 ? 's' : ''}
            </Badge>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {availableZones.map(zone => {
              const typeConfig = ZONE_TYPES[zone.zone_type] || ZONE_TYPES.OM;

              return (
                <div
                  key={zone.id}
                  className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.04] transition-colors cursor-pointer"
                  onClick={() => onZoneClick(zone)}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-white/70">{zone.name}</p>
                      <p className="text-xs text-white/40 mt-1">{zone.code}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/30" />
                  </div>
                  <Badge className={`${typeConfig.color} mt-2`}>
                    {typeConfig.label}
                  </Badge>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </TabsContent>
  </Tabs>
);
