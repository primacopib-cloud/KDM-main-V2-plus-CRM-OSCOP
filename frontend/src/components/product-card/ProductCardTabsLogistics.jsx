import React from 'react';
import {
  Package, Tag, Building2, MapPin, Scale, Ruler, Thermometer,
  Clock, Shield, FileText, Truck, Box, Leaf, Award, AlertTriangle,
  ChevronDown, ChevronUp, ExternalLink, Download, Info, Zap, Wrench,
  Droplets, Flame, Globe, Calendar, CheckCircle2, XCircle, Star
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { TabsContent } from '../ui/tabs';
import Barcode from 'react-barcode';
import {
  CountryFlag, formatCurrency, getCategoryLabel, getStatusBadge,
  getTemperatureLabel, Section, DataRow,
} from './productCardUtils';

export const LogisticsTab = ({ product }) => (
        <TabsContent value="logistics" className="space-y-4 mt-4">
          {/* Stock */}
          {product.stock && (
            <Section title="Stock" icon={Box}>
              <div className="grid sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                  <p className="text-3xl font-bold text-emerald-400">{product.stock.quantity_available}</p>
                  <p className="text-sm text-white/60">Disponible</p>
                </div>
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-center">
                  <p className="text-3xl font-bold text-amber-400">{product.stock.quantity_reserved}</p>
                  <p className="text-sm text-white/60">Réservé</p>
                </div>
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-center">
                  <p className="text-3xl font-bold text-blue-400">{product.stock.quantity_incoming}</p>
                  <p className="text-sm text-white/60">En commande</p>
                </div>
              </div>
            </Section>
          )}
          
          {/* Logistique */}
          {product.logistics && (
            <Section title="Transport & Livraison" icon={Truck}>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <DataRow label="Délai standard" value={`${product.logistics.lead_time_days} jours`} icon={Clock} />
                  <DataRow label="Qté min commande" value={product.logistics.min_order_quantity} />
                  <DataRow label="Multiple commande" value={product.logistics.order_multiple} />
                  <DataRow label="Code douanier" value={product.logistics.customs_code} />
                </div>
                <div className="space-y-2">
                  {product.logistics.is_fragile && (
                    <div className="flex items-center gap-2 text-amber-400">
                      <AlertTriangle className="w-4 h-4" />
                      <span>Produit fragile</span>
                    </div>
                  )}
                  {product.logistics.requires_adr && (
                    <div className="flex items-center gap-2 text-red-400">
                      <Flame className="w-4 h-4" />
                      <span>Transport ADR requis</span>
                    </div>
                  )}
                  {product.logistics.is_stackable && (
                    <div className="flex items-center gap-2 text-emerald-400">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Gerbage autorisé</span>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Zones */}
              {product.logistics.available_zones?.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-white/70 mb-2">Zones de disponibilité</p>
                  <div className="flex flex-wrap gap-2">
                    {product.logistics.available_zones.map((z) => (
                      <Badge key={`zone-${z}`} className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">{z}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </Section>
          )}
        </TabsContent>
);

export const ComplianceTab = ({ product }) => (
        <TabsContent value="compliance" className="space-y-4 mt-4">
          {product.compliance && (
            <Section title="Conformité & Certifications" icon={Shield}>
              <div className="grid sm:grid-cols-2 gap-6">
                {/* Marquages */}
                <div>
                  <p className="text-sm font-medium text-white/70 mb-3">Marquages</p>
                  <div className="space-y-2">
                    <div className={`flex items-center gap-2 ${product.compliance.ce_marking ? 'text-emerald-400' : 'text-white/30'}`}>
                      {product.compliance.ce_marking ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                      <span>Marquage CE</span>
                    </div>
                    <div className={`flex items-center gap-2 ${product.compliance.nf_marking ? 'text-emerald-400' : 'text-white/30'}`}>
                      {product.compliance.nf_marking ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                      <span>Marque NF</span>
                    </div>
                  </div>
                </div>
                
                {/* Certifications */}
                <div>
                  <p className="text-sm font-medium text-white/70 mb-3">Certifications</p>
                  <div className="space-y-2">
                    {product.compliance.organic_certified && (
                      <div className="flex items-center gap-2 text-green-400">
                        <Leaf className="w-4 h-4" />
                        <span>Bio {product.compliance.organic_label && `(${product.compliance.organic_label})`}</span>
                      </div>
                    )}
                    {product.compliance.haccp_compliant && (
                      <div className="flex items-center gap-2 text-emerald-400">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>HACCP</span>
                      </div>
                    )}
                    {product.compliance.reach_compliant && (
                      <div className="flex items-center gap-2 text-blue-400">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>REACH</span>
                      </div>
                    )}
                    {product.compliance.rohs_compliant && (
                      <div className="flex items-center gap-2 text-purple-400">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>RoHS</span>
                      </div>
                    )}
                    {product.compliance.fsc_certified && (
                      <div className="flex items-center gap-2 text-green-400">
                        <Leaf className="w-4 h-4" />
                        <span>FSC</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Classe de danger */}
              {product.compliance.hazard_class && product.compliance.hazard_class !== 'none' && (
                <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                  <div className="flex items-center gap-2 text-red-400">
                    <AlertTriangle className="w-5 h-5" />
                    <span className="font-semibold">Classe de danger: {product.compliance.hazard_class}</span>
                  </div>
                </div>
              )}
            </Section>
          )}
        </TabsContent>
);

export const DocumentsTab = ({ product }) => (
        <TabsContent value="documents" className="space-y-4 mt-4">
          <Section title="Documents" icon={FileText}>
            <div className="grid sm:grid-cols-2 gap-4">
              {product.media?.technical_sheet_url && (
                <a 
                  href={product.media.technical_sheet_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.04] transition-colors flex items-center gap-3"
                >
                  <FileText className="w-8 h-8 text-blue-400" />
                  <div className="flex-1">
                    <p className="font-medium text-white">Fiche technique</p>
                    <p className="text-sm text-white/50">PDF</p>
                  </div>
                  <Download className="w-5 h-5 text-white/40" />
                </a>
              )}
              {product.media?.user_manual_url && (
                <a 
                  href={product.media.user_manual_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.04] transition-colors flex items-center gap-3"
                >
                  <FileText className="w-8 h-8 text-purple-400" />
                  <div className="flex-1">
                    <p className="font-medium text-white">Manuel utilisateur</p>
                    <p className="text-sm text-white/50">PDF</p>
                  </div>
                  <Download className="w-5 h-5 text-white/40" />
                </a>
              )}
              {product.compliance?.safety_data_sheet_url && (
                <a 
                  href={product.compliance.safety_data_sheet_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.04] transition-colors flex items-center gap-3"
                >
                  <FileText className="w-8 h-8 text-amber-400" />
                  <div className="flex-1">
                    <p className="font-medium text-white">Fiche de données sécurité</p>
                    <p className="text-sm text-white/50">PDF</p>
                  </div>
                  <Download className="w-5 h-5 text-white/40" />
                </a>
              )}
              {(!product.media?.technical_sheet_url && !product.media?.user_manual_url && !product.compliance?.safety_data_sheet_url) && (
                <div className="col-span-2 text-center py-8 text-white/50">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Aucun document disponible</p>
                </div>
              )}
            </div>
          </Section>
        </TabsContent>
);

