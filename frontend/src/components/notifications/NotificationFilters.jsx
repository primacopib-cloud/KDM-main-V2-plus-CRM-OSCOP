import React from 'react';
import {
  Search, Filter, Calendar, CheckCheck, Trash2, X,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select';
import { dateFilterOptions } from './notificationUtils';

export const NotificationFilters = ({
  searchQuery, setSearchQuery, handleSearch, selectedType, setSelectedType, types,
  dateFilter, setDateFilter, readFilter, setReadFilter, resetFilters,
  handleMarkAllAsRead, handleClearRead, stats, total,
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
            <div className="flex flex-col lg:flex-row gap-4">
              {/* Search */}
              <form onSubmit={handleSearch} className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Rechercher dans les notifications..."
                    className="pl-10 bg-white/[0.04] border-white/10"
                    data-testid="notifications-search"
                  />
                </div>
              </form>

              {/* Type Filter */}
              <Select value={selectedType} onValueChange={(v) => { setSelectedType(v); setPage(1); }}>
                <SelectTrigger className="w-full lg:w-48 bg-white/[0.04] border-white/10">
                  <Filter className="w-4 h-4 mr-2 text-white/40" />
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les types</SelectItem>
                  {types.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Date Filter */}
              <Select value={dateFilter} onValueChange={(v) => { setDateFilter(v); setPage(1); }}>
                <SelectTrigger className="w-full lg:w-48 bg-white/[0.04] border-white/10">
                  <Calendar className="w-4 h-4 mr-2 text-white/40" />
                  <SelectValue placeholder="Période" />
                </SelectTrigger>
                <SelectContent>
                  {dateFilterOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Read Filter */}
              <Select value={readFilter} onValueChange={(v) => { setReadFilter(v); setPage(1); }}>
                <SelectTrigger className="w-full lg:w-40 bg-white/[0.04] border-white/10">
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Toutes</SelectItem>
                  <SelectItem value="unread">Non lues</SelectItem>
                  <SelectItem value="read">Lues</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Active filters & actions */}
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/10">
              <div className="flex items-center gap-2">
                {(selectedType !== 'all' || dateFilter !== 'all' || readFilter !== 'all' || searchQuery) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={resetFilters}
                    className="text-white/60"
                  >
                    <X className="w-4 h-4 mr-1" />
                    Réinitialiser
                  </Button>
                )}
                <span className="text-sm text-white/50">
                  {total} notification{total !== 1 ? 's' : ''}
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                {stats?.unread > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleMarkAllAsRead}
                    className="text-white/60"
                  >
                    <CheckCheck className="w-4 h-4 mr-2" />
                    Tout marquer comme lu
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClearRead}
                  className="text-red-400 hover:text-red-300"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Nettoyer
                </Button>
              </div>
            </div>
          </div>

  </>
);
