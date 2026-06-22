# Semantic Mapping Assignment Guide
## How to Assign Semantic Mappings to Departments

This guide explains how administrators can assign semantic templates and field mappings to departments.

---

## Overview

The semantic mapping system works in **3 levels**:

1. **Template** (Admin) - Defines global field names and data types
2. **Department** (Admin) - Assigns a template to a department
3. **Field Mappings** (Users) - Maps template fields to local database columns

---

## Step-by-Step Process

### Step 1: Create a Semantic Template (Admin)

**What is a Template?**
A template defines the standard fields your organization uses for KPIs.

**Example Template: "CNPS Standard"**
```
Fields:
  - total_contributions (number)
  - pension_disbursement (number)
  - at_mp_frequency (number)
  - collection_rate (percentage)
  - regional_share (text)
```

**How to Create:**

**Option A: Via API**
```bash
curl -X POST https://your-api.com/api/admin/semantic/templates \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CNPS Standard",
    "description": "Standard CNPS KPI template for all departments"
  }'
```

**Option B: Via Frontend (Admin Dashboard)**
1. Login as **admin**
2. Go to **Admin → Semantic**
3. Click **Create Template**
4. Enter name and description
5. Click **Save**

**Response:**
```json
{
  "status": "success",
  "template": {
    "id": "template-uuid-123",
    "name": "CNPS Standard",
    "description": "Standard CNPS KPI template"
  }
}
```

**Save the `template.id` - you'll need it for the next step!**

---

### Step 2: Add Fields to Template (Admin)

**What are Fields?**
Fields define the specific data points in your template.

**How to Add Fields:**

**Option A: Via API**
```bash
# Add first field
curl -X POST https://your-api.com/api/admin/semantic/templates/{template_id}/fields \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "global_field_name": "total_contributions",
    "data_type": "number",
    "required": true,
    "description": "Total monthly contributions in XAF"
  }'

# Add more fields
curl -X POST https://your-api.com/api/admin/semantic/templates/{template_id}/fields \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "global_field_name": "pension_disbursement",
    "data_type": "number",
    "required": true,
    "description": "Total pension payments"
  }'

curl -X POST https://your-api.com/api/admin/semantic/templates/{template_id}/fields \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "global_field_name": "at_mp_frequency",
    "data_type": "number",
    "required": false,
    "description": "Workplace accident frequency rate"
  }'
```

**Option B: Via Frontend**
1. Go to **Admin → Semantic**
2. Click on your template
3. Click **Add Field**
4. Fill in:
   - **Field Name:** `total_contributions`
   - **Data Type:** `number`
   - **Required:** ✓ Yes
   - **Description:** `Total monthly contributions in XAF`
5. Click **Save**
6. Repeat for all fields

**Complete Field List Example:**
```json
[
  {
    "id": "field-1",
    "global_field_name": "total_contributions",
    "data_type": "number",
    "required": true
  },
  {
    "id": "field-2",
    "global_field_name": "pension_disbursement",
    "data_type": "number",
    "required": true
  },
  {
    "id": "field-3",
    "global_field_name": "at_mp_frequency",
    "data_type": "number",
    "required": false
  },
  {
    "id": "field-4",
    "global_field_name": "collection_rate",
    "data_type": "percentage",
    "required": true
  },
  {
    "id": "field-5",
    "global_field_name": "regional_share",
    "data_type": "text",
    "required": false
  }
]
```

---

### Step 3: Assign Template to Department (Admin)

**What does this do?**
This links a department to a semantic template. All users in that department will use this template.

**How to Assign:**

**Option A: Via API**
```bash
curl -X PUT https://your-api.com/api/admin/departments/{department_id} \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "template-uuid-123"
  }'
```

**Option B: Via Frontend**
1. Go to **Admin → Departments**
2. Find the department (e.g., "Douala Regional Office")
3. Click **Edit**
4. Select template from dropdown: "CNPS Standard"
5. Click **Save**

**Response:**
```json
{
  "status": "success",
  "department_id": "dept-uuid-456",
  "updated": {
    "template_id": "template-uuid-123"
  }
}
```

---

### Step 4: Users Create Field Mappings (Manager/Viewer)

**What are Field Mappings?**
Mappings connect the template fields to actual database columns.

**Example:**
```
Template Field: "total_contributions"
  → Maps to: contributions.contribution_amount
  → Transformation: SUM(contribution_amount)

Template Field: "pension_disbursement"
  → Maps to: pension_payments.pension_amount
  → Transformation: SUM(pension_amount)
```

**How Users Create Mappings:**

**Option A: Via API**
```bash
# Get user's template first
curl https://your-api.com/api/semantic/my-template \
  -H "Authorization: Bearer <user-token>"

# This returns the template and fields assigned to user's department

# Create mapping for first field
curl -X POST https://your-api.com/api/semantic/mappings \
  -H "Authorization: Bearer <user-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "template_field_id": "field-1",
    "local_column_name": "contributions.contribution_amount",
    "transformation_rule": {
      "aggregation": "SUM",
      "filter": "payment_status = '\''paid'\''"
    }
  }'

# Create mapping for second field
curl -X POST https://your-api.com/api/semantic/mappings \
  -H "Authorization: Bearer <user-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "template_field_id": "field-2",
    "local_column_name": "pension_payments.pension_amount",
    "transformation_rule": {
      "aggregation": "SUM"
    }
  }'
```

**Option B: Via Frontend (Settings → Semantic Mapping)**
1. Login as **manager** or **viewer**
2. Go to **Settings → Semantic Mapping**
3. You'll see your department's template fields
4. For each field:
   - **Field Name:** (pre-filled) `total_contributions`
   - **Local Column:** Select from dropdown or type: `contributions.contribution_amount`
   - **Transformation:** (optional) `SUM`, `AVG`, `COUNT`, etc.
5. Click **Save Mapping**
6. Repeat for all fields

---

## Complete Workflow Example

### Scenario: Assign CNPS Template to Douala Department

**1. Admin creates template:**
```bash
POST /api/admin/semantic/templates
{
  "name": "CNPS Standard",
  "description": "Standard KPIs for CNPS operations"
}
# Returns: { "template": { "id": "tmpl-123" } }
```

**2. Admin adds fields:**
```bash
POST /api/admin/semantic/templates/tmpl-123/fields
{
  "global_field_name": "total_contributions",
  "data_type": "number",
  "required": true
}
# Returns: { "field": { "id": "field-1" } }

POST /api/admin/semantic/templates/tmpl-123/fields
{
  "global_field_name": "pension_disbursement",
  "data_type": "number",
  "required": true
}
# Returns: { "field": { "id": "field-2" } }
```

**3. Admin assigns template to department:**
```bash
PUT /api/admin/departments/dept-456
{
  "template_id": "tmpl-123"
}
# Returns: { "status": "success" }
```

**4. Manager in Douala department creates mappings:**
```bash
# First, check their template
GET /api/semantic/my-template
# Returns: { "template": {...}, "fields": [...] }

# Create mapping
POST /api/semantic/mappings
{
  "template_field_id": "field-1",
  "local_column_name": "contributions.contribution_amount",
  "transformation_rule": {
    "aggregation": "SUM",
    "conditions": "payment_status = 'paid'"
  }
}
```

---

## Validation

### Check if Mappings are Complete

**API:**
```bash
curl https://your-api.com/api/semantic/mappings/validate \
  -H "Authorization: Bearer <user-token>"
```

**Response:**
```json
{
  "valid": true,
  "total_fields": 5,
  "mapped_fields": 5,
  "missing_required": [],
  "missing_optional": []
}
```

**If incomplete:**
```json
{
  "valid": false,
  "total_fields": 5,
  "mapped_fields": 3,
  "missing_required": [
    {"id": "field-2", "name": "pension_disbursement"}
  ],
  "missing_optional": [
    {"id": "field-5", "name": "regional_share"}
  ]
}
```

---

## Bulk Assignment (Advanced)

### Assign Template to Multiple Departments

**Script:**
```bash
#!/bin/bash

TEMPLATE_ID="tmpl-123"
DEPARTMENTS=("dept-456" "dept-789" "dept-101")

for dept in "${DEPARTMENTS[@]}"
do
  curl -X PUT https://your-api.com/api/admin/departments/$dept \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"template_id\": \"$TEMPLATE_ID\"}"
  echo "Assigned to $dept"
done
```

### Create Default Mappings for All Users in Department

**Python Script:**
```python
import requests

API_URL = "https://your-api.com"
ADMIN_TOKEN = "your-admin-token"

# Get all users in department
users = requests.get(
    f"{API_URL}/api/admin/departments/{dept_id}/users",
    headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
).json()

# Default mappings
default_mappings = [
    {
        "template_field_id": "field-1",
        "local_column_name": "contributions.contribution_amount",
        "transformation_rule": {"aggregation": "SUM"}
    },
    {
        "template_field_id": "field-2",
        "local_column_name": "pension_payments.pension_amount",
        "transformation_rule": {"aggregation": "SUM"}
    }
]

# Assign to each user
for user in users:
    for mapping in default_mappings:
        requests.post(
            f"{API_URL}/api/semantic/mappings",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
            json={
                **mapping,
                "user_id": user["user_id"]
            }
        )
    print(f"Assigned mappings to {user['email']}")
```

---

## Database Schema

### Tables Involved

**1. semantic_templates**
```sql
- id (UUID)
- name (TEXT)
- description (TEXT)
- created_by (UUID)
- created_at (TIMESTAMP)
```

**2. semantic_fields**
```sql
- id (UUID)
- template_id (UUID)
- global_field_name (TEXT)
- data_type (TEXT)
- required (BOOLEAN)
- description (TEXT)
```

**3. departments**
```sql
- id (UUID)
- name (TEXT)
- template_id (UUID)  ← Links to semantic template
- instance_template_id (UUID)
- regional_office_id (UUID)
```

**4. field_mappings**
```sql
- id (UUID)
- user_id (UUID)
- template_field_id (UUID)
- local_column_name (TEXT)
- transformation_rule (JSONB)
```

---

## Common Issues & Solutions

### Issue 1: "No template assigned to department"
**Solution:** Assign a template to the department via:
```bash
PUT /api/admin/departments/{dept_id}
{ "template_id": "tmpl-123" }
```

### Issue 2: "Required fields not mapped"
**Solution:** User needs to create mappings for all required fields:
```bash
POST /api/semantic/mappings
{
  "template_field_id": "field-id",
  "local_column_name": "table.column"
}
```

### Issue 3: "Template not found"
**Solution:** Create template first:
```bash
POST /api/admin/semantic/templates
{ "name": "My Template" }
```

### Issue 4: "Permission denied"
**Solution:** 
- Template creation: Admin only
- Department assignment: Admin only
- Field mappings: Manager/Viewer (for their own department)

---

## Best Practices

### 1. Template Naming
✅ **Good:** "CNPS Standard KPIs", "Regional Office Metrics"  
❌ **Bad:** "Template 1", "test", "asdf"

### 2. Field Naming
✅ **Good:** `total_contributions`, `pension_disbursement`  
❌ **Bad:** `field1`, `contrib`, `pd`

### 3. Data Types
Use consistent types:
- `number` - For numeric values (contributions, amounts)
- `percentage` - For rates and percentages
- `text` - For categorical data
- `date` - For dates
- `boolean` - For true/false flags

### 4. Required Fields
Mark only essential fields as required:
- ✅ Required: `total_contributions`, `pension_disbursement`
- ❌ Not Required: `notes`, `comments`

### 5. Transformation Rules
Use standard aggregations:
- `SUM` - Total values
- `AVG` - Average values
- `COUNT` - Count records
- `MAX`/`MIN` - Extremes
- `MEDIAN` - Middle value

---

## Quick Reference

### Admin Actions
| Action | Endpoint | Permission |
|--------|----------|------------|
| Create template | `POST /api/admin/semantic/templates` | Admin |
| Add field | `POST /api/admin/semantic/templates/{id}/fields` | Admin |
| Assign to dept | `PUT /api/admin/departments/{id}` | Admin |
| List templates | `GET /api/admin/semantic/templates` | Admin |

### User Actions
| Action | Endpoint | Permission |
|--------|----------|------------|
| Get my template | `GET /api/semantic/my-template` | Any |
| List my mappings | `GET /api/semantic/mappings` | Any |
| Create mapping | `POST /api/semantic/mappings` | Any |
| Update mapping | `PUT /api/semantic/mappings/{id}` | Any |
| Delete mapping | `DELETE /api/semantic/mappings/{id}` | Any |
| Validate mappings | `GET /api/semantic/mappings/validate` | Any |

---

## Example: Complete Setup for CNPS

### 1. Create Template
```json
POST /api/admin/semantic/templates
{
  "name": "CNPS National Standard",
  "description": "Standard KPIs for all CNPS regional offices"
}
```

### 2. Add Fields
```json
POST /api/admin/semantic/templates/{id}/fields
{"global_field_name": "total_contributions", "data_type": "number", "required": true}

POST /api/admin/semantic/templates/{id}/fields
{"global_field_name": "pension_disbursement", "data_type": "number", "required": true}

POST /api/admin/semantic/templates/{id}/fields
{"global_field_name": "collection_rate", "data_type": "percentage", "required": true}

POST /api/admin/semantic/templates/{id}/fields
{"global_field_name": "at_mp_frequency", "data_type": "number", "required": false}

POST /api/admin/semantic/templates/{id}/fields
{"global_field_name": "active_employers", "data_type": "number", "required": false}
```

### 3. Assign to All Regional Departments
```bash
# Douala
PUT /api/admin/departments/dept-douala { "template_id": "tmpl-123" }

# Yaoundé
PUT /api/admin/departments/dept-yaounde { "template_id": "tmpl-123" }

# Garoua
PUT /api/admin/departments/dept-garoua { "template_id": "tmpl-123" }

# ... repeat for all 10 regions
```

### 4. Users Create Mappings
Each regional office manager maps the template fields to their local database columns.

---

**Last Updated:** 2025-01-15  
**Status:** Complete ✅