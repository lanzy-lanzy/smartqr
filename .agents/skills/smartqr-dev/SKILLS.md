---
name: smartqr-dev
description: Deep knowledge and debugging instructions for SmartQR batching, QR code integration, and UI/UX consistency.
---

# SmartQR Dev Skill

This skill provides specialized instructions for maintaining, debugging, and extending the SmartQR Supply Management system.

## 1. Batch Operations Logic

### Batch Requests
- **Grouping**: Multiple `SupplyRequest` objects are linked via a `batch_group_id` (UUID).
- **Consumables vs equipment**: 
  - Consumables decrease `Supply.quantity` immediately or on issue.
  - Equipment creates `BorrowedItem` entries linked to specific `EquipmentInstance`.
- **Validation**: Ensure that `Supply.available_quantity()` is checked for *each* item in the batch before submission.

### Batch Returns
- **Verification**: A batch is considered "Returned" only when *all* `BorrowedItem` entries sharing the same `batch_group_id` have a `returned_at` timestamp.
- **Overdue Logic**: If one item in a batch is overdue, the user's `has_overdue_items` flag is set to True, blocking new requests.

## 2. QR Code Integration

### Generation
- **Models**: `Supply`, `EquipmentInstance`, and `SupplyRequest` have a `generate_qr_code()` method.
- **Pattern**: 
  - Supplies: `SUPPLY-[id]`
  - Instances: `INSTANCE-[id]`
  - Requests: `REQUEST-[id]`
- **Storage**: QR codes are saved as `ContentFile` in the `qr_code` FileField.

### Scanning (Template)
- **Library**: `html5-qrcode` (loaded via CDN in `base.html`).
- **Flow**:
  1. Initialize `Html5Qrcode` on a div (e.g., `#qr-reader`).
  2. `onScanSuccess` sends a POST request to a process view (e.g., `process_qr_scan`).
  3. View returns JSON with item details.
  4. Template uses **Alpine.js** to show a confirmation modal.

## 3. UI/UX Consistency Standards

### Navigation (Sidebar)
- **Architecture**: Role-based sidebars in `templates/sidebars/`:
  - `department_user_sidebar.html` (green theme)
  - `gso_staff_sidebar.html` (indigo theme)
  - `admin_sidebar.html` (red theme)
- **Active State**: Use Alpine.js `:class` with `currentUrl` (updated by Unpoly's `up:location:changed`).
- **Sidebar Persistence**: Sidebars are included in `base.html` (not in content templates), so they never swap.
- **Targeting**: Always use `up-target="main"` on all navigation links to ensure only content swaps, never sidebar.
- **Color Consistency**: Each role has distinct colors (green for users, indigo for staff, red for admin).

### Modals (Unpoly + Alpine)
- **Pattern**: 
  - Use `up-layer="new modal"` for specialized forms.
  - Inside the modal, use Alpine for inline interactions (like adjusting quantity).
  - Ensure `initGlobal()` is called after Unpoly swaps to re-initialize Lucide icons and Alpine components.

## 4. Common Debugging Scenarios

- **Scanner not starting**: Check if the browser allows camera access and if another instance of `Html5Qrcode` is running.
- **Batch submission failing**: Verify `selected_items` format in `batch_create.html` (usually `type:id:qty` or `type:id`).
- **Sidebar link not highlighting**: Verify `{% url '...' %}` matches exactly with `currentUrl` in `base.html`.
- **Modal not closing**: Ensure `up.layer.dismiss()` is called or Alpine's `showModal = false` is used correctly.
