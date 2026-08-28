const STORAGE_KEY = 'zeteo-theme';

export type Theme = 'light' | 'dark';

function systemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function storedTheme(): Theme | null {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'light' || stored === 'dark' ? stored : null;
}

function applyEffective(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

/** Applies the effective theme (stored override, else OS setting) and returns it. */
export function initTheme(): Theme {
  const effective = storedTheme() ?? systemTheme();
  applyEffective(effective);
  return effective;
}

/** Watches the OS setting so the effective theme stays live while no override is stored. */
export function watchSystemTheme(onChange: (theme: Theme) => void): () => void {
  const mql = window.matchMedia('(prefers-color-scheme: dark)');
  const handler = () => {
    if (!storedTheme()) {
      const effective = systemTheme();
      applyEffective(effective);
      onChange(effective);
    }
  };
  mql.addEventListener('change', handler);
  return () => mql.removeEventListener('change', handler);
}

export function toggleTheme(current: Theme): Theme {
  const next: Theme = current === 'dark' ? 'light' : 'dark';
  localStorage.setItem(STORAGE_KEY, next);
  applyEffective(next);
  return next;
}
