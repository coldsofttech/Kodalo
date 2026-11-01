// Fluent UI Web Components: registers the elements the app uses and follows the system theme.
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

provideFluentDesignSystem().register(
  fluentButton(),
  fluentNumberField(),
  fluentSwitch(),
  fluentTextField(),
);

const dark = window.matchMedia('(prefers-color-scheme: dark)');

function applyTheme() {
  baseLayerLuminance.setValueFor(
    document.body,
    dark.matches ? StandardLuminance.DarkMode : StandardLuminance.LightMode,
  );
}

applyTheme();
dark.addEventListener('change', applyTheme);
