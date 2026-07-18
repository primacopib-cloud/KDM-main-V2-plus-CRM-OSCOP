import i18n from '@/i18n';
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowLeft, FileText, Download, Eye, Calendar, Tag, Users,
  CheckCircle2, Clock, Archive, ExternalLink, Loader2, Info,
  Scale, Shield, Building2, Handshake
} from 'lucide-react';

import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from '../components/ui/dialog';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '../components/ui/tabs';

import { partners } from '../data/mock';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Document type icons
const DOC_ICONS = {
  'convention': Handshake,
  'cg-oscop': Scale,
  'cgv-kdmarche': Building2,
  'note-preventive': Shield,
};

// Status badges
const STATUS_CONFIG = {
  'DRAFT': { label: 'Brouillon', color: 'bg-gray-500/20 text-gray-400' },
  'PUBLISHED': { label: 'Publié', color: 'bg-green-500/20 text-green-400' },
  'ARCHIVED': { label: 'Archivé', color: 'bg-orange-500/20 text-orange-400' },
};

// Format date
const formatDate = (dateStr) => {
  if (!dateStr) return '---';
  const date = new Date(dateStr);
  return date.toLocaleDateString(i18n.language, {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });
};

export default function DocumentsPage() {
  const [loading, setLoading] = useState(true);
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  // Load documents
  useEffect(() => {
    const loadDocuments = async () => {
      try {
        const response = await fetch(`${API_URL}/api/ged/documents`);
        if (response.ok) {
          const data = await response.json();
          setDocuments(data);
        } else {
          // Fallback to static list
          setDocuments([
            {
              doc_type: 'convention',
              title: 'Convention de partenariat KDMARCHE – O\'SCOP',
              description: 'Centrale d\'achats B2B ESS — Partenariat (séparation stricte des rôles)',
              ref: 'CONV-KDM-OSCOP-2026-001',
              version: '1.0.0',
              status: 'PUBLISHED',
              filename: 'convention-kdmarche-oscop.html',
              tags: ['partenariat', 'b2b', 'ess'],
              audience: ['B2B', 'ADMIN'],
            },
            {
              doc_type: 'cg-oscop',
              title: 'CG O\'SCOP — Accès, Abonnements, CREDI\'SCOP',
              description: 'Conditions générales applicables aux services O\'SCOP (hors marchandises)',
              ref: 'CG-OSCOP-2026-001',
              version: '1.0.0',
              status: 'PUBLISHED',
              filename: 'cg-oscop.html',
              tags: ['cg', 'oscop', 'abonnement'],
              audience: ['B2B', 'PUBLIC'],
            },
            {
              doc_type: 'cgv-kdmarche',
              title: 'CGV KDMARCHE B2B — Marchandises (EXW)',
              description: 'Conditions générales de vente B2B pour les marchandises (Incoterm EXW)',
              ref: 'CGV-KDM-B2B-2026-001',
              version: '1.0.0',
              status: 'PUBLISHED',
              filename: 'cgv-kdmarche-b2b.html',
              tags: ['cgv', 'kdmarche', 'exw'],
              audience: ['B2B', 'PUBLIC'],
            },
            {
              doc_type: 'note-preventive',
              title: 'Note préventive ACPR / DGCCRF',
              description: 'Qualification et prévention de requalification',
              ref: 'NOTE-ACPR-DGCCRF-2026-001',
              version: '1.0.0',
              status: 'PUBLISHED',
              filename: 'note-preventive-acpr-dgccrf.html',
              tags: ['compliance', 'acpr', 'dgccrf'],
              audience: ['ADMIN', 'LEGAL'],
            },
          ]);
        }
      } catch (error) {
        console.error('Error loading documents:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDocuments();
  }, []);

  // Preview document
  const handlePreview = async (doc) => {
    setSelectedDoc(doc);
    setPreviewLoading(true);
    setPreviewOpen(true);

    try {
      const response = await fetch(`${API_URL}/api/ged/documents/${doc.doc_type}/render`);
      if (response.ok) {
        const html = await response.text();
        setPreviewContent(html);
      } else {
        // Fallback to static file
        const staticResponse = await fetch(`/docs/${doc.filename}`);
        if (staticResponse.ok) {
          const html = await staticResponse.text();
          setPreviewContent(html);
        }
      }
    } catch (error) {
      console.error('Error loading preview:', error);
      toast.error('Erreur lors du chargement');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Download document
  const handleDownload = (doc) => {
    // Try API first, fallback to static
    const apiUrl = `${API_URL}/api/ged/documents/${doc.doc_type}/download`;
    const staticUrl = `/docs/${doc.filename}`;
    
    // Use static for simplicity
    const link = document.createElement('a');
    link.href = staticUrl;
    link.download = doc.filename;
    link.click();
    
    toast.success('Téléchargement démarré');
  };

  // Get metadata
  const handleGetMetadata = async (doc) => {
    try {
      const response = await fetch(`${API_URL}/api/ged/documents/${doc.doc_type}/metadata`);
      if (response.ok) {
        const metadata = await response.json();
        console.log('Document metadata:', metadata);
        toast.success('Métadonnées disponibles (voir console)');
      }
    } catch (error) {
      toast.error('Erreur lors du chargement des métadonnées');
    }
  };

  // Group documents by category
  const contractDocs = documents.filter(d => ['convention'].includes(d.doc_type));
  const termsDocs = documents.filter(d => ['cg-oscop', 'cgv-kdmarche'].includes(d.doc_type));
  const complianceDocs = documents.filter(d => ['note-preventive'].includes(d.doc_type));

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }}>
        <Loader2 className="w-8 h-8 animate-spin text-[#D9B35A]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #FBF6EE 0%, #F5EBD8 45%, #FBF6EE 100%)' }} data-testid="documents-page">
      {/* Header */}
      <header 
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(255,253,247,0.86)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(212,175,55,0.32)'
        }}
      >
        <div className="max-w-[1160px] mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2 text-white/60 hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm hidden sm:inline">Accueil</span>
            </Link>
            <div className="flex items-center gap-3">
              <img src={partners.kdmarche.logo} alt="KDMARCHE" className="h-12 w-auto object-contain" />
              <span className="text-white/40">×</span>
              <img src={partners.oscop.logo} alt="O'SCOP" className="h-8 w-auto object-contain" />
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-[1160px] mx-auto px-5 py-8">
        {/* Title */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Documents légaux</h1>
          <p className="text-white/60">
            Consultez et téléchargez les documents contractuels de la plateforme KDMARCHE × O'SCOP
          </p>
        </div>

        {/* Info banner */}
        <div className="mb-8 p-4 rounded-xl bg-[#D9B35A]/10 border border-[#D9B35A]/20">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-[#D9B35A] flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-[#D9B35A]">Gestion Électronique des Documents (GED)</p>
              <p className="text-sm text-[#D9B35A]/80 mt-1">
                Ces documents sont versionnés et signables électroniquement. Chaque document dispose d'un hash SHA-256 pour garantir son intégrité.
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="all" className="space-y-6">
          <TabsList className="bg-white/[0.04] border border-white/[0.08] p-1">
            <TabsTrigger 
              value="all"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
            >
              Tous ({documents.length})
            </TabsTrigger>
            <TabsTrigger 
              value="contracts"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
            >
              Contrats ({contractDocs.length})
            </TabsTrigger>
            <TabsTrigger 
              value="terms"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
            >
              CG/CGV ({termsDocs.length})
            </TabsTrigger>
            <TabsTrigger 
              value="compliance"
              className="data-[state=active]:bg-[#D9B35A]/20 data-[state=active]:text-[#D9B35A]"
            >
              Conformité ({complianceDocs.length})
            </TabsTrigger>
          </TabsList>

          {/* All documents */}
          <TabsContent value="all" className="space-y-4">
            {documents.map(doc => (
              <DocumentCard 
                key={doc.doc_type} 
                doc={doc} 
                onPreview={handlePreview}
                onDownload={handleDownload}
                onMetadata={handleGetMetadata}
              />
            ))}
          </TabsContent>

          {/* Contracts */}
          <TabsContent value="contracts" className="space-y-4">
            {contractDocs.length === 0 ? (
              <EmptyState message="Aucun contrat" />
            ) : (
              contractDocs.map(doc => (
                <DocumentCard 
                  key={doc.doc_type} 
                  doc={doc} 
                  onPreview={handlePreview}
                  onDownload={handleDownload}
                  onMetadata={handleGetMetadata}
                />
              ))
            )}
          </TabsContent>

          {/* Terms */}
          <TabsContent value="terms" className="space-y-4">
            {termsDocs.map(doc => (
              <DocumentCard 
                key={doc.doc_type} 
                doc={doc} 
                onPreview={handlePreview}
                onDownload={handleDownload}
                onMetadata={handleGetMetadata}
              />
            ))}
          </TabsContent>

          {/* Compliance */}
          <TabsContent value="compliance" className="space-y-4">
            {complianceDocs.map(doc => (
              <DocumentCard 
                key={doc.doc_type} 
                doc={doc} 
                onPreview={handlePreview}
                onDownload={handleDownload}
                onMetadata={handleGetMetadata}
              />
            ))}
          </TabsContent>
        </Tabs>

        {/* API Integration info */}
        <div className="mt-12 glass-panel-soft rounded-[18px] p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <ExternalLink className="w-5 h-5 text-[#D4AF37]" />
            Intégration API GED
          </h3>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08]">
              <p className="font-medium text-[#D4AF37] mb-2">GET /api/ged/documents</p>
              <p className="text-white/60">Liste tous les documents avec métadonnées</p>
            </div>
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08]">
              <p className="font-medium text-[#D4AF37] mb-2">GET /api/ged/documents/{'{type}'}/metadata</p>
              <p className="text-white/60">Métadonnées complètes (ref, version, checksums)</p>
            </div>
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08]">
              <p className="font-medium text-[#D4AF37] mb-2">GET /api/ged/documents/{'{type}'}/render</p>
              <p className="text-white/60">Document rendu avec variables templating</p>
            </div>
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08]">
              <p className="font-medium text-[#D4AF37] mb-2">GET /api/ged/documents/{'{type}'}/versions</p>
              <p className="text-white/60">Historique des versions du document</p>
            </div>
          </div>
        </div>
      </div>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden bg-white text-black">
          <DialogHeader>
            <DialogTitle>{selectedDoc?.title}</DialogTitle>
            <DialogDescription>
              Version {selectedDoc?.version} · Réf: {selectedDoc?.ref}
            </DialogDescription>
          </DialogHeader>
          
          <div className="overflow-auto max-h-[70vh] border rounded-lg">
            {previewLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
              </div>
            ) : (
              <iframe
                srcDoc={previewContent}
                title="Document Preview"
                className="w-full min-h-[600px] border-0"
                sandbox="allow-same-origin"
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Document Card Component
function DocumentCard({ doc, onPreview, onDownload, onMetadata }) {
  const Icon = DOC_ICONS[doc.doc_type] || FileText;
  const statusConfig = STATUS_CONFIG[doc.status] || STATUS_CONFIG.DRAFT;

  return (
    <div className="glass-panel-soft rounded-[18px] p-5 hover:bg-white/[0.02] transition-colors">
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="w-12 h-12 rounded-xl bg-[#D9B35A]/10 flex items-center justify-center flex-shrink-0">
          <Icon className="w-6 h-6 text-[#D9B35A]" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-semibold text-white/90 mb-1">{doc.title}</h3>
              <p className="text-sm text-white/60 mb-3">{doc.description}</p>
            </div>
            <Badge className={statusConfig.color}>
              {statusConfig.label}
            </Badge>
          </div>

          {/* Metadata */}
          <div className="flex flex-wrap gap-4 text-xs text-white/50 mb-4">
            <span className="flex items-center gap-1">
              <FileText className="w-3 h-3" />
              Réf: {doc.ref}
            </span>
            <span className="flex items-center gap-1">
              <Tag className="w-3 h-3" />
              v{doc.version}
            </span>
            {doc.date_effet && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {formatDate(doc.date_effet)}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {doc.audience?.join(', ')}
            </span>
          </div>

          {/* Tags */}
          {doc.tags && doc.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {doc.tags.map(tag => (
                <Badge key={tag} variant="outline" className="text-[10px] text-white/50 border-white/20">
                  {tag}
                </Badge>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            <Button 
              size="sm" 
              variant="outline" 
              onClick={() => onPreview(doc)}
              className="border-white/10 text-white/70 hover:text-white"
            >
              <Eye className="w-4 h-4 mr-1" />
              Aperçu
            </Button>
            <Button 
              size="sm" 
              onClick={() => onDownload(doc)}
              className="bg-[#D9B35A] hover:bg-[#c9a34a] text-black"
            >
              <Download className="w-4 h-4 mr-1" />
              Télécharger
            </Button>
            <Button 
              size="sm" 
              variant="ghost" 
              onClick={() => onMetadata(doc)}
              className="text-white/50 hover:text-white"
            >
              <ExternalLink className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Empty State Component
function EmptyState({ message }) {
  return (
    <div className="text-center py-12 text-white/50">
      <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
      <p>{message}</p>
    </div>
  );
}
