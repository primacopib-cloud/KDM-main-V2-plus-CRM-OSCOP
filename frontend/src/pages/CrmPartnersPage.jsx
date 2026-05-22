import React, { useEffect, useState } from 'react';
import { HeartHandshake, Building2, Activity, Briefcase, RefreshCw, Search, Plus, Tag } from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { crmAPI } from '../services/api';
import { toast } from 'sonner';

const STAGE_COLORS = {
  lead_entrant: '#888',
  qualification: '#3b82f6',
  negociation: '#D9B35A',
  dossier_depose: '#7c3aed',
  activation_planifiee: '#ec4899',
  gagne: '#10b981',
  perdu: '#ef4444',
};

export default function CrmPartnersPage() {
  const [tab, setTab] = useState('contacts');
  const [search, setSearch] = useState('');
  const [contacts, setContacts] = useState([]);
  const [orgs, setOrgs] = useState([]);
  const [opps, setOpps] = useState([]);
  const [dossiers, setDossiers] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const [c, o, p, d, t] = await Promise.all([
        crmAPI.listContacts(search || null),
        crmAPI.listOrgs(search || null),
        crmAPI.listOpps(),
        crmAPI.listDossiers(),
        crmAPI.listTasks(),
      ]);
      setContacts(c.contacts || []);
      setOrgs(o.organizations || []);
      setOpps(p.opportunities || []);
      setDossiers(d.dossiers || []);
      setTasks(t.tasks || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); /* eslint-disable-line */ }, []);

  return (
    <LolodriveLayout
      title="CRM Partenaires O'SCOP"
      subtitle="Couche relationnelle uniquement. La V2 reste la source de vérité transactionnelle."
      actions={
        <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
          <RefreshCw className="w-4 h-4 mr-2" /> Actualiser
        </Button>
      }
    >
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <KpiCard testId="kpi-contacts" label="Contacts" value={contacts.length} icon={HeartHandshake} accent="#ec4899" />
        <KpiCard testId="kpi-orgs" label="Organisations" value={orgs.length} icon={Building2} accent="#3b82f6" />
        <KpiCard testId="kpi-opps" label="Opportunités" value={opps.length} icon={Activity} accent="#D9B35A" />
        <KpiCard testId="kpi-dossiers" label="Dossiers" value={dossiers.length} icon={Briefcase} accent="#7c3aed" />
        <KpiCard testId="kpi-tasks" label="Tâches" value={tasks.length} icon={Tag} accent="#10b981" />
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
          <Input
            placeholder="Rechercher…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && load()}
            className="bg-white/[0.04] border-white/10 pl-9"
            data-testid="crm-search"
          />
        </div>
        <Button variant="outline" size="sm" onClick={load}>Filtrer</Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-white/[0.04] border border-white/10 mb-4">
          <TabsTrigger value="contacts" data-testid="tab-contacts">Contacts</TabsTrigger>
          <TabsTrigger value="orgs" data-testid="tab-orgs">Organisations</TabsTrigger>
          <TabsTrigger value="opps" data-testid="tab-opps">Pipeline</TabsTrigger>
          <TabsTrigger value="dossiers" data-testid="tab-dossiers">Dossiers</TabsTrigger>
          <TabsTrigger value="tasks" data-testid="tab-tasks">Tâches</TabsTrigger>
        </TabsList>

        {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

        {!loading && tab === 'contacts' && (
          <SectionCard title={`Contacts (${contacts.length})`}>
            {contacts.map((c) => (
              <Row key={c.id} testId={`contact-${c.id}`}>
                <div className="flex-1">
                  <div className="font-medium">{c.prenom} {c.nom}</div>
                  <div className="text-xs text-white/40">{c.email} · {c.telephone}</div>
                </div>
                <div className="flex flex-wrap gap-1">
                  <Badge color="#3b82f6">{c.type_acteur}</Badge>
                  <Badge color="#7c3aed">{c.statut_relation}</Badge>
                  {(c.tags || []).slice(0, 3).map((t) => <Badge key={t} color="#D9B35A">{t}</Badge>)}
                </div>
              </Row>
            ))}
          </SectionCard>
        )}

        {!loading && tab === 'orgs' && (
          <SectionCard title={`Organisations (${orgs.length})`}>
            {orgs.map((o) => (
              <Row key={o.id} testId={`org-${o.id}`}>
                <div className="flex-1">
                  <div className="font-medium">{o.raison_sociale}</div>
                  <div className="text-xs text-white/40">
                    {o.enseigne && <>{o.enseigne} · </>}
                    {o.ville} · {o.territoire}
                  </div>
                </div>
                <div className="flex flex-wrap gap-1">
                  <Badge color="#3b82f6">{o.type_structure}</Badge>
                  <Badge color={o.statut_ecosysteme === 'actif' ? '#10b981' : '#888'}>{o.statut_ecosysteme}</Badge>
                </div>
              </Row>
            ))}
          </SectionCard>
        )}

        {!loading && tab === 'opps' && (
          <SectionCard title={`Pipeline opportunités (${opps.length})`}>
            {opps.map((p) => (
              <Row key={p.id} testId={`opp-${p.id}`}>
                <div className="flex-1">
                  <div className="font-medium">{p.titre}</div>
                  <div className="text-xs text-white/40">
                    {p.type_besoin}
                    {p.produit_vise && <> · {p.produit_vise}</>}
                    {p.probabilite_conversion != null && <> · {p.probabilite_conversion}%</>}
                  </div>
                </div>
                <Badge color={STAGE_COLORS[p.pipeline_stage] || '#888'}>{p.pipeline_stage}</Badge>
              </Row>
            ))}
          </SectionCard>
        )}

        {!loading && tab === 'dossiers' && (
          <SectionCard title={`Dossiers (${dossiers.length})`}>
            {dossiers.map((d) => (
              <Row key={d.id} testId={`dossier-${d.id}`}>
                <div className="flex-1">
                  <div className="font-medium">{d.objet_besoin || d.type_dossier}</div>
                  <div className="text-xs text-white/40">{d.type_dossier} · {d.etape_actuelle}</div>
                </div>
                <div className="flex gap-1">
                  <Badge color={d.statut === 'ouvert' ? '#10b981' : '#888'}>{d.statut}</Badge>
                  <Badge color={d.niveau_urgence === 'haute' ? '#ef4444' : '#D9B35A'}>{d.niveau_urgence}</Badge>
                </div>
              </Row>
            ))}
          </SectionCard>
        )}

        {!loading && tab === 'tasks' && (
          <SectionCard title={`Tâches (${tasks.length})`}>
            {tasks.map((t) => (
              <Row key={t.id} testId={`task-${t.id}`}>
                <div className="flex-1">
                  <div className="font-medium">{t.title}</div>
                  {t.description && <div className="text-xs text-white/40">{t.description}</div>}
                  {t.due_at && <div className="text-xs text-white/40 mt-1">📅 {new Date(t.due_at).toLocaleDateString('fr-FR')}</div>}
                </div>
                <div className="flex gap-1">
                  <Badge color={t.priority === 'high' ? '#ef4444' : '#D9B35A'}>{t.priority}</Badge>
                  <Badge color={t.status === 'todo' ? '#888' : t.status === 'in_progress' ? '#3b82f6' : '#10b981'}>{t.status}</Badge>
                </div>
              </Row>
            ))}
          </SectionCard>
        )}
      </Tabs>
    </LolodriveLayout>
  );
}

const Row = ({ children, testId }) => (
  <div data-testid={testId}
    className="flex items-center justify-between gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05] mb-2">
    {children}
  </div>
);
