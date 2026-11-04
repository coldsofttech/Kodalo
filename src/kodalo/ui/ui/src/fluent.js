// Fluent UI Web Components: registers the elements the app uses and follows the chosen theme.
// Only main.jsx imports this file, so tests render the app without upgrading the elements.
import {
  baseLayerLuminance,
  fluentButton,
  fluentNumberField,
  fluentSwitch,
  fluentTextField,
  provideFluentDesignSystem,
  StandardLuminance,
} from '@fluentui/web-components';
import { onThemeChange } from './theme.js';

provideFluentDesignSystem().register(
  fluentButton(),
  fluentNumberField(),
  fluentSwitch(),
  fluentTextField(),
);

const system = window.matchMedia('(prefers-color-scheme: dark)');
let theme = 'system';

function applyTheme() {
  const dark = theme === 'dark' || (theme === 'system' && system.matches);
  baseLayerLuminance.setValueFor(
    document.body,
    dark ? StandardLuminance.DarkMode : StandardLuminance.LightMode,
  );
}

onThemeChange((value) => {
  theme = value;
  applyTheme();
});
system.addEventListener('change', applyTheme);
