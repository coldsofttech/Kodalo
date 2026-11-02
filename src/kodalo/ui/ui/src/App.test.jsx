import { afterEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App.jsx';
import { createBackend, makeBrand, mockApi, typeInto } from './testing.js';

afterEach(() => vi.unstubAllGlobals());

describe('App', () => {
  it('opens on the brands page and keeps unsaved edits when you visit About', async () => {
    const backend = createBackend([makeBrand('b1', 'Main', true)]);
    mockApi(backend.handler);
    render(<App />);
    const nav = screen.getByRole('navigation', { name: 'Main' });
    expect(within(nav).getByRole('button', { name: 'Brands' })).toHaveAttribute(
      'aria-current',
      'page',
    );

    typeInto(await screen.findByLabelText('Brand name'), 'Edited');
    await userEvent.click(within(nav).getByRole('button', { name: 'About' }));
    expect(screen.getByRole('heading', { name: 'About Kodalo' })).toBeVisible();
    expect(within(nav).getByRole('button', { name: 'About' })).toHaveAttribute(
      'aria-current',
      'page',
    );

    await userEvent.click(within(nav).getByRole('button', { name: 'Brands' }));
    expect(screen.getByLabelText('Brand name')).toHaveProperty('value', 'Edited');
  });

  it.each(['Canvases', 'Palettes', 'Layouts'])(
    'opens %s from the sub-menu under Brands',
    async (label) => {
      const backend = createBackend([makeBrand('b1', 'Main', true)]);
      mockApi(backend.handler);
      render(<App />);
      const nav = screen.getByRole('navigation', { name: 'Main' });
      await userEvent.click(within(nav).getByRole('button', { name: label }));
      expect(screen.getByRole('heading', { name: label })).toBeVisible();
      expect(within(nav).getByRole('button', { name: label })).toHaveAttribute(
        'aria-current',
        'page',
      );
    },
  );

  it('has no accessibility violations', async () => {
    const backend = createBackend([makeBrand('b1', 'Main', true)]);
    mockApi(backend.handler);
    const { container } = render(<App />);
    await screen.findByRole('heading', { name: 'Preview' });
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('About page', () => {
  async function openAbout(backend = createBackend([makeBrand('b1', 'Main', true)])) {
    mockApi(backend.handler);
    render(<App />);
    await userEvent.click(
      within(screen.getByRole('navigation', { name: 'Main' })).getByRole('button', {
        name: 'About',
      }),
    );
    return backend;
  }

  it('explains the product and shows the version', async () => {
    await openAbout();

    expect(await screen.findByText('Version 1.2.3')).toBeInTheDocument();
    expect(screen.getByText(/on-brand Instagram posts/)).toBeInTheDocument();
  });

  it('runs the installation checks on request', async () => {
    await openAbout();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Check installation'));

    const table = await screen.findByRole('table', { name: 'Installation checks' });
    expect(within(table).getByRole('rowheader', { name: 'Python' })).toBeInTheDocument();
    expect(within(table).getByText('3.11.9 (requires 3.11+)')).toBeInTheDocument();
    expect(within(table).getByText('Warning')).toBeInTheDocument();
    expect(screen.getByText('Everything looks good.')).toBeInTheDocument();
  });

  it('says when a required check fails', async () => {
    const backend = createBackend([makeBrand('b1', 'Main', true)]);
    backend.state.doctor = {
      healthy: false,
      checks: [{ name: 'Database', ok: false, detail: 'newer than this Kodalo', required: true }],
    };
    await openAbout(backend);
    await userEvent.click(screen.getByText('Check installation'));

    expect(await screen.findByText('One or more required checks failed.')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('shows an error when the check cannot run', async () => {
    const backend = createBackend([makeBrand('b1', 'Main', true)]);
    await openAbout(backend);
    mockApi((method, path, body) =>
      path.endsWith('/doctor')
        ? [503, { detail: 'The local data cannot be opened.' }]
        : backend.handler(method, path, body),
    );
    await userEvent.click(screen.getByText('Check installation'));

    expect(await screen.findByRole('alert')).toHaveTextContent('cannot be opened');
  });

  it('has no accessibility violations with results shown', async () => {
    await openAbout();
    await userEvent.click(screen.getByText('Check installation'));
    await screen.findByRole('table');
    expect(await axe(document.body)).toHaveNoViolations();
  });
});
