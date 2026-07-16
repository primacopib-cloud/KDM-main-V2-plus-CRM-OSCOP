import React from 'react';
import { Search, RefreshCw } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';

export const ShoppingListFilters = ({
  lists, searchQuery, setSearchQuery, sortBy, setSortBy, refreshing, fetchLists,
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
                  <SelectItem value="all">Toutes fréquences</SelectItem>
                  <SelectItem value="weekly">Hebdomadaire</SelectItem>
                  <SelectItem value="biweekly">Bi-mensuel</SelectItem>
                  <SelectItem value="monthly">Mensuel</SelectItem>
                  <SelectItem value="quarterly">Trimestriel</SelectItem>
                  <SelectItem value="one_time">Ponctuel</SelectItem>
                  <SelectItem value="custom">Personnalisé</SelectItem>
                </SelectContent>
              </Select>

              {/* Sort */}
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="w-full lg:w-40 bg-white/[0.04] border-white/10">
                  <SelectValue placeholder="Trier par" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="created_at">Date création</SelectItem>
                  <SelectItem value="last_used_at">Dernière utilisation</SelectItem>
                  <SelectItem value="use_count">Plus utilisées</SelectItem>
                  <SelectItem value="name">Nom A-Z</SelectItem>
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
