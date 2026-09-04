import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Loader2, Scale } from 'lucide-react';
import { API } from '../services/http';
import Header from '../components/Header';
import Footer from '../components/Footer';

export default function LegalDynamicPage() {
  const { pathname } = useLocation();
  const slug = pathname.replace(/^\//, '');
  const [page, setPage] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setPage(null);
    fetch(`${API}/public/legal-pages/${slug}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setPage)
      .catch(() => setError(true));
  }, [slug]);

  return (
    <div className="min-h-screen text-white" style={{ background: 'linear-gradient(180deg, #2A1045 0%, #451F6B 55%, #2A1045 100%)' }}>
      <Header />
      <main className="max-w-[840px] mx-auto px-5 py-14" data-testid={`legal-page-${slug}`}>
        {!page && !error && <Loader2 className="w-6 h-6 animate-spin text-[#D9B35A]" />}
        {error && <p className="text-white/60">Page introuvable.</p>}
        {page && (
          <>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2 flex items-start gap-3">
              <Scale className="w-7 h-7 text-[#D9B35A] mt-1.5 shrink-0" />
              {page.title}
            </h1>
            <p className="text-white/40 text-xs mb-8">Dernière mise à jour : {page.updated_at?.slice(0, 10)}</p>
            <div className="space-y-4">
              {page.content.split('\n\n').map((para, i) => (
                <p key={i} className="text-white/75 text-sm leading-relaxed whitespace-pre-line">{para}</p>
              ))}
            </div>
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}
