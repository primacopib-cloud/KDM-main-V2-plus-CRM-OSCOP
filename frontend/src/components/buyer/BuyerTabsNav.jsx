import i18n from '@/i18n';
import { TabsList, TabsTrigger } from '../ui/tabs';
import { Badge } from '../ui/badge';
import { TrendingUp, Package, FileText, Wallet, Gavel, BrainCircuit } from 'lucide-react';

const cls = 'data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] rounded-lg';

export const BuyerTabsNav = ({ pendingOrders }) => (
  <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1 rounded-xl">
    <TabsTrigger value="dashboard" data-testid="buyer-tab-dashboard" className={cls}>
      <TrendingUp className="w-4 h-4 mr-2" />{i18n.t('buyer.tableau_de_bord')}
    </TabsTrigger>
    <TabsTrigger value="orders" data-testid="buyer-tab-orders" className={cls}>
      <Package className="w-4 h-4 mr-2" />{i18n.t('buyer.commandes')}
      {pendingOrders > 0 && <Badge className="ml-2 bg-amber-500/20 text-amber-400 border-0">{pendingOrders}</Badge>}
    </TabsTrigger>
    <TabsTrigger value="invoices" data-testid="buyer-tab-invoices" className={cls}>
      <FileText className="w-4 h-4 mr-2" />{i18n.t('buyer.factures')}
    </TabsTrigger>
    <TabsTrigger value="wallet" data-testid="buyer-tab-wallet" className={cls}>
      <Wallet className="w-4 h-4 mr-2" />{i18n.t('buyer.wallet')}
    </TabsTrigger>
    <TabsTrigger value="consultations" data-testid="buyer-tab-consultations" className={cls}>
      <Gavel className="w-4 h-4 mr-2" />Consultations
    </TabsTrigger>
    <TabsTrigger value="tools" data-testid="buyer-tab-tools" className={cls}>
      <BrainCircuit className="w-4 h-4 mr-2" />Outils d'achat
    </TabsTrigger>
  </TabsList>
);
