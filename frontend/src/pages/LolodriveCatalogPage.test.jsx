/**
 * Tests verrouillant le contrat hooks de LolodriveCatalogPage :
 *   • Au montage (auth) : 1 appel listTerritories + 1 appel catalogProducts + 1 appel listLoloPoints
 *   • Changement de filter : catalogProducts + listLoloPoints re-appelés, listTerritories PAS rappelé
 *   • Changement de territory : idem
 *   • Si non-auth : navigate('/connexion') ; aucun appel catalogue
 *
 * Si quelqu'un fusionne à nouveau les fetchs en un seul effet sans gérer
 * les deps, ou re-fetch les territoires sur chaque changement, ces tests
 * échouent immédiatement.
 */
import React from 'react';
import { render, screen, act, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// ----------------- Mocks -----------------

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => {
  const real = jest.requireActual('react-router-dom');
  return {
    ...real,
    useNavigate: () => mockNavigate,
  };
});

jest.mock('../services/api', () => {
  const listTerritories = jest.fn();
  const listLoloPoints = jest.fn();
  const catalogProducts = jest.fn();
  const isAuthenticated = jest.fn(() => true);
  return {
    __esModule: true,
    authAPI: { isAuthenticated },
    lolodriveAPI: { listTerritories, listLoloPoints, catalogProducts },
  };
});

// Sonner toasts not relevant for hooks tests
jest.mock('sonner', () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

// LolodriveLayout pulls heavy NavBar/Footer styling; stub to a minimal passthrough.
jest.mock('../components/LolodriveLayout', () => {
  const React = jest.requireActual('react');
  return {
    __esModule: true,
    default: ({ children, actions }) =>
      React.createElement('div', { 'data-testid': 'layout-stub' }, actions, children),
    SectionCard: ({ children }) => React.createElement('div', null, children),
    Badge: ({ children }) => React.createElement('span', null, children),
    fmtEUR: (cents) => `${(cents / 100).toFixed(2)} €`,
  };
});

// Controllable TerritorySelector
jest.mock('../components/TerritorySelector', () => ({
  __esModule: true,
  default: ({ onChange, value }) => (
    <div>
      <span data-testid="current-territory">{value || 'null'}</span>
      <button type="button" onClick={() => onChange('GP')}>set-gp</button>
      <button type="button" onClick={() => onChange('MQ')}>set-mq</button>
    </div>
  ),
  getInitialTerritory: () => null,
}));

import { lolodriveAPI, authAPI } from '../services/api';
import LolodriveCatalogPage from './LolodriveCatalogPage';

const renderPage = () =>
  render(
    <MemoryRouter>
      <LolodriveCatalogPage />
    </MemoryRouter>,
  );

describe('LolodriveCatalogPage — hook contract', () => {
  beforeEach(() => {
    lolodriveAPI.listTerritories.mockReset();
    lolodriveAPI.listLoloPoints.mockReset();
    lolodriveAPI.catalogProducts.mockReset();
    authAPI.isAuthenticated.mockReset();
    authAPI.isAuthenticated.mockReturnValue(true);
    mockNavigate.mockClear();
    lolodriveAPI.listTerritories.mockResolvedValue({
      territories: [{ code: 'GP', name: 'Guadeloupe' }],
    });
    lolodriveAPI.listLoloPoints.mockImplementation(({ territory } = {}) =>
      Promise.resolve({
        points: [{ id: 'p1', code: 'LP-1', name: 'Point 1', territory: territory || 'GP' }],
      }),
    );
    lolodriveAPI.catalogProducts.mockImplementation((catalog_type, territory) =>
      Promise.resolve({
        products: [{ sku: 'SKU-1', name: 'Item', display_price_cents: 100, catalog_type: 'NORMAL' }],
        pass_active: false,
        _catalog_type: catalog_type,
        _territory: territory,
      }),
    );
  });

  test('non authentifié → redirection /connexion, aucun fetch catalogue', async () => {
    authAPI.isAuthenticated.mockReturnValueOnce(false);
    renderPage();
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/connexion'));
    expect(lolodriveAPI.catalogProducts).not.toHaveBeenCalled();
    expect(lolodriveAPI.listLoloPoints).not.toHaveBeenCalled();
  });

  test('au montage authentifié : 1 listTerritories + 1 catalogProducts + 1 listLoloPoints', async () => {
    renderPage();
    await waitFor(() => {
      expect(lolodriveAPI.listTerritories).toHaveBeenCalledTimes(1);
      expect(lolodriveAPI.catalogProducts).toHaveBeenCalledTimes(1);
      expect(lolodriveAPI.listLoloPoints).toHaveBeenCalledTimes(1);
    });
    expect(lolodriveAPI.catalogProducts).toHaveBeenLastCalledWith(undefined, undefined);
    expect(lolodriveAPI.listLoloPoints).toHaveBeenLastCalledWith({ territory: undefined });
  });

  test('changement de territoire : catalogProducts + listLoloPoints re-fetched ; listTerritories pas rappelé', async () => {
    renderPage();
    await waitFor(() => expect(lolodriveAPI.catalogProducts).toHaveBeenCalledTimes(1));

    await act(async () => { fireEvent.click(screen.getByText('set-gp')); });

    await waitFor(() => {
      expect(lolodriveAPI.catalogProducts).toHaveBeenCalledTimes(2);
      expect(lolodriveAPI.listLoloPoints).toHaveBeenCalledTimes(2);
    });
    expect(lolodriveAPI.catalogProducts).toHaveBeenLastCalledWith(undefined, 'GP');
    expect(lolodriveAPI.listLoloPoints).toHaveBeenLastCalledWith({ territory: 'GP' });

    // Contrat clé
    expect(lolodriveAPI.listTerritories).toHaveBeenCalledTimes(1);
  });

  test('pas de boucle infinie : 2 changements → exactement 3 appels catalogProducts (1 mount + 2 changes)', async () => {
    renderPage();
    await waitFor(() => expect(lolodriveAPI.catalogProducts).toHaveBeenCalledTimes(1));

    for (const btn of ['set-gp', 'set-mq']) {
      // eslint-disable-next-line no-await-in-loop
      await act(async () => { fireEvent.click(screen.getByText(btn)); });
    }
    // Laisser passer les éventuels re-render
    await new Promise((r) => setTimeout(r, 100));
    expect(lolodriveAPI.catalogProducts).toHaveBeenCalledTimes(3);
    expect(lolodriveAPI.listLoloPoints).toHaveBeenCalledTimes(3);
    expect(lolodriveAPI.listTerritories).toHaveBeenCalledTimes(1);
  });
});
