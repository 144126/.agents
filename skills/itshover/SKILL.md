---
name: itshover
description: |
  Animated SVG icon library built with React and Motion (motion/react). Drop-in animated icons that work with Next.js, shadcn/ui, Tailwind CSS, and any React project. Use this skill whenever the user wants animated icons, hover-animated icons, interactive SVG icons, or mentions "itshover" — even if they just say they want "icons that animate on hover" or "motion icons for React." Also use this skill when the user needs to create new animated icon components following the itshover pattern, wants to contribute to the itshover open-source project, or wants to install and use animated icons in a React/Next.js/shadcn project.
compatibility:
  requires:
    - react
    - motion/react (npm package)
    - shadcn CLI (optional, for CLI-based installation)
---

# ItsHover: Animated Icon Library (React + Motion)

ItsHover is an open-source library of 186+ animated icons built with React and `motion/react` (the renamed framer-motion). Every icon animates on hover with intentional, crafted motion — not decoration.

## Table of Contents

- [Installation & Setup](#installation--setup)
- [Icon Usage](#icon-usage)
- [Customization](#customization)
- [Imperative Control (ref)](#imperative-control-ref)
- [CLI Installation (shadcn)](#cli-installation-shadcn)
- [Creating New Icons](#creating-new-icons)
- [Icon Registration Pipeline](#icon-registration-pipeline)
- [Contributing to ItsHover](#contributing-to-itshover)
- [Project Structure](#project-structure)

---

## Installation & Setup

The only dependency is `motion`:

```bash
npm install motion
```

That's it. Each icon is a self-contained React component — no CSS files, no global styles, no additional setup.

---

## Icon Usage

```tsx
"use client";
import GithubIcon from "@/components/ui/github-icon";

export default function Example() {
  return <GithubIcon className="h-6 w-6" />;
}
```

Hover over the icon to see the animation. Icons are client components — make sure the consuming component or parent is marked `"use client"`.

---

## Customization

Every icon accepts these props:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `size` | `number \| string` | `24` | Icon size in pixels or CSS string |
| `color` | `string` | `"currentColor"` | SVG stroke color |
| `strokeWidth` | `number` | `2` | SVG stroke width |
| `className` | `string` | `""` | Additional CSS classes |

Standard SVG props (`fill`, `onClick`, `aria-label`, etc.) also work since the component extends native `SVGProps<SVGSVGElement>`.

```tsx
<HeartIcon size={48} color="#ef4444" strokeWidth={1.5} className="my-custom-class" />
```

---

## Imperative Control (ref)

Use a ref to trigger animations programmatically (e.g., on click or after an async action).

```tsx
"use client";
import { useRef } from "react";
import GithubIcon from "@/components/ui/github-icon";
import type { AnimatedIconHandle } from "@/components/ui/types";

export default function Home() {
  const iconRef = useRef<AnimatedIconHandle>(null);

  return (
    <div className="flex flex-col items-center gap-4 p-10">
      <GithubIcon ref={iconRef} size={48} />
      <button onClick={() => iconRef.current?.startAnimation()}>
        Play
      </button>
      <button onClick={() => iconRef.current?.stopAnimation()}>
        Reset
      </button>
    </div>
  );
}
```

The ref handle exposes:
- `startAnimation()` — plays the hover animation
- `stopAnimation()` — resets to the rest state

---

## CLI Installation (shadcn)

Each icon is available as a shadcn registry component. Install individual icons via the CLI:

```bash
npx shadcn@latest add https://itshover.com/r/[icon-name].json
```

For example:

```bash
npx shadcn@latest add https://itshover.com/r/github-icon.json
```

This creates `components/ui/github-icon.tsx` and `components/ui/types.ts` in your project. Browse all 186+ icons at [itshover.com/icons](https://itshover.com/icons).

---

## Creating New Icons

Each icon follows a strict pattern. Start from this template:

```tsx
import { forwardRef, useImperativeHandle } from "react";
import type { AnimatedIconHandle, AnimatedIconProps } from "./types";
import { motion, useAnimate } from "motion/react";

const IconName = forwardRef<AnimatedIconHandle, AnimatedIconProps>(
  (
    { size = 24, color = "currentColor", strokeWidth = 2, className = "" },
    ref,
  ) => {
    const [scope, animate] = useAnimate();

    const start = async () => {
      await animate(
        ".icon-group",
        { scale: [1, 1.1, 1] },
        { duration: 0.4, ease: "easeInOut" },
      );
    };

    const stop = () => {
      animate(".icon-group", { scale: 1 }, { duration: 0.2, ease: "easeOut" });
    };

    useImperativeHandle(ref, () => ({
      startAnimation: start,
      stopAnimation: stop,
    }));

    return (
      <motion.svg
        ref={scope}
        onHoverStart={start}
        onHoverEnd={stop}
        xmlns="http://www.w3.org/2000/svg"
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={`inline-flex cursor-pointer items-center justify-center ${className}`}
        style={{ overflow: "visible" }}
      >
        <motion.path stroke="none" d="M0 0h24v24H0z" fill="none" />
        <motion.g className="icon-group" style={{ transformOrigin: "center" }}>
          {/* SVG paths go here */}
        </motion.g>
      </motion.svg>
    );
  },
);

IconName.displayName = "IconName";
export default IconName;
```

### Animation Rules

- Animate a **unique class name** scoped to that icon (e.g., `.heart`, `.star-fill`, `.github-icon`) — never reuse class names across icons.
- Always set `transformOrigin` (e.g., `"center"` or `"50% 50%"`) on animated elements so transforms are predictable.
- Use `useAnimate()` not `useAnimation()` — the `useAnimate` pattern lets you target child elements by class name from the root scope.
- The `start()` function should be `async` and use `await` so the animation plays sequentially. The `stop()` function should be synchronous (fire-and-forget reset).
- Duration range: 0.2s–0.6s. Easing: `"easeInOut"` or `"easeOut"`.
- Common animation patterns: scale pulsations (e.g., `[1, 1.15, 1, 1.25, 1]`), rotation wobbles (`[0, -5, 5, 0]`), opacity crossfades (`[0, 1]`), and parallel animations on different sub-elements.

### SVG Design Rules

- ViewBox is always `0 0 24 24`
- Stroke-based (like Tabler Icons), not filled (unless the design calls for fill elements)
- `strokeLinecap="round"`, `strokeLinejoin="round"`
- First child is always the hidden background path: `<path stroke="none" d="M0 0h24v24H0z" fill="none" />`
- Follow the Tabler Icons style: clean, simple, line-based, 2px stroke

---

## Icon Registration Pipeline

To register a new icon so it appears in the gallery and the shadcn registry, you need to touch 2 files (the third is auto-generated):

### 1. `icons/index.ts` — Add to ICON_LIST

```typescript
import YourIcon from "./your-icon";

export const ICON_LIST = [
  // ... existing icons
  {
    name: "your-icon",
    icon: YourIcon,
    keywords: ["your", "keywords", "searchable", "terms"],
    // optional: customProps for extra configuration
    customProps: [
      { name: "propName", type: "boolean", defaultValue: false },
    ],
  },
];
```

### 2. `lib/icons.ts` — Add to ICONS array for routing

```typescript
{ name: "your icon", path: "/icons/your-icon" }
```

### 3. Regenerate registry files

```bash
npm run registry:build
```

This runs the `scripts/generate-registry.ts` script which auto-generates `registry.json` and the per-icon JSON files in `public/r/`.

---

## Contributing to ItsHover

Before submitting, run all checks:

```bash
npm run check
npm run registry:build
```

### Coding Standards

- TypeScript for all new code
- Functional components with hooks
- `forwardRef` for all icon components
- Single-purpose, focused components
- Meaningful `keywords` for search
- Import order: 1) React/Next.js, 2) third-party, 3) internal
- Branch naming: `feature/your-feature-name` or `fix/bug-description`
- Commit format: `<type>: <subject>` (types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `chore`)

---

## Project Structure

```
itshover/
├── app/                  # Next.js App Router pages
├── components/           # Website UI components
├── icons/                # ★ Animated icon components (186+)
│   ├── index.ts          # ICON_LIST registry + all imports
│   ├── types.ts          # AnimatedIconProps, AnimatedIconHandle
│   └── [icon-name].tsx   # Individual icon components
├── lib/                  # Utilities (icons.ts, utils.ts, stars.ts)
├── actions/              # Server actions
├── public/r/             # Per-icon shadcn registry JSON files (auto-generated)
├── scripts/              # Registry generation scripts
└── registry.json         # Master shadcn registry (auto-generated)
```

### Key Types

```typescript
export interface AnimatedIconProps
  extends Omit<SVGProps<SVGSVGElement>, "ref" | "onAnimationStart" | "onAnimationEnd" | "onAnimationIteration" | "onDrag" | "onDragEnd" | "onDragEnter" | "onDragExit" | "onDragLeave" | "onDragOver" | "onDragStart" | "onDrop" | "values"> {
  size?: number | string;
  color?: string;
  strokeWidth?: number;
  className?: string;
}

export interface AnimatedIconHandle {
  startAnimation: () => void;
  stopAnimation: () => void;
}
```

---

## Resources

- **Website**: https://itshover.com
- **Icons gallery**: https://itshover.com/icons
- **GitHub repo**: https://github.com/itshover/itshover
- **API docs**: `icons/types.ts` in the repo
- **Architecture**: `ARCHITECTURE.md` in the repo
- **Contributing**: `CONTRIBUTING.md` in the repo
- **Icon inspiration**: https://tabler-icons.io (matching design style)
