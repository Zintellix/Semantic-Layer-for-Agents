-- L0 · One SQLite file, two logical halves.
-- The commerce half stands in for ClickHouse; the registry half for PostgreSQL.
-- They live in one file as a POC shortcut, but are accessed through separate
-- modules (objects.py vs registry.py) so the split survives promotion.

-- ============================================================
-- COMMERCE  (ClickHouse stand-in)
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    product_id   TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    franchise    TEXT
);

CREATE TABLE IF NOT EXISTS variants (
    variant_id     TEXT PRIMARY KEY,
    product_id     TEXT NOT NULL,
    sku            TEXT NOT NULL,
    display_title  TEXT NOT NULL,
    shade          TEXT,
    undertone      TEXT,
    price          REAL,
    cost           REAL,
    revenue_28d    REAL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS inventory_positions (
    position_id         TEXT PRIMARY KEY,   -- "{variant_id}@{location_id}"
    variant_id          TEXT NOT NULL,
    location_id         TEXT NOT NULL,
    on_hand             REAL,
    avg_daily_units_7d  REAL,
    FOREIGN KEY (variant_id) REFERENCES variants(variant_id)
);

-- ============================================================
-- REGISTRY  (PostgreSQL stand-in) — populated by the compiler (L2/L3)
-- ============================================================
CREATE TABLE IF NOT EXISTS ontology_object_types (
    object_type  TEXT PRIMARY KEY,
    pack         TEXT,
    version      TEXT,
    status       TEXT DEFAULT 'ACTIVE',
    extends      TEXT,
    implements   TEXT,          -- json array
    definition   TEXT           -- json blob
);

CREATE TABLE IF NOT EXISTS ontology_link_types (
    link_type     TEXT,
    version       TEXT,
    from_type     TEXT,
    to_type       TEXT,
    cardinality   TEXT,
    join_binding  TEXT,         -- json array
    PRIMARY KEY (link_type, from_type)
);

CREATE TABLE IF NOT EXISTS ontology_action_types (
    action_type      TEXT,
    version          TEXT,
    object_type      TEXT,
    tier             INTEGER,
    reversibility    TEXT,
    parameter_schema TEXT,      -- json
    connector_write  TEXT,
    rollback_spec    TEXT,
    guards           TEXT,      -- json array
    PRIMARY KEY (action_type, object_type)
);

CREATE TABLE IF NOT EXISTS ontology_functions (
    function_id  TEXT PRIMARY KEY,
    version      TEXT,
    returns      TEXT,
    kind         TEXT,
    inputs       TEXT,          -- json array
    formula      TEXT,
    params       TEXT,          -- json
    tests        TEXT           -- json array
);

CREATE TABLE IF NOT EXISTS ontology_event_types (
    event_type     TEXT PRIMARY KEY,
    version        TEXT,
    object_type    TEXT,
    severity_rules TEXT         -- json array
);

CREATE TABLE IF NOT EXISTS ontology_windows (
    window      TEXT PRIMARY KEY,
    version     TEXT,
    definition  TEXT            -- json
);

CREATE TABLE IF NOT EXISTS entity_aliases (
    workspace_id  TEXT,
    domain        TEXT DEFAULT 'cosmetics',
    alias         TEXT,
    object_type   TEXT,         -- resolved target type (or 'ObjectSet'/'Window')
    object_id     TEXT,         -- resolved target id (function id / window / object id)
    source        TEXT,         -- 'seed' | 'learned'
    confidence    REAL,
    confirmed_count INTEGER DEFAULT 0,
    PRIMARY KEY (workspace_id, domain, alias)
);

CREATE TABLE IF NOT EXISTS decision_log (
    action_id      TEXT PRIMARY KEY,
    action_type    TEXT,
    target_objects TEXT,        -- json array of object ids
    tier           INTEGER,
    status         TEXT,        -- PROPOSED | APPROVED | EXECUTED | BLOCKED
    params         TEXT,        -- json
    rollback       TEXT,
    created_at     TEXT
);
