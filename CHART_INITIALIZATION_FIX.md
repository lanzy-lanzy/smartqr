# Dashboard Charts Initialization Fix

## Problem
Charts were not displaying when navigating to the dashboard via Unpoly navigation. They would only appear after a manual page refresh.

## Root Cause
The site uses **Unpoly** for client-side navigation (not full page reloads). When navigating to the dashboard:
1. The chart canvas elements were being inserted into the DOM
2. But the JavaScript chart initialization code was not being triggered properly
3. The `DOMContentLoaded` event only fires on full page loads, not on Unpoly fragment insertions

## Solution

### 1. **Enhanced Chart Initialization** (dashboard/index.html)
- Added comprehensive error handling with try-catch blocks to all chart loading functions
- Added null-checks before accessing canvas elements
- Added console logging for debugging
- Made chart functions resilient to missing elements

### 2. **Global Unpoly Hook** (base.html)
- Added a trigger in the base template's Unpoly lifecycle hook
- When `up:fragment:inserted` fires (indicating a new page was loaded via Unpoly), it calls `window.ensureChartsInitialized()`
- This ensures charts initialize even if the dashboard's own event listeners don't fire

### 3. **Safeguard Function** (dashboard/index.html)
- Created `ensureChartsInitialized()` function that:
  - Checks if chart canvas elements exist in the DOM
  - Checks if chart variables have been initialized
  - If elements exist but charts aren't initialized, it initializes them
  - Resets chart variables to ensure fresh initialization
  - Exposed this function to global scope so base.html can call it

### 4. **Multiple Event Listeners**
- `DOMContentLoaded`: For initial page loads
- `up:fragment:inserted`: For Unpoly navigation (via base template)
- `htmx:afterSettle`: For HTMX requests (fallback)
- Dropdown change event: For changing the time period on the requests chart

## Files Modified
1. `templates/dashboard/index.html` - Enhanced chart initialization with error handling and safeguard function
2. `templates/base.html` - Added trigger for chart initialization in Unpoly fragment insertion hook

## Testing
1. Navigate to the dashboard normally (full page load) - charts should display
2. Navigate to dashboard from other pages using sidebar links (Unpoly) - charts should display immediately
3. Change the date range dropdown on the requests chart - should update without full page reload
4. Open browser dev console to see logging messages confirming chart initialization

## Debugging
If charts still don't display, check the browser console for:
- `Initializing all charts...` - indicates chart initialization started
- `Dashboard fragment inserted, initializing charts...` - indicates Unpoly loaded the dashboard
- Error messages indicating what went wrong (fetch errors, missing elements, etc.)
