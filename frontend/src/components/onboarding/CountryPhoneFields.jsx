import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Search } from 'lucide-react';
import { COUNTRIES } from './countries';
import { Flag } from '../Flag';

const fieldCls = 'h-11 rounded-xl px-2 text-sm text-white bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60';

export const SearchableCountryDropdown = ({ value, onSelect, display, mode = 'country', countries = COUNTRIES, testId, buttonClassName = '' }) => {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const norm = (s) => (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const filtered = countries.filter((c) => {
    const needle = norm(q.trim());
    if (!needle) return true;
    return norm(c.name).includes(needle) || (c.dial || '').replace('+', '').startsWith(needle.replace('+', '')) || norm(c.code).startsWith(needle);
  });

  return (
    <div className="relative" ref={ref}>
      <button type="button" data-testid={testId}
        onClick={() => { setOpen(!open); setQ(''); }}
        className={`${fieldCls} ${buttonClassName} flex items-center gap-2 pl-2.5 pr-2 w-full`}>
        <Flag code={value} className="w-5 h-auto rounded-[2px] shrink-0" />
        <span className="flex-1 text-left truncate">{display}</span>
        <ChevronDown className="w-3.5 h-3.5 opacity-50 shrink-0" />
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-64 rounded-xl border border-[#D9B35A]/30 shadow-2xl overflow-hidden"
          style={{ background: '#2A1045' }} data-testid={`${testId}-panel`}>
          <div className="flex items-center gap-2 px-2.5 py-2 border-b border-white/10">
            <Search className="w-3.5 h-3.5 text-white/40 shrink-0" />
            <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} data-testid={`${testId}-search`}
              placeholder={mode === 'dial' ? 'Indicatif ou pays… (ex. 590)' : 'Rechercher un pays…'}
              className="w-full bg-transparent text-sm text-white placeholder-white/35 focus:outline-none" />
          </div>
          <div className="max-h-56 overflow-y-auto">
            {filtered.length === 0 && <p className="px-3 py-2.5 text-xs text-white/40">Aucun résultat</p>}
            {filtered.map((c) => (
              <button key={c.code} type="button" data-testid={`${testId}-opt-${c.code}`}
                onClick={() => { onSelect(c); setOpen(false); }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-left text-sm hover:bg-white/10 ${c.code === value ? 'bg-[#D9B35A]/15 text-[#E9CF8E]' : 'text-white/80'}`}>
                <Flag code={c.code} className="w-5 h-auto rounded-[2px] shrink-0" />
                <span className="flex-1 truncate">{c.name}</span>
                <span className="text-white/45 text-xs">{c.dial}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export const CountrySelect = ({ value, onChange, testId = 'country-select' }) => {
  const current = COUNTRIES.find((c) => c.code === value);
  return (
    <SearchableCountryDropdown value={value} display={current?.name || value} mode="country" testId={testId}
      onSelect={(c) => onChange(c.code)} />
  );
};

export const PhoneInput = ({ dial, number, onDialChange, onNumberChange, testId = 'phone-input' }) => {
  const code = (dial || '|GP').split('|')[1];
  const dialValue = (dial || '+590|GP').split('|')[0];
  return (
    <div className="flex gap-2">
      <div className="w-[8.25rem] shrink-0">
        <SearchableCountryDropdown value={code} display={dialValue} mode="dial" testId={`${testId}-dial`}
          onSelect={(c) => onDialChange(c.dial + '|' + c.code)} />
      </div>
      <input required type="tel" value={number} onChange={(e) => onNumberChange(e.target.value)}
        data-testid={testId} placeholder="690 00 00 00"
        className="flex-1 h-11 rounded-xl px-3.5 text-sm text-white placeholder-white/35 bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60" />
    </div>
  );
};
