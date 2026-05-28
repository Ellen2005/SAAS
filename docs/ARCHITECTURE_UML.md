# SAAS architecture & UML diagrams

## System context

```mermaid
flowchart TB
  User[Manager / Admin / Viewer]
  PWA[React PWA :5000]
  API[FastAPI :8000]
  SB[(Supabase Postgres)]
  SRC[(Customer source DB)]

  User --> PWA
  PWA -->|JWT + REST| API
  PWA -->|Auth + RLS reads| SB
  API -->|Service role| SB
  API -->|Read-only SQL/Mongo| SRC[(Customer source DB: PostgreSQL / MySQL / Oracle / SQLite / SQL Server / MongoDB)]
```

## Use cases

```mermaid
flowchart LR
  subgraph Manager
    UC1[Connect database]
    UC2[Sync / generate report]
    UC3[Ask data NLQ]
    UC4[Explore schema]
    UC5[Custom chart]
  end
  subgraph Admin
    UC6[Define KPI template]
    UC7[Manage departments/users]
  end
  subgraph System
    UC8[Auto-discover KPIs]
    UC9[Email briefing]
  end
```

## KPI decision activity

```mermaid
flowchart TD
  Start[ETL / Sync triggered] --> HasConn{Connection saved?}
  HasConn -->|No| Overview[Overview: no connection]
  HasConn -->|Yes| Extract[Extract from source DB]
  Extract --> HasRows{Rows returned?}
  HasRows -->|No| Overview2[Overview: table counts]
  HasRows -->|Yes| AdminFields{Admin KPI fields defined?}
  AdminFields -->|No| Auto[Auto-discovered KPI names from DB]
  AdminFields -->|Yes| Mapped{Mappings saved?}
  Mapped -->|Yes| Configured[Configured KPI path + validation]
  Mapped -->|No| Auto
  Auto --> Store[Store KPIs + narrative]
  Configured --> Store
  Overview2 --> Store
```

## Sequence: Ask your data (NLQ)

```mermaid
sequenceDiagram
  participant U as User
  participant F as Frontend
  participant A as FastAPI
  participant G as Groq optional
  participant D as Source DB

  U->>F: Natural language question
  F->>A: POST /api/nlq
  A->>A: Load connection decrypt if enc:
  alt GROQ_API_KEY set
    A->>G: Generate SELECT
    G-->>A: SQL
  else Fallback
    A->>A: Rule-based SQL
  end
  A->>D: Execute read-only query
  D-->>A: Rows
  A->>A: Build chart spec
  A-->>F: rows + sql + chart
  F-->>U: Table + chart
```

## Sequence: Save connection

```mermaid
sequenceDiagram
  participant F as Frontend
  participant A as FastAPI
  participant S as Supabase

  F->>A: POST /api/test-connection
  A->>A: SQLAlchemy ping
  A-->>F: success / error
  F->>A: POST /api/settings/connection
  A->>A: Normalize URI + optional Fernet encrypt
  A->>S: Upsert database_connections
  A-->>F: saved
```

## ER diagram (app database)

```mermaid
erDiagram
  auth_users ||--o{ user_roles : has
  departments ||--o{ user_roles : contains
  semantic_templates ||--o{ semantic_fields : defines
  semantic_fields ||--o{ field_mappings : mapped_by
  auth_users ||--o{ field_mappings : owns
  auth_users ||--o{ database_connections : owns
  auth_users ||--o{ kpi_results : owns
  auth_users ||--o{ daily_reports : owns
  departments ||--o{ kpi_results : scopes
```

## Service classes (backend)

```mermaid
classDiagram
  class ETLService {
    extract_from_source()
    run_user_etl_pipeline()
    detect_anomalies_and_transform()
  }
  class SchemaIntrospector {
    introspect_sql()
    suggest_analyses()
    run_analysis()
  }
  class NLQService {
    run_nlq()
  }
  class KPIConfig {
    resolve_kpi_mode()
    get_admin_kpi_fields()
  }
  class ChartService {
    build_chart_from_rows()
    build_kpi_snapshot_chart()
  }
  ETLService --> SchemaIntrospector
  ETLService --> KPIConfig
  NLQService --> ChartService
```
