import i18n from '@/i18n';
import React from 'react';
import { Search, RefreshCw, Calendar } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';

export const ShoppingListFilters = ({
  lists, searchQuery, setSearchQuery, sortBy, setSortBy, refreshing, fetchLists,
  filterFrequency, setFilterFrequency,
}) => (
  <>
          {/* Filters */}
          <div
            className="p-4 rounded-2xl mb-6"
            style={{
              background: 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div className="flex flex-col lg:flex-row gap-4 items-center">
              {/* Search */}
              <div className="relative flex-1 w-full">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Rechercher une liste..."
                  className="pl-10 bg-white/[0.04] border-white/10"
                  data-testid="lists-search"
                />
              </div>

              {/* Frequency Filter */}
              <Select value={filterFrequency} onValueChange={setFilterFrequency}>
                <SelectTrigger className="w-full lg:w-48 bg-white/[0.04] border-white/10">
                  <Calendar className="w-4 h-4 mr-2 text-white/40" />
                  <SelectValue placeholder="Fréquence" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{i18n.t('lists.toutes_frequences')}</SelectItem>
                  <SelectItem value="weekly">{i18n.t('lists.hebdomadaire')}</SelectItem>
                  <SelectItem value="biweekly">{i18n.t('lists.bi_mensuel')}</SelectItem>
                  <SelectItem value="monthly">{i18n.t('lists.mensuel')}</SelectItem>
                  <SelectItem value="quarterly">{i18n.t('lists.trimestriel')}</SelectItem>
                  <SelectItem value="one_time">{i18n.t('lists.ponctuel')}</SelectItem>
                  <SelectItem value="custom">{i18n.t('lists.personnalise')}</SelectItem>
                </SelectContent>
              </Select>

              {/* Sort */}
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="w-full lg:w-40 bg-white/[0.04] border-white/10">
                  <SelectValue placeholder="Trier par" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="created_at">{i18n.t('lists.date_creation')}</SelectItem>
                  <SelectItem value="last_used_at">{i18n.t('lists.derniere_utilisation')}</SelectItem>
                  <SelectItem value="use_count">{i18n.t('lists.plus_utilisees')}</SelectItem>
                  <SelectItem value="name">{i18n.t('lists.nom_a_z')}</SelectItem>
                </SelectContent>
              </Select>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => fetchLists(true)}
                disabled={refreshing}
                className="text-white/60"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
  </>
);
