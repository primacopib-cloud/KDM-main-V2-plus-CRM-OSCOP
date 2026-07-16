import { ArrowLeft, FileText, Scale, Building2, CreditCard, Truck, Shield, Handshake, CheckCircle2, XCircle, Download, ChevronRight, Leaf, Package, FileSignature, Route } from 'lucide-react';
import { replaceVariables, auditComplianceTable } from '../../data/legalDocuments';

export const renderContent = (content) => {
  const processedContent = replaceVariables(content);
  
  return processedContent.split('\n').map((line, idx) => {
    // Bold text
    const boldRegex = /\*\*(.+?)\*\*/g;
    let processedLine = line.replace(boldRegex, '<strong class="text-white/95 font-semibold">$1</strong>');
    
    // List items with dash
    if (line.trim().startsWith('-') || line.trim().startsWith('—')) {
      return (
        <li key={`line-${idx}-${line.slice(0, 24)}`} className="ml-4 text-white/70 text-sm leading-relaxed list-none flex items-start gap-2 mb-1.5">
          <ChevronRight className="w-3 h-3 mt-1 text-white/40 flex-shrink-0" />
          <span dangerouslySetInnerHTML={{ __html: processedLine.replace(/^[-—]\s*/, '') }} />
        </li>
      );
    }
    
    // Empty line
    if (line.trim() === '') {
      return <div key={`empty-${idx}`} className="h-2" />;
    }
    
    return (
      <p key={`p-${idx}-${line.slice(0, 24)}`} className="text-white/70 text-sm leading-relaxed mb-2" 
         dangerouslySetInnerHTML={{ __html: processedLine }} />
    );
  });
};

// Document Section Component
export const DocumentSection = ({ number, title, content, highlight, accentColor }) => (
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
export const PartiesCard = ({ parties }) => {
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
      <div className="p-4 rounded-xl bg-[#D4AF37]/5 border border-[#D4AF37]/15">
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="w-4 h-4 text-[#D4AF37]" />
          <h4 className="text-sm font-semibold text-[#D4AF37] uppercase tracking-wider">O&apos;SCOP</h4>
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
export const AuditTable = () => (
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
            <th className="text-center py-2 px-3 text-[#D4AF37] font-medium">{auditComplianceTable.headers[2]}</th>
          </tr>
        </thead>
        <tbody>
          {auditComplianceTable.rows.map((row) => (
            <tr key={`audit-${row.element}`} className="border-b border-white/5">
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
                  <CheckCircle2 className="w-5 h-5 text-[#D4AF37] mx-auto" />
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
      <p className="text-xs uppercase tracking-wider text-[#8B5CF6] font-semibold mb-2">Phrase d&apos;audit officielle</p>
      <p className="text-sm text-white/80 italic leading-relaxed">
        {auditComplianceTable.officialPhrase}
      </p>
    </div>
  </div>
);

// Full Document Component
export const LegalDocument = ({ document }) => {
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
            Date d&apos;effet : <span className="text-white/90">{processedDate}</span>
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
            Clause officielle (affichée dans l&apos;onboarding)
          </p>
          <p className="text-base text-white/90 italic leading-relaxed font-medium">
            {document.officialClause}
          </p>
        </div>
      )}
    </div>
  );
};

