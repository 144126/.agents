---
name: wydsc
description: >
  Provides short, concise answers about Waydroid keyboard shortcuts and keybindings.
  Trigger this skill whenever the user's query contains 'wydsc' or asks what a specific
  keyboard shortcut does in Waydroid. Answers must be extremely brief — just state the
  key/combo, what it does, and nothing more. No explanations, no context, no preamble.
  One or two lines max. Only use this for Waydroid shortcut lookups; if the user asks
  something broader, just answer briefly about the shortcut and stop.
---

# wydsc — Waydroid Shortcuts

When the user asks `wydsc <query>`, give a **one-line answer** with just the shortcut and what it does. No explanations, no markdown tables unless many results are needed, no "here is the answer". Just state it.

## Built-in shortcuts (inside Waydroid window)

- **Esc** → Back button (Android `KEYCODE_BACK`)
- **Ctrl+Space** → Switch physical keyboard layout (when 2+ layouts configured in Android settings)
- **Left Alt** (tap once) → Reset physical keyboard detection when keyboard stops responding
- **Alt+F4** → Close/focus escape — not Android-native, handled by Wayland compositor

## Android physical keyboard shortcuts (work inside Waydroid)

These are standard Android hardware-keyboard shortcuts that work because Waydroid exposes the keyboard as `wayland_keyboard`:

- **Win/Meta + Enter** → Home screen
- **Win/Meta + N** → Show notifications
- **Win/Meta + L** → Lock
- **Alt+Tab** → App switcher (hold Alt, tab through)
- **Alt+Tab → Del/Backspace** → Close selected app from switcher
- **F3** → Recent apps (on some devices)
- **Ctrl+A/C/V/X/Z/Y** → Select all / copy / paste / cut / undo / redo

## Waydroid Helper keymapper (third-party)

- **F1** → Toggle Edit Mode / Mapping Mode
- **Ctrl+Q** → Quit
- **?** → Show shortcuts overlay

## Phantom keymapper (third-party)

- **F1** → Toggle mouse routing
- **F8** → Toggle capture
- **F9** → Toggle pause
- **F10** → Toggle debug preview
- **F2** → Shutdown daemon

## Layout switching

- **Ctrl+Space** → Switch physical keyboard layout (requires 2+ layouts in Android Settings > System > Languages & input > Physical keyboard)

## Disable on-screen keyboard

```
Settings > System > Languages & input > Physical keyboard > Use on-screen keyboard
```
Or via shell: `sudo waydroid shell settings put secure show_ime_with_hard_keyboard 0`

## Related props

- `waydroid prop set persist.waydroid.fake_touch "com.example.app"` → Mouse acts as touch
- `waydroid prop set waydroid.keyboard_layout english` → Set keyboard layout
