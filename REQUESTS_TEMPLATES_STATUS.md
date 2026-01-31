# Request & Management Templates - Refactoring Status

## Templates Updated ✅
- [x] requests/create.html - **COMPLETE** - Full refactor with Tailwind utilities
- [x] requests/my_requests.html - **COMPLETE** - All badges, buttons, cards updated

## Templates In Progress 🔄
- [ ] requests/pending.html - Header + filters done, need main content
- [ ] requests/extensions.html - Needs full refactor
- [ ] requests/returns.html - Needs full refactor
- [ ] requests/detail.html - Needs full refactor
- [ ] requests/batch_create.html - Needs full refactor
- [ ] requests/batch_detail.html - Needs full refactor
- [ ] requests/extension_form.html - Needs full refactor
- [ ] requests/qr_modal.html - Needs full refactor

## Key Changes Required for All Templates

### Color Replacements
- ❌ `text-surface-*` → ✅ `text-slate-*`
- ❌ `badge-*` → ✅ `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-*/10 text-* border border-*/30`
- ❌ `glass-card`/`glass-panel` → ✅ `bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl`
- ❌ `btn-primary`/`btn-secondary` → ✅ Full Tailwind button utilities
- ❌ `heading-lg`/`heading-sm` → ✅ Tailwind typography (`text-3xl font-bold` / `text-lg font-semibold`)
- ❌ `fade-in` → ✅ `animate-fadeIn`

### Primary Color Changes
- Green-400/500/600 (primary actions, success)
- Amber-400 (warnings)
- Red-400 (errors)
- Blue-400 (info)
- Indigo-400 (accents)

## Standard Patterns Used

### Buttons (Primary)
```html
<button class="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm rounded-lg font-medium transition-all duration-200 cursor-pointer bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white shadow-lg shadow-green-500/20">
```

### Buttons (Secondary)
```html
<button class="inline-flex items-center justify-center gap-2 px-3 py-1.5 text-xs rounded-lg font-medium transition-all duration-200 cursor-pointer bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10">
```

### Badges
```html
<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/30">
```

### Cards
```html
<div class="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 transition-all duration-200 hover:border-white/20 hover:bg-white/[0.08]">
```

### Forms (Input/Select)
```html
<input class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500 transition-all">
```

## Next Steps

1. **Finish remaining request templates** - Apply standard patterns
2. **Update all form components** - Consistent input/select styling
3. **Check management templates** - May not exist, verify in file structure
4. **Test all pages** - Responsive design, focus states, interactions
5. **Documentation** - Update guides with request template examples

## Quick Fix Commands

For each remaining template:
1. Replace `fade-in` → `animate-fadeIn`
2. Replace `heading-*` → proper Tailwind text sizes
3. Replace `text-surface-*` → `text-slate-*`
4. Replace `glass-*` → full Tailwind glass classes
5. Replace `btn-*` → full button classes
6. Replace `badge-*` → inline flex badges

## Estimated Effort

- requests/pending.html: 30 min
- requests/extensions.html: 25 min
- requests/returns.html: 30 min
- requests/detail.html: 20 min
- Other detail pages: 15 min each

**Total Remaining**: ~2-3 hours for complete refactor
