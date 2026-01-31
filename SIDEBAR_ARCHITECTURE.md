# Sidebar Architecture Refactoring

## Overview
The sidebar has been refactored from a single monolithic component to a role-based modular system. This ensures:
- **Persistence**: Sidebar never resets when navigating between pages
- **Consistency**: Each role has a consistent, maintainable sidebar
- **Scalability**: Easy to add new roles or modify role-specific navigation

## Architecture

### File Structure
```
templates/
├── base.html                      (Master layout - conditionally includes sidebars)
└── sidebars/
    ├── base_sidebar.html          (Deprecated: template shell - not currently used)
    ├── department_user_sidebar.html (Department user navigation)
    ├── gso_staff_sidebar.html       (GSO staff navigation)
    └── admin_sidebar.html           (Admin/system navigation)
```

### How It Works

#### 1. **base.html** - Conditional Sidebar Include
```django
{% if user.role == 'admin' %}
    {% include 'sidebars/admin_sidebar.html' %}
{% elif user.role == 'gso_staff' %}
    {% include 'sidebars/gso_staff_sidebar.html' %}
{% else %}
    {% include 'sidebars/department_user_sidebar.html' %}
{% endif %}
```

The sidebar is included directly in `base.html` **outside the main content area**. This means:
- When Unpoly swaps content with `up-target="main"`, only the `<main>` element is replaced
- The sidebar (`<aside>`) is never touched during navigation
- The sidebar persists with all its state (open/closed)

#### 2. **Role-Based Sidebars**

##### `department_user_sidebar.html`
- **For**: Department users submitting requests
- **Color Theme**: Green accents
- **Navigation**:
  - Dashboard
  - My Requests
  - Returns
  - Quick Action: New Request

##### `gso_staff_sidebar.html`
- **For**: GSO staff approving requests and managing inventory
- **Color Theme**: Indigo accents
- **Navigation**:
  - Dashboard
  - Pending Requests
  - Returns
  - Inventory
  - Quick Action: Scan QR

##### `admin_sidebar.html`
- **For**: System administrators
- **Color Theme**: Red accents
- **Navigation**:
  - Dashboard
  - Pending Requests
  - Returns
  - Inventory
  - Administration (Users, Categories, Departments)
  - Quick Action: Scan QR

## Key Implementation Details

### 1. **All Links Have `up-target="main"`**
```html
<a href="{% url 'dashboard' %}" up-target="main" up-follow>Dashboard</a>
```
This tells Unpoly to only swap the `<main>` element, leaving the sidebar untouched.

### 2. **Alpine.js State Persistence**
The sidebar uses Alpine.js for interactive state:
```html
<body x-data="{ 
    sidebarOpen: window.innerWidth >= 1024,
    currentUrl: window.location.pathname
    ...
}">
```

Since the sidebar is never removed from the DOM, its Alpine state persists across page navigations.

### 3. **Active Link Highlighting**
Each sidebar uses `currentUrl` to highlight the active navigation item:
```html
:class="currentUrl === '{% url 'dashboard' %}' ? 'bg-green-500/20 text-green-300' : '...'"
```

This is updated by Unpoly's `up:location:changed` event in `base.html`.

### 4. **Responsive Behavior**
- **Desktop (lg+)**: Sidebar is sticky, stays visible, can collapse to icon-only view
- **Mobile**: Sidebar is fixed, slides in/out, has backdrop overlay
- Alpine.js manages responsive state with `@resize.window` listener

## UI/UX Consistency

### Design Principles Applied

1. **Color Consistency by Role**
   - Department User: Green (growth, user-facing)
   - GSO Staff: Indigo (authority, management)
   - Admin: Red (system, control)

2. **Uniform Layout**
   - Logo section (16px height)
   - Navigation sections with dividers
   - User profile section at bottom
   - Consistent spacing, font sizes, transitions

3. **Icon Usage**
   - All icons from Lucide Icons library
   - Icons with transitions and responsive visibility
   - Icon-only mode for collapsed state

4. **Typography**
   - Consistent font sizes (text-sm for nav items)
   - Font weights (semibold for emphasis)
   - Color palette (slate-400/text-white for states)

### Maintainability

To modify the sidebar for a role:
1. Edit the corresponding sidebar file (e.g., `gso_staff_sidebar.html`)
2. Add/remove navigation links as needed
3. Update color scheme if desired (just change the color utility classes)
4. No need to modify `base.html` or other templates

## Migration Notes

### Old Sidebar
- The original hardcoded sidebar in `base.html` (lines 227-420) is now hidden with `display:none`
- It's kept as a reference; can be removed once the new sidebars are validated
- Don't edit the old sidebar; edit the role-specific files instead

### Why The Old Sidebar Reset
The old system included the entire sidebar in `base.html` with all role-specific logic inline. While this seemed like a single sidebar, it was actually causing issues because:
- Any page template that tried to override navigation would cause sidebar flickering
- The monolithic structure made role-specific customization difficult
- It was hard to understand which links applied to which role

## Future Enhancements

1. **Dynamic Sidebar Configuration**
   - Move navigation items to database for easier management
   - Create admin interface for sidebar customization

2. **Nested Navigation**
   - Add collapsible sections for grouping related links
   - Implement breadcrumb navigation in main content

3. **Custom Themes**
   - Allow users to customize sidebar colors per role
   - Add light mode support

4. **Permission-Based Visibility**
   - Show/hide links based on specific permissions, not just role
   - Implement fine-grained access control

## Testing Checklist

- [ ] Department user sees correct sidebar
- [ ] GSO staff sees correct sidebar
- [ ] Admin sees correct sidebar
- [ ] Sidebar does NOT reset when clicking nav links
- [ ] Sidebar does NOT reset on browser back button
- [ ] Mobile sidebar slide-in/out works smoothly
- [ ] Active link highlighting works correctly
- [ ] All sidebar links use `up-target="main"`
- [ ] No JavaScript errors in console
- [ ] Icons render correctly after Unpoly swap

## Related Files

- `templates/base.html` - Master layout with conditional sidebar includes
- `templates/sidebars/*.html` - Role-based sidebar components
- `core/models.py` - User model with Role choices
- `core/views.py` - View logic checking user roles
