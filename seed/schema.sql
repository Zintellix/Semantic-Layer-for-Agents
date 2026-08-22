-- L0 · Registry Schema
-- Populated by the compiler (L2/L3)


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
    roles_allowed TEXT,         -- json array of allowed roles
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
    event_type     TEXT,
    version        TEXT,
    object_type    TEXT,
    severity_rules TEXT,         -- json array
    PRIMARY KEY (event_type, object_type)
);


CREATE TABLE IF NOT EXISTS ontology_windows (
    window      TEXT PRIMARY KEY,
    version     TEXT,
    definition  TEXT            -- json
);

CREATE TABLE IF NOT EXISTS entity_aliases (
    workspace_id  TEXT,
    domain        TEXT,
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



