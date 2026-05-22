/**
 * Tests verrouillant le contrat hooks de PublicLolodriveMapSection :
 *   • listTerritories DOIT être appelé UNE FOIS (montage) — pas re-déclenché
 *     par un changement de territoire.
 *   • listLoloPoints DOIT être appelé une fois au montage (territory=null)
 *     puis à chaque changement de territoire.
 *
 * Si quelqu'un re-introduit l'ancien effet unique avec
 * `[territory]` qui mélangeait territoires + points, ces tests échouent.
 */
import React from 'react';
import { render, screen, act, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// ----------------- Mocks -----------------

jest.mock('../services/api', () => {
  const listTerritories = jest.fn();
  const listLoloPoints = jest.fn();
  return {
    __esModule: true,
    lolodriveAPI: { listTerritories, listLoloPoints },
    downloadOffer: jest.fn(),
    authAPI: { isAuthenticated: jest.fn(() => true) },
    quoteAPI: { create: jest.fn() },
  };
});

// Heavy WebGL component — replace by a tiny stub that just shows points count.
jest.mock('../components/LoloPointsMap', () => ({
  __esModule: true,
  default: ({ points }) => (
    <div data-testid="mock-map">map:{points?.length || 0}</div>
  ),
}));

// Controllable selector — emits buttons we can click in the tests.
jest.mock('../components/TerritorySelector', () => ({
  __esModule: true,
  default: ({ onChange, value }) => (
    <div data-testid="mock-territory-selector">
      <span data-testid="current-territory">{value || 'null'}</span>
      <button type="button" onClick={() => onChange('GP')}>set-gp</button>
      <button type="button" onClick={() => onChange('MQ')}>set-mq</button>
      <button type="button" onClick={() => onChange(null)}>set-null</button>
    </div>
  ),
  getInitialTerritory: () => null,
}));

import { lolodriveAPI } from '../services/api';
import { PublicLolodriveMapSection } from './LandingPage';

const renderSection = () =>
  render(
    <MemoryRouter>
      <PublicLolodriveMapSection />
    </MemoryRouter>,
  );

describe('PublicLolodriveMapSection — hook contract', () => {
  beforeEach(() => {
    lolodriveAPI.listTerritories.mockReset();
    lolodriveAPI.listLoloPoints.mockReset();
    lolodriveAPI.listTerritories.mockResolvedValue({
      territories: [
        { code: 'GP', name: 'Guadeloupe' },
        { code: 'MQ', name: 'Martinique' },
      ],
    });
    lolodriveAPI.listLoloPoints.mockImplementation(({ territory } = {}) =>
      Promise.resolve({
        points: [
          { id: 'p1', code: 'LP-1', name: 'Point 1', territory: territory || 'GP', lat: 16, lng: -61 },
        ],
      }),
    );
  });

  test('au montage : 1 appel listTerritories + 1 appel listLoloPoints', async () => {
    renderSection();
    await waitFor(() => {
      expect(lolodriveAPI.listTerritories).toHaveBeenCalledTimes(1);
      expect(lolodriveAPI.listLoloPoints).toHaveBeenCalledTimes(1);
    });
    expect(lolodriveAPI.listLoloPoints).toHaveBeenLastCalledWith({ territory: undefined });
    await waitFor(() => {
      expect(screen.getByTestId('mock-map')).toHaveTextContent('map:1');
    });
  });

  test('changement de territoire : listLoloPoints relancé, listTerritories PAS rappelé', async () => {
    renderSection();
    await waitFor(() => expect(lolodriveAPI.listLoloPoints).toHaveBeenCalledTimes(1));

    await act(async () => {
      fireEvent.click(screen.getByText('set-gp'));
    });
    await waitFor(() => expect(lolodriveAPI.listLoloPoints).toHaveBeenCalledTimes(2));
    expect(lolodriveAPI.listLoloPoints).toHaveBeenLastCalledWith({ territory: 'GP' });

    await act(async () => {
      fireEvent.click(screen.getByText('set-mq'));
    });
    await waitFor(() => expect(lolodriveAPI.listLoloPoints).toHaveBeenCalledTimes(3));
    expect(lolodriveAPI.listLoloPoints).toHaveBeenLastCalledWith({ territory: 'MQ' });

    // Le contrat clé : territoires fetched une seule fois quoi qu'il arrive
    expect(lolodriveAPI.listTerritories).toHaveBeenCalledTimes(1);
  });

  test('pas de boucle infinie : 3 changements → exactement 4 appels listLoloPoints (1 mount + 3 changes)', async () => {
    renderSection();
    await waitFor(() => expect(lolodriveAPI.listLoloPoints).toHaveBeenCalledTimes(1));

    for (const btn of ['set-gp', 'set-mq', 'set-null']) {
      // eslint-disable-next-line no-await-in-loop
      await act(async () => { fireEvent.click(screen.getByText(btn)); });
    }
    // Wait for any pending state updates to settle
    await new Promise((r) => setTimeout(r, 100));
    expect(lolodriveAPI.listLoloPoints).toHaveBeenCalledTimes(4);
    expect(lolodriveAPI.listTerritories).toHaveBeenCalledTimes(1);
  });
});
