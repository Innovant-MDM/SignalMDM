# Frontend Integration & Extensions Guide — MDM Phase 2

This guide is designed for the frontend development team. It provides a complete map of the newly integrated Phase 2 files (connecting the FastAPI backend to the React/Vite frontend), detailing where every file is located, and outlines the standard modular pattern to follow when introducing new screens or services.

---

## 1. Directory Mapping: Backend to Frontend

Each backend domain in Phase 2 has a matching schema, API endpoint, client-side TypeScript service, and skeleton user interface page:

| Feature / Domain | Backend Model | API Route Router | Frontend Service Class | Frontend React Page Component | Component Local CSS Sheet |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Canonical Models** | `db/models/mdm_phase2/canonical_field.py` | `/api/v1/canonical-models` | `src/services/mdm_phase2/canonicalService.ts` | `src/pages/mdm_phase2/CanonicalModelsPage.tsx` | `src/styles/mdm_phase2/CanonicalModelsPage.css` |
| **Field Mappings** | `db/models/mdm_phase2/field_mapping.py` | `/api/v1/field-mappings` | `src/services/mdm_phase2/mappingService.ts` | `src/pages/mdm_phase2/FieldMappingsPage.tsx` | `src/styles/mdm_phase2/FieldMappingsPage.css` |
| **Transformation Rules** | `db/models/mdm_phase2/transformation_rule.py` | `/api/v1/transformation-rules` | `src/services/mdm_phase2/ruleService.ts` | `src/pages/mdm_phase2/TransformationRulesPage.tsx` | `src/styles/mdm_phase2/TransformationRulesPage.css` |
| **Standardization Rules** | `db/models/mdm_phase2/standardization_rule.py` | `/api/v1/standardization-rules` | `src/services/mdm_phase2/ruleService.ts` | `src/pages/mdm_phase2/StandardizationRulesPage.tsx` | `src/styles/mdm_phase2/StandardizationRulesPage.css` |
| **Normalization Runs** | `db/models/mdm_phase2/normalization_run.py` | `/api/v1/normalization-runs` | `src/services/mdm_phase2/normalizationService.ts` | `src/pages/mdm_phase2/NormalizationRunsPage.tsx` | `src/styles/mdm_phase2/NormalizationRunsPage.css` |
| **Normalized Records** | `db/models/staging_entity.py` (columns added) | `/api/v1/normalization-runs/records` | `src/services/mdm_phase2/normalizationService.ts` | `src/pages/mdm_phase2/NormalizedRecordsPage.tsx` | `src/styles/mdm_phase2/NormalizedRecordsPage.css` |
| **Mapping Errors** | `db/models/mdm_phase2/mapping_error.py` | `/api/v1/mapping-errors` | `src/services/mdm_phase2/normalizationService.ts` | `src/pages/mdm_phase2/MappingErrorsPage.tsx` | `src/styles/mdm_phase2/MappingErrorsPage.css` |

---

## 2. Global Integration & Wiring Locations

If you need to adjust routes, permissions, or navigation structure, here are the exact files to modify:

### 2.1 React Route Registry
All page routing is managed in [App.tsx](file:///d:/SignalMDM/MDM_Frontend/src/App.tsx). 
New routes are registered nested under the protected layout shell context:
```tsx
{/* MDM Phase 2 Routing */}
<Route path="canonical-models" element={<CanonicalModelsPage />} />
<Route path="field-mappings" element={<FieldMappingsPage />} />
<Route path="transformation-rules" element={<TransformationRulesPage />} />
...
```

### 2.2 Navigation Menu & Sidebar
Navigation groups and screen access locks are managed in [MainLayout.tsx](file:///d:/SignalMDM/MDM_Frontend/src/layouts/MainLayout.tsx) under the `NAV` array.
Each sidebar item takes the following configuration keys:
*   `label`: Human-readable title in the sidebar menu.
*   `path`: Router link path.
*   `icon`: Unicode/SVG badge descriptor icon.
*   `screen`: Permission key checked in RBAC (`canAccess(screen, 'view')`).
```tsx
{
  group: 'Mapping & Normalization',
  items: [
    { label: 'Canonical Models',    path: '/canonical-models',    icon: '✥', screen: 'canonical_models' },
    { label: 'Field Mappings',       path: '/field-mappings',       icon: '⇌', screen: 'field_mappings' },
    ...
  ],
}
```

### 2.3 Roles and Permissions Checklist Labels
Checklist naming for screen keys in the RBAC setup screen is defined inside [PlatformRBAC.tsx](file:///d:/SignalMDM/MDM_Frontend/src/pages/platform/PlatformRBAC.tsx) inside the `screenLabels` dictionary:
```typescript
const screenLabels: Record<string, string> = {
  canonical_models: 'Canonical Models',
  field_mappings: 'Field Mappings',
  ...
};
```

---

## 3. How to Add a New Screen (Standard Extension Pattern)

To introduce a new screen into SignalMDM, follow this modular step-by-step developer pipeline:

### Step 1: Create the Frontend API Service Class
Create a dedicated API helper inside `src/services/` (or `src/services/mdm_phase2/`) to manage axios operations via the global api instance:
```typescript
// Example: src/services/mdm_phase2/myNewService.ts
import { api } from '../api';

export interface MyDataPayload {
  id: string;
  name: string;
}

export const myNewService = {
  async fetchData(): Promise<MyDataPayload[]> {
    const res = await api.get<MyDataPayload[]>('/my-new-endpoint');
    return res.data;
  }
};
```

### Step 2: Create the CSS Stylesheet
Create a component-specific stylesheet in the matching folder layout under `src/styles/`:
```css
/* Example: src/styles/mdm_phase2/MyNewPage.css */
.new-page-container {
  padding: 1.5rem;
  max-width: 80rem;
  margin-left: auto;
  margin-right: auto;
}
```

### Step 3: Create the React Page Component
Create a page component in `src/pages/` (or `src/pages/mdm_phase2/`). Always import both the global `theme.css` and your local component CSS at the top:
```tsx
// Example: src/pages/mdm_phase2/MyNewPage.tsx
import React, { useEffect, useState } from 'react';
import '../../styles/theme.css';
import '../../styles/mdm_phase2/MyNewPage.css';
import { myNewService, type MyDataPayload } from '../../services/mdm_phase2/myNewService';

export const MyNewPage: React.FC = () => {
  const [data, setData] = useState<MyDataPayload[]>([]);

  useEffect(() => {
    myNewService.fetchData().then(setData).catch(console.error);
  }, []);

  return (
    <div className="new-page-container">
      <h1 className="text-3xl font-bold">My New Screen Title</h1>
      <ul>
        {data.map(item => <li key={item.id}>{item.name}</li>)}
      </ul>
    </div>
  );
};

export default MyNewPage;
```

### Step 4: Register Route in React Router
Open [App.tsx](file:///d:/SignalMDM/MDM_Frontend/src/App.tsx), import the component and register a child route inside `<MainLayout />`:
```typescript
import MyNewPage from './pages/mdm_phase2/MyNewPage';
// ...
<Route path="my-new-path" element={<MyNewPage />} />
```

### Step 5: Add Sidebar Navigation Link
Open [MainLayout.tsx](file:///d:/SignalMDM/MDM_Frontend/src/layouts/MainLayout.tsx), find the target group in `NAV`, and append the entry:
```typescript
{ label: 'New Screen Label', path: '/my-new-path', icon: '✦', screen: 'my_new_screen_key' }
```

### Step 6: Map screen keys to RBAC Configuration Checklist
Open [PlatformRBAC.tsx](file:///d:/SignalMDM/MDM_Frontend/src/pages/platform/PlatformRBAC.tsx) and add your `my_new_screen_key` inside `screenLabels`:
```typescript
my_new_screen_key: 'My New Screen Display Label',
```

### Step 7: (Database/RBAC Admin Roles seeding)
If you require permissions checks (other than super_admin who gets all screens automatically), add corresponding `INSERT` entries into the database catalog (`platform_permission` and `platform_role_permission`) to allow roles to access the screen. Use the [db_phase2_rbac_seed.sql](file:///d:/SignalMDM/db_phase2_rbac_seed.sql) template as a base.
