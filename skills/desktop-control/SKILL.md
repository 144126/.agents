---
name: desktop-control
description: Visually operate desktop applications on Ed's Sway laptop using screenshots, window focus, mouse clicks, and keyboard input. Use for native or Wine desktop apps when the user asks to interact with their interface; use agent-browser for browser tasks.
---

# Desktop control

Use this for the same visual workflow used to configure MetaTrader: inspect the screen, identify a control's coordinates, interact, then inspect the result. This is Ed's live desktop; actions and focus changes are visible to him. Avoid disrupting an active task and never trigger an irreversible action beyond what he requested.

1. Identify the window and workspace with `swaymsg -t get_tree` and focus it with `swaymsg '[con_id=ID] focus'` if needed. Window focus can switch workspaces. Check what is currently visible before acting.
2. Capture the current screen in memory with `grim -t png - | base64 -w0`. In `functions.exec`, pass the result directly as an image, not text or a saved file:

```js
const r = await tools.exec_command({cmd: 'grim -t png - | base64 -w0', max_output_tokens: 300000});
if (r.exit_code === 0 && r.output.startsWith('iVBOR')) image('data:image/png;base64,' + r.output);
else text(r.output);
```

3. Read the image yourself and estimate the target's screen coordinates. For Xwayland windows, `xdotool mousemove X Y click 1` clicks; `click 3` opens a context menu. `xdotool key KEY` sends a key. Use `swaymsg -t get_tree` to distinguish Xwayland `window_properties` from native Wayland `app_id`; `xdotool` may not control native Wayland apps. For those, use an installed Wayland-compatible input tool only if it supports the needed action.
4. Capture again and confirm the expected state before the next action. Re-check positions after menus, dialogs, scrolling, focus, window resizing, or workspace changes. Never infer that a click or save succeeded just because the command exited successfully. Do not test a trading hotkey by placing an order unless explicitly requested.

Trap: `wtype` entered garbled text and missed shortcuts in MetaEditor on this machine; do not use it blindly for text or control combinations. For Xwayland, `xdotool` successfully clicked MetaTrader menus and entered shortcut keys. Verify focus and the resulting text before saving; stop if typing is unreliable.

Screenshots can contain private information. Inspect only what is needed, keep screenshots in memory where possible, and obey Ed's storage rules before saving renders. For web pages or Electron apps, use the agent-browser skill and its browser-profile rules instead of taking over Ed's visible browser.
