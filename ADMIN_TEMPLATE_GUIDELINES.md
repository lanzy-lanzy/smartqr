# Admin Template Implementation Guidelines

This document provides guidelines for creating new admin templates that maintain consistency with the unified design system.

## Quick Start

When creating a new admin template, follow these key principles:

### 1. Base Structure
```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Page Name - Smart Supply{% endblock %}
{% block page_title %}Page Name{% endblock %}

{% block content %}
<div class="space-y-6 animate-fadeIn">
  <!-- Your content here -->
</div>
{% endblock %}
```

### 2. Always Use These Utilities
✅ **DO**
- Use `bg-white/5 backdrop-blur-lg border border-white/10` for glass effect
- Use `text-slate-*` for text colors (not `text-surface-*`)
- Use `text-white` for primary text, `text-slate-300/400` for secondary
- Use `animate-fadeIn` for page entrance animations
- Use `space-y-6` for vertical spacing between sections

❌ **DON'T**
- Use custom CSS classes like `glass-panel`, `heading-lg`, `stat-card`
- Use `text-surface-*` colors
- Use `btn-primary`, `btn-secondary` classes
- Use `badge-*` classes
- Create new custom CSS files

### 3. Color Consistency

#### Primary Brand Colors
```tailwind
Green (Primary):
- Buttons: from-green-600 to-green-500
- Hover: from-green-500 to-green-400
- Shadow: shadow-green-500/20
- Icons: text-green-400

For secondary emphasis:
- Indigo: text-indigo-400, bg-indigo-500/20
- Blue: text-blue-400, bg-blue-500/20
- Amber: text-amber-400, bg-amber-500/20
- Red: text-red-400, bg-red-500/20
```

#### Text Colors
```tailwind
White: text-white              (headings, primary text)
Light: text-slate-300         (secondary text)
Medium: text-slate-400        (tertiary text, labels)
Dark: text-slate-500          (smallest/helper text)
Muted: text-slate-600         (disabled state)
```

### 4. Standard Component Patterns

#### Page Header with Action Button
```html
<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
  <div>
    <h2 class="text-3xl font-bold tracking-tight text-white">Page Title</h2>
    <p class="text-slate-400 mt-1">Brief description</p>
  </div>
  <a href="..." class="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 cursor-pointer bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white shadow-lg shadow-green-500/20">
    <i data-lucide="plus" class="w-4 h-4"></i>
    Action
  </a>
</div>
```

#### Stat Card with Icon
```html
<div class="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 transition-all duration-200 hover:border-white/20 hover:bg-white/[0.08] hover:shadow-lg hover:shadow-indigo-500/10 hover:-translate-y-0.5">
  <div class="flex items-start justify-between mb-4">
    <div class="w-12 h-12 rounded-lg bg-indigo-500/20 flex items-center justify-center">
      <i data-lucide="icon" class="w-6 h-6 text-indigo-400"></i>
    </div>
  </div>
  <div>
    <p class="text-2xl font-bold text-white">123</p>
    <p class="text-sm text-slate-400 mt-1">Label</p>
  </div>
</div>
```

#### Data Table
```html
<div class="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead class="border-b border-white/10 bg-white/[0.02]">
        <tr>
          <th class="px-6 py-4 text-left font-semibold text-slate-300">Column</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-white/5">
        <tr class="hover:bg-white/[0.03] transition-colors">
          <td class="px-6 py-4">Content</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

#### Filter Section
```html
<div class="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-4">
  <form method="GET" class="flex flex-wrap items-end gap-4">
    <div class="flex-1 min-w-[150px]">
      <label class="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Filter</label>
      <select class="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-green-500/50">
        <option>Option</option>
      </select>
    </div>
  </form>
</div>
```

### 5. Responsive Design Checklist

All templates should handle these breakpoints:
- **Mobile** (< 640px): Stack vertically, reduce padding to `p-4`
- **Tablet** (640px - 1024px): 2-column layouts start
- **Desktop** (> 1024px): Full multi-column layouts

Use these patterns:
```tailwind
grid-cols-1 sm:grid-cols-2 lg:grid-cols-4    (for stat cards)
flex-col sm:flex-row                           (for horizontal layouts)
hidden md:flex                                 (for desktop-only elements)
w-full sm:w-auto                              (for responsive widths)
```

### 6. Interactive Elements

#### Buttons
```html
<!-- Primary (Green) -->
<button class="...bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400...">

<!-- Secondary (Ghost) -->
<button class="...bg-white/5 border border-white/10 hover:bg-white/10...">

<!-- Danger -->
<button class="...bg-red-500/10 text-red-400 border border-red-500/30...">
```

#### Links
```html
<a href="..." class="text-green-400 hover:text-green-300 transition-colors font-medium">Link Text</a>
```

#### Form Focus States
```html
input, select, textarea: focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500
```

### 7. Status Indicators

```html
<!-- Success -->
<span class="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/30">Success</span>

<!-- Warning -->
<span class="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">Warning</span>

<!-- Error -->
<span class="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/30">Error</span>

<!-- Info -->
<span class="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">Info</span>
```

### 8. Empty States

Always provide helpful empty states:
```html
<div class="flex flex-col items-center justify-center p-12 text-center">
  <i data-lucide="icon-name" class="w-16 h-16 text-slate-600 mb-4"></i>
  <h3 class="text-lg font-semibold text-slate-300 mb-2">No items found</h3>
  <p class="text-sm text-slate-500">Description or call to action</p>
</div>
```

### 9. Typography Hierarchy

```tailwind
Page Title:      text-3xl font-bold tracking-tight text-white
Section Title:   text-lg font-semibold text-white
Subsection:      text-base font-medium text-white
Body:            text-sm text-slate-300
Caption:         text-xs text-slate-500
Code:            text-green-400 (for technical terms)
```

### 10. Spacing Standards

```tailwind
Container gaps:     gap-6 (large), gap-4 (standard), gap-2 (compact)
Section spacing:    space-y-6 (between major sections)
Grid gaps:         gap-4 lg:gap-6 (responsive)
Padding:           p-6 (cards), p-4 (panels), p-2 (tight)
Margin:            my-4, my-6 (vertical spacing)
```

## Common Mistakes to Avoid

❌ **Using custom CSS classes**
- Instead of `glass-panel`, use `bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl`

❌ **Mixing color palettes**
- Don't mix `text-surface-*` with `text-slate-*`
- Don't mix `primary-*` with `green-*`

❌ **Inconsistent button styling**
- Always include shadow: `shadow-lg shadow-green-500/20`
- Always include hover effects: `hover:from-green-500 hover:to-green-400`

❌ **Missing focus states**
- All interactive elements need: `focus:outline-none focus:ring-2 focus:ring-green-500/50`

❌ **Poor mobile layout**
- Test with `sm:` and `lg:` breakpoints
- Ensure proper stacking on mobile

## Validation Checklist

Before submitting a new admin template:

- [ ] All styling uses Tailwind utilities only (no custom CSS)
- [ ] Text uses `text-slate-*` colors, never `text-surface-*`
- [ ] All cards use `bg-white/5 backdrop-blur-lg` glass effect
- [ ] Primary actions use green gradient: `from-green-600 to-green-500`
- [ ] All buttons have hover effects: `hover:-translate-y-0.5`
- [ ] All badges follow the pattern: `bg-*/10 text-* border border-*/30`
- [ ] Page header follows standard pattern with title and subtitle
- [ ] Tables have proper styling: `divide-y divide-white/5`
- [ ] Empty states are informative and well-designed
- [ ] Responsive breakpoints tested (`sm:`, `lg:`)
- [ ] Page uses `animate-fadeIn` for entrance
- [ ] Page container has `space-y-6`
- [ ] All interactive elements have transition effects
- [ ] Focus states are visible (for accessibility)

## Using the Tailwind Component Reference

Refer to `TAILWIND_COMPONENT_REFERENCE.md` for copy-paste patterns of:
- Button styles (primary, secondary, small)
- Badge patterns (all color variants)
- Card patterns (standard, stat, alert)
- Form elements (input, select, label)
- Table structure
- List items with avatars
- Filter and tab patterns
- Header patterns
- Empty state patterns
- Status indicators

## Questions?

If you're unsure about styling for a new component:
1. Check `TAILWIND_COMPONENT_REFERENCE.md` for similar patterns
2. Look at existing admin templates for examples
3. Use Tailwind's official documentation: https://tailwindcss.com

## Future Updates

As we expand the design system:
- New components will be added to the reference guide
- Color adjustments will be communicated via update
- All templates will be updated simultaneously for consistency
