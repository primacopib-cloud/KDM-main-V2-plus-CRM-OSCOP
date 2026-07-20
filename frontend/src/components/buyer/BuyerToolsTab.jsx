import { TabsContent } from '../ui/tabs';
import { LotComparator } from './LotComparator';
import { FreightSimulator } from './FreightSimulator';
import { DemandForecast } from './DemandForecast';
import { SupplyRisk } from './SupplyRisk';

export const BuyerToolsTab = () => (
  <TabsContent value="tools" className="space-y-4" data-testid="buyer-tools-tab">
    <p className="text-[11px] text-white/40">
      Outils d'intelligence d'achat KDMARCHÉ PRO — préparez vos consultations avec des données objectives.
    </p>
    <LotComparator />
    <FreightSimulator />
    <SupplyRisk />
    <DemandForecast />
  </TabsContent>
);
