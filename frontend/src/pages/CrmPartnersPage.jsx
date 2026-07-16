import i18n from '@/i18n';
import React, { useEffect, useState } from 'react';
import {
  HeartHandshake, Building2, Activity, Briefcase, RefreshCw, Search, Plus,
  CheckCircle2, Clock, ListChecks, ArrowRight,
} from 'lucide-react';
import LolodriveLayout, { KpiCard, SectionCard, Badge } from '../components/LolodriveLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { crmAPI } from '../services/api';
import { toast } from 'sonner';

const PIPELINE_STAGES = [
  { id: 'lead_entrant', label: 'Lead', color: '#888' },
  { id: 'qualification', label: 'Qualification', color: '#3b82f6' },
  { id: 'negociation', label: 'Négociation', color: '#D9B35A' },
  { id: 'dossier_depose', label: 'Dossier déposé', color: '#7c3aed' },
  { id: 'activation_planifiee', label: 'Activation planifiée', color: '#ec4899' },
  { id: 'gagne', label: 'Gagné', color: '#10b981' },
  { id: 'perdu', label: 'Perdu', color: '#ef4444' },
];

export default function CrmPartnersPage() {
  const [tab, setTab] = useState('pipeline');
  const [search, setSearch] = useState('');
  const [contacts, setContacts] = useState([]);
  const [orgs, setOrgs] = useState([]);
  const [opps, setOpps] = useState([]);
  const [dossiers, setDossiers] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(null);

  // Dialog forms
  const [newContact, setNewContact] = useState(false);
  const [newOrg, setNewOrg] = useState(false);
  const [newOpp, setNewOpp] = useState(false);
  const [newTask, setNewTask] = useState(false);

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

  const moveOpp = async (oppId, stage) => {
    setOpps(opps.map((o) => o.id === oppId ? { ...o, pipeline_stage: stage } : o));
    try {
      await crmAPI.updateOppStage(oppId, stage);
      toast.success(`Opportunité → ${stage}`);
    } catch (e) {
      toast.error(e.message);
      load();
    }
  };

  const toggleTask = async (task) => {
    const next = task.status === 'done' ? 'todo' : 'done';
    try {
      await crmAPI.updateTaskStatus(task.id, next);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <LolodriveLayout
      title="CRM Partenaires O'SCOP"
      subtitle="Pipeline drag-and-drop, contacts, organisations, opportunités, dossiers, tâches."
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
        <KpiCard testId="kpi-tasks" label="Tâches" value={tasks.length} icon={ListChecks} accent="#10b981" />
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
          <Input
            placeholder="Rechercher contact / org…"
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
          <TabsTrigger value="pipeline" data-testid="tab-pipeline">Pipeline</TabsTrigger>
          <TabsTrigger value="contacts" data-testid="tab-contacts">Contacts</TabsTrigger>
          <TabsTrigger value="orgs" data-testid="tab-orgs">Organisations</TabsTrigger>
          <TabsTrigger value="dossiers" data-testid="tab-dossiers">Dossiers</TabsTrigger>
          <TabsTrigger value="tasks" data-testid="tab-tasks">Tâches</TabsTrigger>
        </TabsList>

        {loading && <div className="text-center text-white/50 py-12">Chargement…</div>}

        {!loading && tab === 'pipeline' && (
          <>
            <div className="flex justify-end mb-2">
              <NewOppDialog open={newOpp} onOpenChange={setNewOpp} orgs={orgs} onCreated={load} />
            </div>
            <div className="overflow-x-auto pb-3" data-testid="kanban">
              <div className="flex gap-3 min-w-max">
                {PIPELINE_STAGES.map((s) => {
                  const stageOpps = opps.filter((o) => o.pipeline_stage === s.id);
                  return (
                    <div
                      key={s.id}
                      data-testid={`column-${s.id}`}
                      onDragOver={(e) => { e.preventDefault(); setDragOver(s.id); }}
                      onDragLeave={() => setDragOver(null)}
                      onDrop={(e) => {
                        e.preventDefault();
                        const oppId = e.dataTransfer.getData('oppId');
                        if (oppId) moveOpp(oppId, s.id);
                        setDragOver(null);
                      }}
                      className={`w-72 shrink-0 rounded-xl bg-white/[0.025] border ${dragOver === s.id ? 'border-[#D9B35A]' : 'border-white/[0.07]'} p-3 transition-colors`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                          <div className="text-xs font-semibold uppercase tracking-wider">{s.label}</div>
                        </div>
                        <Badge color={s.color}>{stageOpps.length}</Badge>
                      </div>
                      <div className="space-y-2 min-h-[100px]">
                        {stageOpps.map((o) => (
                          <div
                            key={o.id}
                            draggable
                            onDragStart={(e) => e.dataTransfer.setData('oppId', o.id)}
                            data-testid={`card-${o.id}`}
                            className="p-3 rounded-lg bg-white/[0.04] border border-white/[0.07] cursor-grab active:cursor-grabbing hover:border-white/[0.15] transition-colors"
                          >
                            <div className="font-medium text-sm leading-tight mb-1">{o.titre}</div>
                            <div className="text-[11px] text-white/40 mb-2">
                              {o.type_besoin}
                              {o.produit_vise && <> · {o.produit_vise}</>}
                            </div>
                            {o.probabilite_conversion != null && (
                              <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden">
                                <div className="h-full rounded-full" style={{
                                  width: `${o.probabilite_conversion}%`,
                                  background: s.color,
                                }} />
                              </div>
                            )}
                            {o.montant_estime_cents && (
                              <div className="text-[10px] text-white/50 mt-1">
                                {(o.montant_estime_cents / 100).toLocaleString(i18n.language, { style: 'currency', currency: 'EUR' })}
                              </div>
                            )}
                          </div>
                        ))}
                        {stageOpps.length === 0 && (
                          <div className="text-[10px] text-white/30 text-center py-4 border border-dashed border-white/10 rounded">
                            Glissez ici
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}

        {!loading && tab === 'contacts' && (
          <SectionCard
            title={`Contacts (${contacts.length})`}
            action={<NewContactDialog open={newContact} onOpenChange={setNewContact} onCreated={load} />}
          >
            {contacts.map((c) => (
              <CrmRow key={c.id} testId={`contact-${c.id}`}>
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{c.prenom} {c.nom}</div>
                  <div className="text-xs text-white/40">{c.email} · {c.telephone}</div>
                </div>
                <div className="flex flex-wrap gap-1">
                  <Badge color="#3b82f6">{c.type_acteur}</Badge>
                  <Badge color="#7c3aed">{c.statut_relation}</Badge>
                  {(c.tags || []).slice(0, 2).map((t) => <Badge key={t} color="#D9B35A">{t}</Badge>)}
                </div>
              </CrmRow>
            ))}
          </SectionCard>
        )}

        {!loading && tab === 'orgs' && (
          <SectionCard
            title={`Organisations (${orgs.length})`}
            action={<NewOrgDialog open={newOrg} onOpenChange={setNewOrg} onCreated={load} />}
          >
            {orgs.map((o) => (
              <CrmRow key={o.id} testId={`org-${o.id}`}>
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{o.raison_sociale}</div>
                  <div className="text-xs text-white/40">
                    {o.enseigne && <>{o.enseigne} · </>}{o.ville} · {o.territoire}
                  </div>
                </div>
                <div className="flex flex-wrap gap-1">
                  <Badge color="#3b82f6">{o.type_structure}</Badge>
                  <Badge color={o.statut_ecosysteme === 'actif' ? '#10b981' : '#888'}>{o.statut_ecosysteme}</Badge>
                </div>
              </CrmRow>
            ))}
          </SectionCard>
        )}

        {!loading && tab === 'dossiers' && (
          <SectionCard title={`Dossiers (${dossiers.length})`}>
            {dossiers.map((d) => (
              <CrmRow key={d.id} testId={`dossier-${d.id}`}>
                <div className="flex-1">
                  <div className="font-medium">{d.objet_besoin || d.type_dossier}</div>
                  <div className="text-xs text-white/40">{d.type_dossier} · {d.etape_actuelle}</div>
                </div>
                <div className="flex gap-1">
                  <Badge color={d.statut === 'ouvert' ? '#10b981' : '#888'}>{d.statut}</Badge>
                  <Badge color={d.niveau_urgence === 'haute' ? '#ef4444' : '#D9B35A'}>{d.niveau_urgence}</Badge>
                </div>
              </CrmRow>
            ))}
          </SectionCard>
        )}

        {!loading && tab === 'tasks' && (
          <SectionCard
            title={`Tâches (${tasks.length})`}
            action={<NewTaskDialog open={newTask} onOpenChange={setNewTask} opps={opps} dossiers={dossiers} onCreated={load} />}
          >
            {tasks.map((t) => (
              <div key={t.id} data-testid={`task-${t.id}`}
                className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05] mb-2">
                <button onClick={() => toggleTask(t)} className="shrink-0" data-testid={`task-toggle-${t.id}`}>
                  {t.status === 'done'
                    ? <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    : <Clock className="w-5 h-5 text-white/40 hover:text-white/70" />}
                </button>
                <div className="flex-1">
                  <div className={`font-medium ${t.status === 'done' ? 'line-through text-white/40' : ''}`}>
                    {t.title}
                  </div>
                  {t.description && <div className="text-xs text-white/40">{t.description}</div>}
                  {t.due_at && <div className="text-xs text-white/40 mt-1">📅 {new Date(t.due_at).toLocaleDateString(i18n.language)}</div>}
                </div>
                <div className="flex gap-1">
                  <Badge color={t.priority === 'high' ? '#ef4444' : '#D9B35A'}>{t.priority}</Badge>
                  <Badge color={t.status === 'todo' ? '#888' : t.status === 'in_progress' ? '#3b82f6' : '#10b981'}>{t.status}</Badge>
                </div>
              </div>
            ))}
          </SectionCard>
        )}
      </Tabs>
    </LolodriveLayout>
  );
}

const CrmRow = ({ children, testId }) => (
  <div data-testid={testId}
    className="flex items-center justify-between gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05] mb-2">
    {children}
  </div>
);

const NewContactDialog = ({ open, onOpenChange, onCreated }) => {
  const [f, setF] = useState({ prenom: '', nom: '', email: '', telephone: '', type_acteur: 'prospect', source_contact: 'manuel' });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" data-testid="new-contact-btn"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
          <Plus className="w-3 h-3 mr-1" /> Contact
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#15151c] border-white/10 text-white">
        <DialogHeader><DialogTitle>Nouveau contact</DialogTitle></DialogHeader>
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="Prénom" value={f.prenom} onChange={(e) => setF({ ...f, prenom: e.target.value })} className="bg-white/[0.04] border-white/10" />
            <Input placeholder="Nom" value={f.nom} onChange={(e) => setF({ ...f, nom: e.target.value })} className="bg-white/[0.04] border-white/10" />
          </div>
          <Input placeholder="Email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className="bg-white/[0.04] border-white/10" />
          <Input placeholder="Téléphone" value={f.telephone} onChange={(e) => setF({ ...f, telephone: e.target.value })} className="bg-white/[0.04] border-white/10" />
          <Button className="w-full" onClick={async () => {
            try { await crmAPI.createContact(f); toast.success('Contact créé'); onOpenChange(false); onCreated(); }
            catch (e) { toast.error(e.message); }
          }} data-testid="confirm-new-contact"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>Créer</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

const NewOrgDialog = ({ open, onOpenChange, onCreated }) => {
  const [f, setF] = useState({ raison_sociale: '', enseigne: '', ville: '', territoire: 'Guadeloupe', type_structure: 'fournisseur_partenaire' });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" data-testid="new-org-btn"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
          <Plus className="w-3 h-3 mr-1" /> Org.
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#15151c] border-white/10 text-white">
        <DialogHeader><DialogTitle>Nouvelle organisation</DialogTitle></DialogHeader>
        <div className="space-y-2">
          <Input placeholder="Raison sociale" value={f.raison_sociale} onChange={(e) => setF({ ...f, raison_sociale: e.target.value })} className="bg-white/[0.04] border-white/10" />
          <Input placeholder="Enseigne" value={f.enseigne} onChange={(e) => setF({ ...f, enseigne: e.target.value })} className="bg-white/[0.04] border-white/10" />
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="Ville" value={f.ville} onChange={(e) => setF({ ...f, ville: e.target.value })} className="bg-white/[0.04] border-white/10" />
            <Input placeholder="Territoire" value={f.territoire} onChange={(e) => setF({ ...f, territoire: e.target.value })} className="bg-white/[0.04] border-white/10" />
          </div>
          <Button className="w-full" onClick={async () => {
            try { await crmAPI.createOrg(f); toast.success('Organisation créée'); onOpenChange(false); onCreated(); }
            catch (e) { toast.error(e.message); }
          }} data-testid="confirm-new-org"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>Créer</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

const NewOppDialog = ({ open, onOpenChange, orgs, onCreated }) => {
  const [f, setF] = useState({ titre: '', organization_id: '', type_besoin: 'partenariat', pipeline_stage: 'lead_entrant', probabilite_conversion: 50 });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" data-testid="new-opp-btn"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
          <Plus className="w-3 h-3 mr-1" /> Opportunité
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#15151c] border-white/10 text-white">
        <DialogHeader><DialogTitle>Nouvelle opportunité</DialogTitle></DialogHeader>
        <div className="space-y-2">
          <Input placeholder="Titre" value={f.titre} onChange={(e) => setF({ ...f, titre: e.target.value })} className="bg-white/[0.04] border-white/10" />
          <Select value={f.organization_id} onValueChange={(v) => setF({ ...f, organization_id: v })}>
            <SelectTrigger className="bg-white/[0.04] border-white/10"><SelectValue placeholder="Organisation (optionnelle)" /></SelectTrigger>
            <SelectContent>{orgs.map((o) => <SelectItem key={o.id} value={o.id}>{o.raison_sociale}</SelectItem>)}</SelectContent>
          </Select>
          <Input placeholder="Type de besoin" value={f.type_besoin} onChange={(e) => setF({ ...f, type_besoin: e.target.value })} className="bg-white/[0.04] border-white/10" />
          <Select value={f.pipeline_stage} onValueChange={(v) => setF({ ...f, pipeline_stage: v })}>
            <SelectTrigger className="bg-white/[0.04] border-white/10"><SelectValue /></SelectTrigger>
            <SelectContent>{PIPELINE_STAGES.map((s) => <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>)}</SelectContent>
          </Select>
          <Button className="w-full" onClick={async () => {
            try {
              const p = { ...f }; if (!p.organization_id) delete p.organization_id;
              await crmAPI.createOpp(p); toast.success('Opportunité créée'); onOpenChange(false); onCreated();
            } catch (e) { toast.error(e.message); }
          }} data-testid="confirm-new-opp"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>Créer</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

const NewTaskDialog = ({ open, onOpenChange, opps, dossiers, onCreated }) => {
  const [f, setF] = useState({ title: '', description: '', priority: 'normal', status: 'todo', due_at: '', related_type: '', related_id: '' });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" data-testid="new-task-btn"
          style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>
          <Plus className="w-3 h-3 mr-1" /> Tâche
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#15151c] border-white/10 text-white">
        <DialogHeader><DialogTitle>Nouvelle tâche</DialogTitle></DialogHeader>
        <div className="space-y-2">
          <Input placeholder="Titre" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className="bg-white/[0.04] border-white/10" />
          <Textarea placeholder="Description (optionnelle)" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} className="bg-white/[0.04] border-white/10" />
          <Input type="date" value={f.due_at?.slice(0,10) || ''} onChange={(e) => setF({ ...f, due_at: new Date(e.target.value).toISOString() })} className="bg-white/[0.04] border-white/10" />
          <Select value={f.priority} onValueChange={(v) => setF({ ...f, priority: v })}>
            <SelectTrigger className="bg-white/[0.04] border-white/10"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="low">Basse</SelectItem>
              <SelectItem value="normal">Normale</SelectItem>
              <SelectItem value="high">Haute</SelectItem>
            </SelectContent>
          </Select>
          <Button className="w-full" onClick={async () => {
            try { const p = { ...f }; if (!p.due_at) delete p.due_at; await crmAPI.createTask(p); toast.success('Tâche créée'); onOpenChange(false); onCreated(); }
            catch (e) { toast.error(e.message); }
          }} data-testid="confirm-new-task"
            style={{ background: 'linear-gradient(135deg, #D9B35A, #7c3aed)' }}>Créer</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
