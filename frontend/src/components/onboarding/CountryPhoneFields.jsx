import { COUNTRIES } from './countries';
import { Flag } from '../Flag';

const selectCls = 'h-11 rounded-xl px-2 text-sm text-white bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60';
const flagWrap = 'absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none flex items-center';

export const CountrySelect = ({ value, onChange, testId = 'country-select' }) => (
  <div className="relative">
    <span className={flagWrap}><Flag code={value} className="w-5 h-auto rounded-[2px] block" /></span>
    <select value={value} onChange={(e) => onChange(e.target.value)} data-testid={testId}
      className={`${selectCls} w-full pl-10`} style={{ colorScheme: 'dark' }}>
      {COUNTRIES.map((c) => (
        <option key={c.code} value={c.code} style={{ background: '#2A1045' }}>
          {c.name}
        </option>
      ))}
    </select>
  </div>
);

export const PhoneInput = ({ dial, number, onDialChange, onNumberChange, testId = 'phone-input' }) => (
  <div className="flex gap-2">
    <div className="relative shrink-0">
      <span className={flagWrap}><Flag code={(dial || '|GP').split('|')[1]} className="w-5 h-auto rounded-[2px] block" /></span>
      <select value={dial} onChange={(e) => onDialChange(e.target.value)} data-testid={`${testId}-dial`}
        className={`${selectCls} w-[8.25rem] pl-10`} style={{ colorScheme: 'dark' }}>
        {COUNTRIES.map((c) => (
          <option key={c.code} value={c.dial + '|' + c.code} style={{ background: '#2A1045' }}>
            {c.dial} {c.code}
          </option>
        ))}
      </select>
    </div>
    <input required type="tel" value={number} onChange={(e) => onNumberChange(e.target.value)}
      data-testid={testId} placeholder="690 00 00 00"
      className="flex-1 h-11 rounded-xl px-3.5 text-sm text-white placeholder-white/35 bg-white/[0.05] border border-[#D9B35A]/25 focus:outline-none focus:ring-1 focus:ring-[#D9B35A]/60" />
  </div>
);
