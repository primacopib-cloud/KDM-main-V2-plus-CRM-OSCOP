import React from 'react';
import {
  Building2, Clock, Shield, Award, Thermometer, Calendar, CheckCircle2, XCircle, Globe, Factory,
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { TabsContent } from '../ui/tabs';
import { getTemperatureLabel, Section, DataRow } from './productCardUtils';

const Empty = ({ text }) => (
  <p className="text-white/40 text-sm p-4 text-center">{text}</p>
);

export const SupplierTab = ({ product }) => (
  <TabsContent value="supplier" className="space-y-4 mt-4" data-testid="product-tab-supplier">
    <Section title="Fournisseur & Fabricant" icon={Factory}>
      <div className="space-y-2">
        <DataRow label="Vendeur" value={product.vendor_name} icon={Building2} highlight />
        <DataRow label="Fabricant" value={product.manufacturer} />
        <DataRow label="Marque" value={product.brand} />
        <DataRow label="Réf. fabricant" value={product.manufacturer_ref} />
      </div>
      {!product.vendor_name && !product.manufacturer && !product.brand && (
        <Empty text="Informations fournisseur non renseignées" />
      )}
    </Section>
    {product.origin && (
      <Section title="Producteur & Origine" icon={Globe}>
        <div className="space-y-2">
          <DataRow label="Producteur" value={product.origin.producer_name} />
          <DataRow label="Code producteur" value={product.origin.producer_code} />
          <DataRow label="Pays d'origine" value={product.origin.country_name} />
          <DataRow label="Région" value={product.origin.region} />
        </div>
      </Section>
    )}
  </TabsContent>
);

export const DlcTab = ({ product }) => {
  const c = product.conservation;
  return (
    <TabsContent value="dlc" className="space-y-4 mt-4" data-testid="product-tab-dlc">
      <Section title="DLC & Conservation" icon={Calendar}>
        {c ? (
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <DataRow label="Type de date" value={c.dlc_type} highlight />
              <DataRow label="Durée de conservation" value={c.shelf_life_days ? `${c.shelf_life_days} jours` : null} icon={Clock} />
              <DataRow label="Après ouverture" value={c.opened_shelf_life_days ? `${c.opened_shelf_life_days} jours` : null} />
            </div>
            <div className="space-y-2">
              <DataRow label="Température" value={getTemperatureLabel(c.temperature_range)} icon={Thermometer} />
              <DataRow label="Temp. min" value={c.temperature_min_c != null ? `${c.temperature_min_c} °C` : null} />
              <DataRow label="Temp. max" value={c.temperature_max_c != null ? `${c.temperature_max_c} °C` : null} />
            </div>
          </div>
        ) : (
          <Empty text="DLC / conservation non renseignée pour ce produit" />
        )}
        {c?.storage_instructions && (
          <p className="mt-3 p-3 rounded-lg bg-white/[0.04] text-sm text-white/70">{c.storage_instructions}</p>
        )}
      </Section>
    </TabsContent>
  );
};

export const WarrantyTab = ({ product }) => {
  const w = product.warranty;
  return (
    <TabsContent value="warranty" className="space-y-4 mt-4" data-testid="product-tab-warranty">
      <Section title="Garantie" icon={Shield}>
        {w ? (
          <div className="space-y-2">
            <DataRow label="Durée" value={`${w.duration_months} mois`} highlight />
            <DataRow label="Type" value={w.warranty_type} />
            <div className="flex justify-between items-center py-2">
              <span className="text-white/60">Garantie fabricant</span>
              {w.manufacturer_warranty
                ? <span className="flex items-center gap-1.5 text-emerald-400"><CheckCircle2 className="w-4 h-4" /> Oui</span>
                : <span className="flex items-center gap-1.5 text-white/40"><XCircle className="w-4 h-4" /> Non</span>}
            </div>
            {w.coverage && <p className="p-3 rounded-lg bg-white/[0.04] text-sm text-white/70"><b className="text-white/90">Couverture :</b> {w.coverage}</p>}
            {w.exclusions && <p className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-sm text-amber-200/80"><b>Exclusions :</b> {w.exclusions}</p>}
          </div>
        ) : (
          <Empty text="Aucune garantie renseignée pour ce produit" />
        )}
      </Section>
    </TabsContent>
  );
};

const COMPLIANCE_FLAGS = [
  ['ce_marking', 'Marquage CE'], ['nf_marking', 'Marque NF'], ['haccp_compliant', 'HACCP'],
  ['organic_certified', 'Certifié Bio'], ['reach_compliant', 'REACH'], ['rohs_compliant', 'RoHS'],
  ['fsc_certified', 'FSC'],
];

export const NormsTab = ({ product }) => {
  const norms = product.technical_specs?.norms || [];
  const certs = product.technical_specs?.certifications || [];
  const comp = product.compliance || {};
  const activeFlags = COMPLIANCE_FLAGS.filter(([k]) => comp[k]);
  return (
    <TabsContent value="norms" className="space-y-4 mt-4" data-testid="product-tab-norms">
      <Section title="Normes" icon={Award}>
        {norms.length ? (
          <div className="flex flex-wrap gap-2">
            {norms.map((n) => (
              <Badge key={n} className="bg-[#D9B35A]/15 text-[#E9CF8E] border-[#D9B35A]/30">{n}</Badge>
            ))}
          </div>
        ) : (
          <Empty text="Aucune norme renseignée" />
        )}
        {certs.length > 0 && (
          <div className="mt-4">
            <p className="text-sm text-white/60 mb-2">Certifications</p>
            <div className="flex flex-wrap gap-2">
              {certs.map((cName) => (
                <Badge key={cName} variant="outline" className="bg-white/[0.04] border-white/10">{cName}</Badge>
              ))}
            </div>
          </div>
        )}
      </Section>
      {activeFlags.length > 0 && (
        <Section title="Marquages & conformité" icon={Shield}>
          <div className="grid sm:grid-cols-2 gap-2">
            {activeFlags.map(([k, label]) => (
              <span key={k} className="flex items-center gap-2 text-emerald-400 text-sm">
                <CheckCircle2 className="w-4 h-4" /> {label}
              </span>
            ))}
          </div>
        </Section>
      )}
    </TabsContent>
  );
};
