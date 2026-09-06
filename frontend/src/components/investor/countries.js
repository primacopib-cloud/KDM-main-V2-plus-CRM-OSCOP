// Pays du formulaire FINANCER — dérivés de la liste mondiale partagée (206 pays)
import { COUNTRIES as WORLD } from '../onboarding/countries';

const PRIORITY_CODES = ['FR', 'GP', 'MQ', 'GF', 'RE', 'YT', 'PM', 'BL', 'MF', 'PF', 'NC', 'WF'];
const mapped = WORLD.map((c) => ({ code: c.code, name: c.name, prefix: c.dial }));

export const PRIORITY_COUNTRIES = PRIORITY_CODES
  .map((code) => mapped.find((c) => c.code === code))
  .filter(Boolean);
export const WORLD_COUNTRIES = mapped
  .filter((c) => !PRIORITY_CODES.includes(c.code))
  .sort((a, b) => a.name.localeCompare(b.name, 'fr'));
export const ALL_COUNTRIES = [...PRIORITY_COUNTRIES, ...WORLD_COUNTRIES];
