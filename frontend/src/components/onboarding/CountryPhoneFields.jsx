import { COUNTRIES } from './countries';

const selectCls = 'h-11 rounded-xl px-2 text-sm text-white bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60';

export const CountrySelect = ({ value, onChange, testId = 'country-select' }) => (
  <select value={value} onChange={(e) => onChange(e.target.value)} data-testid={testId}
    className={`${selectCls} w-full`} style={{ colorScheme: 'dark' }}>
    {COUNTRIES.map((c) => (
      <option key={c.code} value={c.code} style={{ background: '#2A1045' }}>
        {c.flag} {c.name}
      </option>
    ))}
  </select>
);

export const PhoneInput = ({ dial, number, onDialChange, onNumberChange, testId = 'phone-input' }) => (
  <div className="flex gap-2">
    <select value={dial} onChange={(e) => onDialChange(e.target.value)} data-testid={`${testId}-dial`}
      className={`${selectCls} w-[7.5rem] shrink-0`} style={{ colorScheme: 'dark' }}>
      {COUNTRIES.map((c) => (
        <option key={c.code} value={c.dial + '|' + c.code} style={{ background: '#2A1045' }}>
          {c.flag} {c.dial}
        </option>
      ))}
    </select>
    <input required type="tel" value={number} onChange={(e) => onNumberChange(e.target.value)}
      data-testid={testId} placeholder="690 00 00 00"
      className="flex-1 h-11 rounded-xl px-3.5 text-sm text-white placeholder-white/35 bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60" />
  </div>
);
