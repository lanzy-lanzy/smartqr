# Quick Reference - Admin Templates

## Color Palette Cheat Sheet

```
PRIMARY (Green)           SECONDARY (Slate)        STATUS COLORS
from-green-600            bg-white/5               Success: green-*
to-green-500              border-white/10          Warning: amber-*
text-green-400            text-slate-300           Error: red-*
bg-green-500/20           text-slate-400           Info: indigo-*/blue-*
text-green-400                                     Disabled: slate-600
```

## Most Common Patterns (Copy & Paste)

### 1. Page Header
```html
<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
  <div>
    <h2 class="text-3xl font-bold tracking-tight text-white">Title</h2>
    <p class="text-slate-400 mt-1">Subtitle</p>
  </div>
</div>
```

### 2. Primary Button
```html
<button class="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm rounded-lg font-medium transition-all duration-200 cursor-pointer bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white shadow-lg shadow-green-500/20">
  Button Text
</button>
```

### 3. Card Container
```html
<div class="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 transition-all duration-200 hover:border-white/20 hover:bg-white/[0.08] hover:shadow-lg hover:shadow-green-500/10 hover:-translate-y-0.5">
  <!-- Content -->
</div>
```

### 4. Success Badge
```html
<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/30">
  Success
</span>
```

### 5. Table Structure
```html
<div class="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
  <table class="w-full text-sm">
    <thead class="border-b border-white/10 bg-white/[0.02]">
      <tr><th class="px-6 py-4 text-left font-semibold text-slate-300">Column</th></tr>
    </thead>
    <tbody class="divide-y divide-white/5">
      <tr class="hover:bg-white/[0.03] transition-colors">
        <td class="px-6 py-4">Data</td>
      </tr>
    </tbody>
  </table>
</div>
```

### 6. Input Field
```html
<input type="text" placeholder="Text..."
       class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500 transition-all">
```

### 7. Select Dropdown
```html
<select class="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500 transition-all">
  <option>Option</option>
</select>
```

### 8. Stat Card
```html
<div class="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 transition-all duration-200 hover:border-white/20 hover:bg-white/[0.08] hover:shadow-lg hover:shadow-indigo-500/10 hover:-translate-y-0.5">
  <div class="flex items-start justify-between mb-4">
    <div class="w-12 h-12 rounded-lg bg-indigo-500/20 flex items-center justify-center">
      <i data-lucide="users" class="w-6 h-6 text-indigo-400"></i>
    </div>
  </div>
  <p class="text-2xl font-bold text-white">123</p>
  <p class="text-sm text-slate-400 mt-1">Label</p>
</div>
```

### 9. Empty State
```html
<div class="flex flex-col items-center justify-center p-12 text-center">
  <i data-lucide="inbox" class="w-16 h-16 text-slate-600 mb-4"></i>
  <h3 class="text-lg font-semibold text-slate-300 mb-2">No items</h3>
  <p class="text-sm text-slate-500">Message</p>
</div>
```

### 10. List Item with Avatar
```html
<div class="p-4 flex items-center gap-4 hover:bg-white/[0.02] transition-colors">
  <div class="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center text-white font-semibold flex-shrink-0">AB</div>
  <div class="flex-1">
    <p class="font-medium text-white">Name</p>
    <p class="text-sm text-slate-400">Subtitle</p>
  </div>
  <p class="font-semibold text-white">123</p>
</div>
```

## Status Badge Quick Variations

```html
<!-- Green (Success) -->
<span class="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/30">✓ Success</span>

<!-- Amber (Warning) -->
<span class="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">⚠ Warning</span>

<!-- Red (Error) -->
<span class="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/30">✗ Error</span>

<!-- Blue (Info) -->
<span class="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">ℹ Info</span>

<!-- Slate (Neutral) -->
<span class="inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/30">○ Neutral</span>
```

## Button Size Variations

```html
<!-- Large -->
<button class="...px-6 py-3 text-base...">Large Button</button>

<!-- Standard (use this mostly) -->
<button class="...px-4 py-2.5 text-sm...">Standard Button</button>

<!-- Small -->
<button class="...px-3 py-1.5 text-xs...">Small Button</button>
```

## Text Color Variations

```html
<p class="text-white">Primary heading</p>
<p class="text-slate-300">Secondary text</p>
<p class="text-slate-400">Tertiary/label text</p>
<p class="text-slate-500">Helper/small text</p>
<p class="text-green-400">Success/accent</p>
<p class="text-red-400">Error/warning accent</p>
```

## Spacing Quick Reference

```
Container padding:     p-6          (standard)
Compact padding:       p-4          (tight spaces)
Gap between elements:  gap-4        (standard)
Compact gap:           gap-2        (tight)
Section spacing:       space-y-6    (vertical)
Icon sizes:            w-4 h-4      (small), w-6 h-6 (medium), w-8 h-8 (large)
Rounded corners:       rounded-2xl  (large cards), rounded-xl (panels), rounded-lg (elements)
```

## Icon Color Combinations

```html
<!-- Indigo Icon with Indigo Background -->
<div class="w-12 h-12 rounded-lg bg-indigo-500/20 flex items-center justify-center">
  <i data-lucide="icon" class="w-6 h-6 text-indigo-400"></i>
</div>

<!-- Green Icon with Green Background -->
<div class="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center">
  <i data-lucide="icon" class="w-6 h-6 text-green-400"></i>
</div>

<!-- Red Icon with Red Background (for alerts) -->
<div class="w-12 h-12 rounded-lg bg-red-500/20 flex items-center justify-center">
  <i data-lucide="icon" class="w-6 h-6 text-red-400"></i>
</div>
```

## Common Responsive Patterns

```html
<!-- Stack on mobile, side-by-side on desktop -->
<div class="flex flex-col sm:flex-row gap-4">

<!-- 1 col mobile, 2 col tablet, 4 col desktop -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">

<!-- Hidden on mobile, visible on tablet+ -->
<div class="hidden sm:flex">

<!-- Full width on mobile, auto on desktop -->
<div class="w-full sm:w-auto">
```

## Do's and Don'ts

✅ **DO** - Use these classes
- `text-slate-*`
- `bg-white/5`
- `border-white/10`
- `rounded-2xl`
- `gap-4`
- `p-6`

❌ **DON'T** - Avoid these classes
- `text-surface-*`
- `glass-panel`
- `glass-card`
- `btn-primary`
- `heading-lg`
- `badge-success`

## Files to Reference

1. Existing templates (copy their patterns):
   - `templates/admin/users.html`
   - `templates/admin/departments.html`
   - `templates/admin/import.html`

2. Documentation:
   - `TAILWIND_COMPONENT_REFERENCE.md` (copy-paste)
   - `ADMIN_TEMPLATE_GUIDELINES.md` (rules)
   - `ADMIN_TEMPLATES_UNIFIED.md` (details)

## Pro Tips

1. **Always include transitions**: `transition-all duration-200`
2. **Always add hover effects**: `hover:border-white/20 hover:bg-white/[0.08] hover:shadow-lg`
3. **Always test mobile**: Use `sm:` and `lg:` breakpoints
4. **Always use green**: For primary actions and success states
5. **Always check focus states**: Especially on form inputs
6. **Always include icons**: They improve visual hierarchy
7. **Always space properly**: Use `gap-4` or `space-y-6` consistently
8. **Always be consistent**: Copy patterns from existing templates

## Quick Debug Checklist

- [ ] Colors are `slate-*` not `surface-*`
- [ ] Buttons have gradient: `from-green-600 to-green-500`
- [ ] Cards have glass effect: `bg-white/5 backdrop-blur-lg border border-white/10`
- [ ] Inputs have green focus: `focus:ring-green-500/50`
- [ ] Badges have matching colors: `bg-*/10 text-* border-*/30`
- [ ] Tables have dividers: `divide-y divide-white/5`
- [ ] Responsive breakpoints used: `sm:` and `lg:`
- [ ] Hover effects present: `hover:` states defined
- [ ] Text hierarchy clear: Different `text-*` sizes and colors
- [ ] Spacing consistent: Using `gap-4`, `p-6`, `space-y-6`

## Emergency Help

"My page doesn't look right!"

1. Check file → `TAILWIND_COMPONENT_REFERENCE.md`
2. Compare to → Existing admin template
3. Look for → `text-surface-*` or custom classes
4. Replace with → `text-slate-*` or Tailwind utilities
5. Test → On mobile, tablet, desktop

"What color should I use?"

- Primary action? → Green (500-600)
- Success? → Green
- Warning? → Amber
- Error? → Red
- Info? → Indigo/Blue
- Text? → White/Slate-300/Slate-400

"How do I make a component?"

1. Copy pattern from reference or existing template
2. Adapt colors if needed
3. Test responsiveness
4. Add hover effects
5. Check focus states

---

**Last Updated**: January 29, 2026  
**Status**: ✅ All Templates Unified  
**Customization**: Fully Tailwind-based
