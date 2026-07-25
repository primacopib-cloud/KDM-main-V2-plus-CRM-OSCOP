import { ExternalLink, X, FileText } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

export const DocPreviewModal = ({ doc, onClose }) => {
  if (!doc) return null;
  const src = `${process.env.REACT_APP_BACKEND_URL}${doc.file_url}`;
  return (
    <Dialog open={!!doc} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-4xl w-[92vw] h-[85vh] flex flex-col p-4 bg-[#1a0b2e] border-white/10 text-white" data-testid="doc-preview-modal">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2 text-white text-base pr-8">
            <FileText className="w-4 h-4 text-[#D4AF37]" />
            <span>{doc.doc_type}</span>
            {doc.file_name && <span className="text-white/50 text-sm font-normal truncate">{doc.file_name}</span>}
            <a href={src} target="_blank" rel="noreferrer" data-testid="doc-preview-open-tab"
              className="ml-auto inline-flex items-center gap-1 text-xs text-[#D4AF37] hover:underline font-normal">
              <ExternalLink className="w-3.5 h-3.5" />
              Nouvel onglet
            </a>
          </DialogTitle>
        </DialogHeader>
        <iframe src={src} title={doc.file_name || doc.doc_type}
          className="flex-1 w-full rounded-lg bg-white" data-testid="doc-preview-iframe" />
      </DialogContent>
    </Dialog>
  );
};
