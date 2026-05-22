import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, Scale, Building2, CreditCard, Truck, Shield, Handshake, CheckCircle2, XCircle, Download, ChevronRight, Leaf, Package, FileSignature, Route } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { partners } from '../data/mock';
import { BreadcrumbPill } from '../components/Breadcrumb';
import { 
  cgvKdmarcheContent, 
  cgOscopContent, 
  conventionContent,
  charteESSContent,
  annexeLogiscopContent,
  contratTransportLogiscopContent,
  annexeTourneesESSContent,
  auditComplianceTable,
  replaceVariables, 
  legalVariables,
  getDocumentById,
  allLegalDocuments
} from '../data/legalDocuments';

// Render markdown-like content
const renderContent = (content) => {
  const processedContent = replaceVariables(content);
  
  return processedContent.split('\n').map((line, idx) => {
    // Bold text
    const boldRegex = /\*\*(.+?)\*\*/g;
    let processedLine = line.replace(boldRegex, '<strong class="text-white/95 font-semibold">$1</strong>');
    
    // List items with dash
    if (line.trim().startsWith('-') || line.trim().startsWith('—')) {
      return (
        <li key={idx} className="ml-4 text-white/70 text-sm leading-relaxed list-none flex items-start gap-2 mb-1.5">
          <ChevronRight className="w-3 h-3 mt-1 text-white/40 flex-shrink-0" />
          <span dangerouslySetInnerHTML={{ __html: processedLine.replace(/^[-—]\s*/, '') }} />
        </li>
      );
    }
    
    // Empty line
    if (line.trim() === '') {
      return <div key={idx} className="h-2" />;
    }
    
    return (
      <p key={idx} className="text-white/70 text-sm leading-relaxed mb-2" 
         dangerouslySetInnerHTML={{ __html: processedLine }} />
    );
  });
};

// Document Section Component
const DocumentSection = ({ number, title, content, highlight, accentColor }) => (
  <div className={`mb-8 last:mb-0 ${highlight ? 'relative' : ''}`}>
    {highlight && (
      <div 
        className="absolute -left-4 top-0 bottom-0 w-1 rounded-full"
        style={{ background: `linear-gradient(180deg, ${accentColor}, transparent)` }}
      />
    )}
    <div className="flex items-start gap-3 mb-3">
      <div 
        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ background: highlight ? `${accentColor}30` : `${accentColor}15` }}
      >
        <span className="font-bold text-sm" style={{ color: accentColor }}>{number}</span>
      </div>
      <h3 className={`text-base font-semibold pt-1 ${highlight ? 'text-white' : 'text-white/90'}`}>
        {title}
        {highlight && (
          <span className="ml-2 text-xs px-2 py-0.5 rounded-full" style={{ background: `${accentColor}25`, color: accentColor }}>
            Clause clé
          </span>
        )}
      </h3>
    </div>
    <div className={`ml-11 ${highlight ? 'p-4 rounded-xl border' : ''}`}
         style={highlight ? { 
           background: `linear-gradient(135deg, ${accentColor}08, ${accentColor}03)`,
           borderColor: `${accentColor}25`
         } : {}}>
      {renderContent(content)}
    </div>
  </div>
);

// Parties Card Component for Convention
const PartiesCard = ({ parties }) => {
  const kdm = parties.kdmarche;
  const osc = parties.oscop;
  
  return (
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div className="p-4 rounded-xl bg-[#D9B35A]/5 border border-[#D9B35A]/15">
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="w-4 h-4 text-[#D9B35A]" />
          <h4 className="text-sm font-semibold text-[#D9B35A] uppercase tracking-wider">KDMARCHE</h4>
        </div>
        <div className="space-y-1 text-sm text-white/70">
          <p><span className="text-white/50">Dénomination :</span> <strong className="text-white/90">{replaceVariables(kdm.name)}</strong></p>
          <p><span className="text-white/50">Forme :</span> {replaceVariables(kdm.form)}</p>
          <p><span className="text-white/50">SIRET :</span> {replaceVariables(kdm.siret)}</p>
          <p><span className="text-white/50">Siège :</span> {replaceVariables(kdm.address)}</p>
          <p><span className="text-white/50">Représentée par :</span> {replaceVariables(kdm.rep_name)}, {replaceVariables(kdm.rep_title)}</p>
        </div>
      </div>
      <div className="p-4 rounded-xl bg-[#57D19A]/5 border border-[#57D19A]/15">
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="w-4 h-4 text-[#57D19A]" />
          <h4 className="text-sm font-semibold text-[#57D19A] uppercase tracking-wider">O'SCOP</h4>
        </div>
        <div className="space-y-1 text-sm text-white/70">
          <p><span className="text-white/50">Dénomination :</span> <strong className="text-white/90">{replaceVariables(osc.name)}</strong></p>
          <p><span className="text-white/50">Forme :</span> {replaceVariables(osc.form)}</p>
          <p><span className="text-white/50">SIRET :</span> {replaceVariables(osc.siret)}</p>
          <p><span className="text-white/50">Siège :</span> {replaceVariables(osc.address)}</p>
          <p><span className="text-white/50">Représentée par :</span> {replaceVariables(osc.rep_name)}, {replaceVariables(osc.rep_title)}</p>
        </div>
      </div>
    </div>
  );
};

// Audit Compliance Table Component
const AuditTable = () => (
  <div className="mt-8 p-5 rounded-2xl bg-white/[0.02] border border-white/[0.08]">
    <h3 className="text-lg font-semibold text-white/90 mb-4 flex items-center gap-2">
      <Shield className="w-5 h-5 text-[#8B5CF6]" />
      {auditComplianceTable.title}
    </h3>
    
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10">
            <th className="text-left py-2 px-3 text-white/60 font-medium">{auditComplianceTable.headers[0]}</th>
            <th className="text-center py-2 px-3 text-[#D9B35A] font-medium">{auditComplianceTable.headers[1]}</th>
            <th className="text-center py-2 px-3 text-[#57D19A] font-medium">{auditComplianceTable.headers[2]}</th>
          </tr>
        </thead>
        <tbody>
          {auditComplianceTable.rows.map((row, idx) => (
            <tr key={idx} className="border-b border-white/5">
              <td className="py-2.5 px-3 text-white/80">{row.element}</td>
              <td className="py-2.5 px-3 text-center">
                {row.kdmarche ? (
                  <CheckCircle2 className="w-5 h-5 text-[#D9B35A] mx-auto" />
                ) : (
                  <XCircle className="w-5 h-5 text-white/20 mx-auto" />
                )}
              </td>
              <td className="py-2.5 px-3 text-center">
                {row.oscop ? (
                  <CheckCircle2 className="w-5 h-5 text-[#57D19A] mx-auto" />
                ) : (
                  <XCircle className="w-5 h-5 text-white/20 mx-auto" />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    
    <div className="mt-4 p-4 rounded-xl bg-[#8B5CF6]/8 border border-[#8B5CF6]/20">
      <p className="text-xs uppercase tracking-wider text-[#8B5CF6] font-semibold mb-2">Phrase d'audit officielle</p>
      <p className="text-sm text-white/80 italic leading-relaxed">
        {auditComplianceTable.officialPhrase}
      </p>
    </div>
  </div>
);

// Full Document Component
const LegalDocument = ({ document }) => {
  const processedVersion = replaceVariables(document.version);
  const processedDate = replaceVariables(document.dateEffet);
  const processedRef = replaceVariables(document.reference);
  const accentColor = document.accentColor || '#D9B35A';
  
  return (
    <div className="space-y-6">
      {/* Document Header */}
      <div 
        className="p-6 rounded-2xl border"
        style={{
          background: `linear-gradient(135deg, ${accentColor}08, transparent)`,
          borderColor: `${accentColor}20`
        }}
      >
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-2xl font-bold mb-2" style={{ color: accentColor }}>
              {document.title}
            </h2>
            <p className="text-white/60 text-sm">{document.subtitle}</p>
          </div>
          <Button 
            variant="outline" 
            size="sm"
            className="text-xs border-white/10 hover:bg-white/5"
            onClick={() => window.print()}
          >
            <Download className="w-3.5 h-3.5 mr-1.5" />
            Télécharger PDF
          </Button>
        </div>
        <div className="flex flex-wrap gap-3 mt-4 text-xs">
          <span className="px-3 py-1.5 rounded-full bg-white/[0.04] text-white/70 border border-white/[0.06]">
            Version : <span className="text-white/90">{processedVersion}</span>
          </span>
          <span className="px-3 py-1.5 rounded-full bg-white/[0.04] text-white/70 border border-white/[0.06]">
            Date d'effet : <span className="text-white/90">{processedDate}</span>
          </span>
          <span className="px-3 py-1.5 rounded-full bg-white/[0.04] text-white/70 border border-white/[0.06]">
            Référence : <span className="text-white/90 font-mono">{processedRef}</span>
          </span>
        </div>
      </div>
      
      {/* Parties for Convention only (has kdmarche/oscop structure) */}
      {document.parties && document.parties.kdmarche && document.parties.oscop && (
        <PartiesCard parties={document.parties} />
      )}
      
      {/* Sections */}
      <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.08]">
        {document.sections.map((section, idx) => (
          <DocumentSection 
            key={idx}
            number={section.number}
            title={section.title}
            content={section.content}
            highlight={section.highlight}
            accentColor={accentColor}
          />
        ))}
      </div>
      
      {/* Audit Table for Convention */}
      {document.id === 'convention' && <AuditTable />}
      
      {/* Official Clause for Charte ESS */}
      {document.id === 'charte-ess' && document.officialClause && (
        <div className="mt-6 p-5 rounded-2xl bg-[#10B981]/8 border border-[#10B981]/20">
          <p className="text-xs uppercase tracking-wider text-[#10B981] font-semibold mb-3 flex items-center gap-2">
            <Leaf className="w-4 h-4" />
            Clause officielle (affichée dans l'onboarding)
          </p>
          <p className="text-base text-white/90 italic leading-relaxed font-medium">
            {document.officialClause}
          </p>
        </div>
      )}
    </div>
  );
};

export default function LegalPage() {
  const { docId } = useParams();
  const navigate = useNavigate();
  
  // Determine active tab based on URL parameter
  const getInitialTab = () => {
    if (docId === 'cg-oscop') return 'oscop';
    if (docId === 'convention') return 'convention';
    if (docId === 'charte-ess') return 'charte-ess';
    if (docId === 'annexe-logiscop') return 'logiscop';
    if (docId === 'contrat-transport') return 'transport';
    if (docId === 'annexe-ess-route' || docId === 'annexe-tournees-ess') return 'ess-route';
    return 'kdmarche';
  };
  
  const [activeTab, setActiveTab] = useState(getInitialTab());
  
  // Update tab when URL changes
  useEffect(() => {
    setActiveTab(getInitialTab());
  }, [docId]);
  
  // Handle tab change
  const handleTabChange = (value) => {
    setActiveTab(value);
    const routes = {
      'kdmarche': '/legal/cgv-kdmarche',
      'oscop': '/legal/cg-oscop',
      'convention': '/legal/convention',
      'charte-ess': '/legal/charte-ess',
      'logiscop': '/legal/annexe-logiscop',
      'transport': '/legal/contrat-transport',
      'ess-route': '/legal/annexe-ess-route'
    };
    navigate(routes[value] || '/legal/cgv-kdmarche');
  };
  
  return (
    <div 
      className="min-h-screen text-white"
      style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}
    >
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(255,253,247,0.96)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(212,175,55,0.32)'
        }}
      >
        <div className="max-w-[1000px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Retour</span>
            </Link>
            <div className="flex items-center gap-2">
              <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-8 w-auto object-contain" />
              <span className="text-white/30 text-xs">×</span>
              <img src={partners.oscop.logo} alt="O'SCOP" className="h-5 w-auto object-contain" />
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4 text-[#D9B35A]" />
            <span className="text-sm text-white/70">Documents juridiques</span>
          </div>
        </div>
      </header>

      <div className="max-w-[1000px] mx-auto px-5 py-8">
        {/* Breadcrumb */}
        <div className="mb-6">
          <BreadcrumbPill />
        </div>

        {/* Page Title */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold mb-2">Conditions Générales & Convention</h1>
          <p className="text-white/60">
            Documents contractuels régissant les relations B2B — Centrale d'achats ESS
          </p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-6">
          <TabsList className="grid grid-cols-7 w-full max-w-5xl mx-auto bg-white/[0.04] border border-white/[0.08] p-1 h-auto">
            <TabsTrigger 
              value="kdmarche"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A] flex items-center gap-1 py-2.5 text-xs sm:text-sm"
              data-testid="tab-cgv-kdmarche"
            >
              <Truck className="w-4 h-4" />
              <span className="hidden lg:inline">CGV</span> KDM
            </TabsTrigger>
            <TabsTrigger 
              value="oscop"
              className="data-[state=active]:bg-[#57D19A]/20 data-[state=active]:text-[#57D19A] flex items-center gap-1 py-2.5 text-xs sm:text-sm"
              data-testid="tab-cg-oscop"
            >
              <CreditCard className="w-4 h-4" />
              <span className="hidden lg:inline">CG</span> O'SCOP
            </TabsTrigger>
            <TabsTrigger 
              value="convention"
              className="data-[state=active]:bg-[#8B5CF6]/20 data-[state=active]:text-[#8B5CF6] flex items-center gap-1 py-2.5 text-xs sm:text-sm"
              data-testid="tab-convention"
            >
              <Handshake className="w-4 h-4" />
              <span className="hidden lg:inline">Conv.</span>
              <span className="lg:hidden">Conv</span>
            </TabsTrigger>
            <TabsTrigger 
              value="charte-ess"
              className="data-[state=active]:bg-[#10B981]/20 data-[state=active]:text-[#10B981] flex items-center gap-1 py-2.5 text-xs sm:text-sm"
              data-testid="tab-charte-ess"
            >
              <Leaf className="w-4 h-4" />
              <span className="hidden lg:inline">Charte</span> ESS
            </TabsTrigger>
            <TabsTrigger 
              value="logiscop"
              className="data-[state=active]:bg-[#8B5CF6]/20 data-[state=active]:text-[#8B5CF6] flex items-center gap-1 py-2.5 text-xs sm:text-sm"
              data-testid="tab-logiscop"
            >
              <Package className="w-4 h-4" />
              <span className="hidden lg:inline">LOGI'</span>SCOP
            </TabsTrigger>
            <TabsTrigger 
              value="transport"
              className="data-[state=active]:bg-[#F59E0B]/20 data-[state=active]:text-[#F59E0B] flex items-center gap-1 py-2.5 text-xs sm:text-sm"
              data-testid="tab-contrat-transport"
            >
              <FileSignature className="w-4 h-4" />
              <span className="hidden lg:inline">Contrat</span> Tr.
            </TabsTrigger>
            <TabsTrigger 
              value="ess-route"
              className="data-[state=active]:bg-[#10B981]/20 data-[state=active]:text-[#10B981] flex items-center gap-1 py-2.5 text-xs sm:text-sm"
              data-testid="tab-ess-route"
            >
              <Route className="w-4 h-4" />
              <span className="hidden lg:inline">Tournées</span> ESS
            </TabsTrigger>
          </TabsList>

          <TabsContent value="kdmarche" data-testid="content-cgv-kdmarche">
            <LegalDocument document={cgvKdmarcheContent} />
          </TabsContent>

          <TabsContent value="oscop" data-testid="content-cg-oscop">
            <LegalDocument document={cgOscopContent} />
          </TabsContent>

          <TabsContent value="convention" data-testid="content-convention">
            <LegalDocument document={conventionContent} />
          </TabsContent>
          
          <TabsContent value="charte-ess" data-testid="content-charte-ess">
            <LegalDocument document={charteESSContent} />
          </TabsContent>

          <TabsContent value="logiscop" data-testid="content-logiscop">
            <LegalDocument document={annexeLogiscopContent} />
            {/* Tarification LOGI'SCOP */}
            {annexeLogiscopContent.tarification && (
              <div className="mt-8 p-6 rounded-2xl bg-white/[0.02] border border-white/[0.08]">
                <h3 className="text-lg font-semibold text-white/90 mb-4 flex items-center gap-2">
                  <Package className="w-5 h-5 text-[#8B5CF6]" />
                  {annexeLogiscopContent.tarification.title}
                </h3>
                <p className="text-sm text-white/60 mb-4">{annexeLogiscopContent.tarification.description}</p>
                
                {/* Zones Rates Table */}
                <div className="overflow-x-auto mb-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="text-left py-2 px-3 text-white/60 font-medium">Zone</th>
                        <th className="text-center py-2 px-3 text-white/60 font-medium">Base</th>
                        <th className="text-center py-2 px-3 text-white/60 font-medium">€/kg</th>
                        <th className="text-center py-2 px-3 text-white/60 font-medium">€/m³</th>
                      </tr>
                    </thead>
                    <tbody>
                      {annexeLogiscopContent.tarification.zones.map((zone, idx) => (
                        <tr key={idx} className="border-b border-white/5">
                          <td className="py-2.5 px-3">
                            <span className="text-white/80">{zone.name}</span>
                            <span className="ml-2 text-xs text-white/40">({zone.code})</span>
                          </td>
                          <td className="py-2.5 px-3 text-center text-[#8B5CF6] font-medium">{zone.base}</td>
                          <td className="py-2.5 px-3 text-center text-white/70">{zone.perKg}</td>
                          <td className="py-2.5 px-3 text-center text-white/70">{zone.perM3}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Supplements */}
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-[#8B5CF6]/5 border border-[#8B5CF6]/15">
                    <h4 className="text-sm font-semibold text-[#8B5CF6] mb-3">Suppléments créneau</h4>
                    <div className="space-y-2">
                      {annexeLogiscopContent.tarification.supplements.map((sup, idx) => (
                        <div key={idx} className="flex justify-between text-sm">
                          <span className="text-white/70">{sup.label}</span>
                          <span className="text-white/90 font-medium">{sup.amount}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08]">
                    <h4 className="text-sm font-semibold text-white/80 mb-3">Frais de préparation</h4>
                    <div className="space-y-2">
                      {annexeLogiscopContent.tarification.preparation.map((prep, idx) => (
                        <div key={idx} className="flex justify-between text-sm">
                          <span className="text-white/60">{prep.label}</span>
                          <span className="text-white/80">{prep.amount}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <p className="mt-4 text-xs text-white/50 italic">{annexeLogiscopContent.tarification.tvaNote}</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="transport" data-testid="content-contrat-transport">
            <LegalDocument document={contratTransportLogiscopContent} />
            
            {/* Disclaimer box */}
            <div className="mt-6 p-5 rounded-2xl bg-[#F59E0B]/8 border border-[#F59E0B]/20">
              <p className="text-xs uppercase tracking-wider text-[#F59E0B] font-semibold mb-3 flex items-center gap-2">
                <FileSignature className="w-4 h-4" />
                Clause affichée au checkout
              </p>
              <p className="text-base text-white/90 italic leading-relaxed font-medium">
                {contratTransportLogiscopContent.disclaimer}
              </p>
            </div>

            {/* Parties info */}
            {contratTransportLogiscopContent.parties && (
              <div className="mt-6 grid md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-[#8B5CF6]/5 border border-[#8B5CF6]/15">
                  <h4 className="text-sm font-semibold text-[#8B5CF6] mb-3 flex items-center gap-2">
                    <Truck className="w-4 h-4" />
                    Transporteur
                  </h4>
                  <div className="space-y-1.5 text-sm">
                    <p className="text-white/90 font-medium">{contratTransportLogiscopContent.parties.transporteur.name}</p>
                    <p className="text-white/60">{contratTransportLogiscopContent.parties.transporteur.form}</p>
                    <p className="text-white/50 text-xs">{contratTransportLogiscopContent.parties.transporteur.role}</p>
                  </div>
                </div>
                <div className="p-4 rounded-xl bg-[#F59E0B]/5 border border-[#F59E0B]/15">
                  <h4 className="text-sm font-semibold text-[#F59E0B] mb-3 flex items-center gap-2">
                    <Building2 className="w-4 h-4" />
                    Client B2B
                  </h4>
                  <div className="space-y-1.5 text-sm">
                    <p className="text-white/90 font-medium">{replaceVariables(contratTransportLogiscopContent.parties.client.name)}</p>
                    <p className="text-white/60">{contratTransportLogiscopContent.parties.client.role}</p>
                    <p className="text-white/50 text-xs">Identifié dans la commande</p>
                  </div>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="ess-route" data-testid="content-ess-route">
            <LegalDocument document={annexeTourneesESSContent} />
            
            {/* Official clause */}
            <div className="mt-6 p-5 rounded-2xl bg-[#10B981]/8 border border-[#10B981]/20">
              <p className="text-xs uppercase tracking-wider text-[#10B981] font-semibold mb-3 flex items-center gap-2">
                <Route className="w-4 h-4" />
                Clause affichée au checkout (Tournées ESS)
              </p>
              <p className="text-base text-white/90 italic leading-relaxed font-medium">
                {annexeTourneesESSContent.officialClause}
              </p>
            </div>

            {/* Tarification ESS Route */}
            {annexeTourneesESSContent.tarification && (
              <div className="mt-8 p-6 rounded-2xl bg-white/[0.02] border border-white/[0.08]">
                <h3 className="text-lg font-semibold text-white/90 mb-4 flex items-center gap-2">
                  <Route className="w-5 h-5 text-[#10B981]" />
                  {annexeTourneesESSContent.tarification.title}
                </h3>
                <p className="text-sm text-white/60 mb-4">{annexeTourneesESSContent.tarification.description}</p>
                
                {/* ESS Benefits */}
                <div className="grid md:grid-cols-3 gap-3 mb-6">
                  {annexeTourneesESSContent.tarification.benefits.map((benefit, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-[#10B981]/5 border border-[#10B981]/15 text-center">
                      <p className="text-xs text-[#10B981] uppercase tracking-wider mb-1">{benefit.label}</p>
                      <p className="text-white/90 font-semibold">{benefit.value}</p>
                    </div>
                  ))}
                </div>
                
                {/* Zones Rates Table */}
                <div className="overflow-x-auto mb-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="text-left py-2 px-3 text-white/60 font-medium">Zone</th>
                        <th className="text-center py-2 px-3 text-white/60 font-medium">Base</th>
                        <th className="text-center py-2 px-3 text-white/60 font-medium">€/kg</th>
                        <th className="text-center py-2 px-3 text-white/60 font-medium">€/carton</th>
                      </tr>
                    </thead>
                    <tbody>
                      {annexeTourneesESSContent.tarification.zones.map((zone, idx) => (
                        <tr key={idx} className="border-b border-white/5">
                          <td className="py-2.5 px-3">
                            <span className="text-white/80">{zone.name}</span>
                            <span className="ml-2 text-xs text-white/40">({zone.code})</span>
                          </td>
                          <td className="py-2.5 px-3 text-center text-[#10B981] font-medium">{zone.base}</td>
                          <td className="py-2.5 px-3 text-center text-white/70">{zone.perKg}</td>
                          <td className="py-2.5 px-3 text-center text-white/70">{zone.perCarton}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <p className="mt-4 text-xs text-white/50 italic">{annexeTourneesESSContent.tarification.tvaNote}</p>
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Footer Note */}
        <div className="mt-12 p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] text-center">
          <p className="text-xs text-white/50">
            Ces documents sont fournis à titre informatif. Pour toute question, contactez-nous à{' '}
            <a href="mailto:juridique@kdmarche-oscop.fr" className="text-[#D9B35A] hover:underline">
              juridique@kdmarche-oscop.fr
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
