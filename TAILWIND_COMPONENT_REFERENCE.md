# Tailwind Component Reference for Admin Templates

This document provides the standard Tailwind patterns used across all admin templates.

## Button Patterns

### Primary Button (Green Gradient)
```html
<button class="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm rounded-lg font-medium transition-all duration-200 cursor-pointer bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white shadow-lg shadow-green-500/20">
  <i data-lucide="icon-name" class="w-4 h-4"></i>
  Button Text
</button>
```

### Secondary Button (Ghost Style)
```html
<button class="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm rounded-lg font-medium transition-all duration-200 cursor-pointer bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 hover:text-white">
  Button Text
</button>
```

### Small Button (Compact)
```html
<button class="inline-flex items-center justify-center gap-2 px-3 py-1.5 text-xs rounded-lg font-medium transition-all duration-200 cursor-pointer bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 text-white shadow-lg shadow-green-500/20">
  Small Button
</button>
```

## Badge Patterns

### Success Badge (Green)
```html
<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-500/10 text-green-400 border border-green-500/30">
  Success
</span>
```

### Warning Badge (Amber)
```html
<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
  Warning
</span>
```

### Danger Badge (Red)
```html
<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/30">
  Danger
</span>
```

### Info Badge (Blue/Indigo)
```html
<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">
  Info
</span>
```

## Card Patterns

### Standard Card (with Hover Effect)
```html
<div class="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 transition-all duration-200 hover:border-white/20 hover:bg-white/[0.08] hover:shadow-lg hover:shadow-green-500/10 hover:-translate-y-0.5">
  <!-- Card content -->
</div>
```

### Stat Card (with color-coded icon)
```html
<div class="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 transition-all duration-200 hover:border-white/20 hover:bg-white/[0.08] hover:shadow-lg hover:shadow-indigo-500/10 hover:-translate-y-0.5">
  <div class="flex items-start justify-between mb-4">
    <div class="w-12 h-12 rounded-lg bg-indigo-500/20 flex items-center justify-center">
      <i data-lucide="users" class="w-6 h-6 text-indigo-400"></i>
    </div>
  </div>
  <div>
    <p class="text-2xl font-bold text-white">123</p>
    <p class="text-sm text-slate-400 mt-1">Stat Label</p>
  </div>
</div>
```

### Alert/Warning Card (Red Theme)
```html
<div class="bg-red-500/5 backdrop-blur-lg border border-red-500/30 rounded-2xl p-6 transition-all duration-200 hover:border-red-500/50 hover:bg-red-500/10 hover:shadow-lg hover:shadow-red-500/10 hover:-translate-y-0.5">
  <!-- Content -->
</div>
```

## Form Elements

### Input Field
```html
<input type="text" 
       placeholder="Placeholder text"
       class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500 transition-all">
```

### Select Dropdown
```html
<select class="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500 transition-all">
  <option value="">Choose option</option>
</select>
```

### Form Label
```html
<label class="block text-sm font-medium text-slate-300 mb-3">
  Label Text
</label>
```

## Table Patterns

### Table Structure
```html
<div class="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <!-- Header -->
      <thead class="border-b border-white/10 bg-white/[0.02]">
        <tr>
          <th class="px-6 py-4 text-left font-semibold text-slate-300">Column</th>
        </tr>
      </thead>
      <!-- Body -->
      <tbody class="divide-y divide-white/5">
        <tr class="hover:bg-white/[0.03] transition-colors">
          <td class="px-6 py-4 text-white">Content</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

## List Items

### List Item with Avatar
```html
<div class="p-4 flex items-center gap-4 hover:bg-white/[0.02] transition-colors">
  <div class="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center text-white font-semibold flex-shrink-0">
    AB
  </div>
  <div class="flex-1">
    <p class="font-medium text-white">Name</p>
    <p class="text-sm text-slate-400">Subtitle</p>
  </div>
  <div class="text-right flex-shrink-0">
    <p class="font-semibold text-white">123</p>
    <p class="text-xs text-slate-500">unit</p>
  </div>
</div>
```

## Filter/Tab Patterns

### Tab Button (Underline Style)
```html
<div class="flex gap-2 mb-6 border-b border-white/10">
  <button @click="activeTab = 'tab1'" 
          :class="activeTab === 'tab1' ? 'border-b-2 border-green-500 text-white' : 'text-slate-400 hover:text-white'"
          class="px-4 py-2 text-sm font-medium transition-colors">
    Tab Label
  </button>
</div>
```

### Filter Select
```html
<div class="flex-1 min-w-[150px]">
  <label class="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
    Filter Label
  </label>
  <select class="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-green-500/50">
    <option value="">All Options</option>
  </select>
</div>
```

## Header Patterns

### Page Header
```html
<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
  <div>
    <h2 class="text-3xl font-bold tracking-tight text-white">Page Title</h2>
    <p class="text-slate-400 mt-1">Subtitle or description</p>
  </div>
  <!-- Optional action button -->
</div>
```

### Section Header
```html
<h3 class="text-lg font-semibold text-white mb-4">Section Title</h3>
```

## Empty State Pattern

```html
<div class="flex flex-col items-center justify-center p-12 text-center">
  <i data-lucide="icon-name" class="w-16 h-16 text-slate-600 mb-4"></i>
  <h3 class="text-lg font-semibold text-slate-300 mb-2">No items found</h3>
  <p class="text-sm text-slate-500">Helpful message about what's missing</p>
</div>
```

## Status Indicators

### Pulsing Animation
```html
<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/30 animate-pulse">
  {{ count }} overdue
</span>
```

## Color Mapping by Use Case

| Use Case | Color | Pattern |
|----------|-------|---------|
| Primary Actions | Green (500-600) | `bg-gradient-to-r from-green-600 to-green-500` |
| Secondary Actions | White/Slate | `bg-white/5 border border-white/10` |
| Success Status | Green | `bg-green-500/10 text-green-400 border border-green-500/30` |
| Warning Status | Amber | `bg-amber-500/10 text-amber-400 border border-amber-500/30` |
| Error Status | Red | `bg-red-500/10 text-red-400 border border-red-500/30` |
| Info Status | Blue/Indigo | `bg-blue-500/10 text-blue-400 border border-blue-500/30` |
| Icons/Accents | Color-matched | Same as status color, lighter shade |

## Spacing Standards

- **Container Padding**: `p-6` (standard), `p-4` (compact)
- **Gap Between Elements**: `gap-4` (standard), `gap-2` (compact)
- **Section Spacing**: `space-y-6` (container), `my-4` (individual)
- **Table Cells**: `px-6 py-4` (standard), `px-4 py-3` (compact)
- **Icon Margins**: `w-4 h-4` (standard), `w-5 h-5` (large)

## Border & Shadows

- **Glass Effect**: `backdrop-blur-lg border border-white/10`
- **Card Hover Shadow**: `hover:shadow-lg hover:shadow-COLOR-500/10`
- **Hover Lift**: `hover:-translate-y-0.5`
- **Subtle Dividers**: `border-white/5` or `border-white/10`

## Animation Classes

- **Fade In**: `animate-fadeIn` (defined in base.html)
- **Smooth Transitions**: `transition-all duration-200`
- **Pulsing**: `animate-pulse`
- **Hover Effects**: Always include `transition-all` with appropriate duration

