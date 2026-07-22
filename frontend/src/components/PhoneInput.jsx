import { useState } from 'react';
import { PHONE_COUNTRIES } from './contactFormData';
import { Flag } from './Flag';

export const PhoneInput = ({ value = '', onChange, inputClass = '', testId = 'phone-input' }) => {
  const [dial, setDial] = useState('+590');
  const number = value.startsWith('+') ? value.split(' ').slice(1).join(' ') : value;
  const country = PHONE_COUNTRIES.find((c) => c.dial === dial) || PHONE_COUNTRIES[0];

  const emit = (d, n) => onChange(n ? `${d} ${n}` : '');

  return (
    <div className="flex items-center gap-1.5">
      <Flag code={country.code} className="w-5 h-auto rounded-[2px] flex-shrink-0" />
      <select value={dial} data-testid={`${testId}-dial`}
        onChange={(e) => { setDial(e.target.value); emit(e.target.value, number); }}
        className="h-9 px-1.5 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15 w-[80px]">
        {PHONE_COUNTRIES.map((c) => (
          <option key={`${c.code}-${c.dial}`} value={c.dial}>{c.code} {c.dial}</option>
        ))}
      </select>
      <input value={number} data-testid={testId} placeholder="690 00 00 00"
        onChange={(e) => emit(dial, e.target.value.replace(/[^\d ]/g, ''))}
        className={inputClass || 'h-9 px-2.5 rounded-lg text-xs text-white bg-white/[0.05] border border-white/15 w-28'} />
      <span className="sr-only">{country.name}</span>
    </div>
  );
};
