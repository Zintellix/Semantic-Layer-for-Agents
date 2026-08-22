"""Zintellix Enterprise Semantic Layer — Streamlit Dashboard.

Provides a visual interface for:
  1. Platform Overview & Health
  2. Schema Explorer (types, properties, links)
  3. Ontology Graph Visualizer
  4. Data Browser (browse rows per object type)
  5. Agent Chat (Gemini-powered Q&A)
  6. Domain Manager (upload YAMLs, rebuild)
  7. Lineage Explorer
  8. Audit Log
"""
import streamlit as st
import requests
import json
import os
import pandas as pd

# Configure page
st.set_page_config(
    page_title="Zintellix Semantic Layer",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = os.environ.get("ZX_API_URL", "http://localhost:8000")

# ---- Sidebar ----
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
    st.title("Zintellix")
    st.caption("Enterprise Semantic Layer")
    st.divider()
    
    # API Health Check
    try:
        health = requests.get(f"{API_URL}/api/health", timeout=3).json()
        st.success(f"✅ API Online — v{health.get('version', '?')}")
        llm_status = "🟢 Connected" if health.get("llm_available") else "🔴 No API Key"
        st.caption(f"LLM: {llm_status} ({health.get('provider') or 'none'})")
    except Exception:
        health = {}
        st.error("❌ API Offline — Start uvicorn on port 8000")
    
    st.divider()
    
    # Gemini API Key
    api_key = st.text_input("🔑 Gemini API Key", type="password",
                            help="Enter your Google Gemini API key to enable the AI Agent.")
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
        os.environ["ZX_AGENT_PROVIDER"] = "gemini"
    
    st.divider()
    
    # Domain Selector
    try:
        domains_resp = requests.get(f"{API_URL}/api/domains", timeout=3).json()
        domain_list = [d["name"] for d in domains_resp.get("domains", [])]
        domain_info = {d["name"]: d for d in domains_resp.get("domains", [])}
    except Exception:
        domain_list = []
        domain_info = {}
    
    if domain_list:
        active_domain = st.selectbox("🌐 Active Domain", domain_list)
    else:
        active_domain = None
        st.warning("No domains loaded")
    
    st.divider()
    st.caption("© Zintellix 2026 — Semantic Layer POC")


# ---- Tabs ----
tabs = st.tabs([
    "📋 Overview",
    "🏗️ Schema",
    "🕸️ Graph",
    "📊 Data",
    "🤖 Agent",
    "📂 Domains",
    "🔗 Lineage",
    "📜 Audit Log"
])

# ============================================================
# TAB 1: Overview
# ============================================================
with tabs[0]:
    st.header("📋 Platform Overview")
    
    if health:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Domains", len(domain_list))
        
        try:
            schema_data = requests.get(f"{API_URL}/api/schema", timeout=5).json()
            col2.metric("Object Types", len(schema_data.get("object_types", {})))
            col3.metric("Link Types", len(schema_data.get("link_types", [])))
            col4.metric("Functions", len(schema_data.get("functions", [])))
        except Exception:
            col2.metric("Object Types", "?")
            col3.metric("Object Types", "?")
            col4.metric("Functions", "?")
        
        st.divider()
        
        st.subheader("Loaded Domains")
        for d in domains_resp.get("domains", []):
            with st.expander(f"🌐 {d['name'].upper()} — {d.get('label', '')}"):
                st.markdown(f"**Flagship Question:** {d.get('flagship', 'N/A')}")
                st.markdown(f"**Primary Type:** `{d.get('primary_type', 'N/A')}`")
                if d.get("samples"):
                    st.markdown("**Sample Queries:**")
                    for s in d["samples"]:
                        st.markdown(f"  - _{s}_")
    else:
        st.info("Start the API server to see platform stats.")


# ============================================================
# TAB 2: Schema Explorer
# ============================================================
with tabs[1]:
    st.header("🏗️ Schema Explorer")
    
    if active_domain:
        try:
            schema_data = requests.get(f"{API_URL}/api/schema",
                                       params={"domain": active_domain}, timeout=5).json()
        except Exception:
            schema_data = {}
        
        if schema_data.get("object_types"):
            for type_name, type_def in schema_data["object_types"].items():
                with st.expander(f"📦 {type_name}  (pack: {type_def.get('pack', '?')})"):
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Primary Key:** `{type_def.get('primary_key')}`")
                    c2.markdown(f"**Datasource:** `{type_def.get('datasource')}`")
                    
                    # Properties Table
                    if type_def.get("properties"):
                        st.markdown("##### Properties")
                        prop_rows = []
                        for pname, pdef in type_def["properties"].items():
                            prop_rows.append({
                                "Name": pname,
                                "Type": pdef.get("type", ""),
                                "Source": pdef.get("source") or pdef.get("function") or "",
                                "Binding": "Computed" if pdef.get("is_derived") else "Direct"
                            })
                        st.dataframe(pd.DataFrame(prop_rows), use_container_width=True, hide_index=True)
                    
                    # Links
                    if type_def.get("links"):
                        st.markdown("##### Links")
                        link_rows = []
                        for lname, ldef in type_def["links"].items():
                            link_rows.append({
                                "Link": lname,
                                "Target": ldef.get("to", ""),
                                "Cardinality": ldef.get("cardinality", ""),
                                "Join": ", ".join(ldef.get("join", []))
                            })
                        st.dataframe(pd.DataFrame(link_rows), use_container_width=True, hide_index=True)
            
            # Functions
            if schema_data.get("functions"):
                st.subheader("⚙️ Functions")
                for fn in schema_data["functions"]:
                    cols = st.columns([2, 1, 1, 3])
                    cols[0].code(fn["function_id"])
                    cols[1].caption(fn.get("kind", ""))
                    cols[2].caption(fn.get("returns", ""))
                    if fn.get("formula"):
                        cols[3].code(fn["formula"])
                    elif fn.get("params"):
                        cols[3].json(fn["params"])
            
            # Actions
            if schema_data.get("actions"):
                st.subheader("⚡ Actions")
                for act in schema_data["actions"]:
                    st.markdown(f"- **{act['action_type']}** on `{act['object_type']}` "
                                f"(Tier {act['tier']}, {act.get('reversibility', '?')})")
        else:
            st.info("No schema found for this domain.")
    else:
        st.info("Select a domain from the sidebar.")


# ============================================================
# TAB 3: Ontology Graph Visualizer
# ============================================================
with tabs[2]:
    st.header("🕸️ Semantic Graph")
    
    if active_domain and st.button("Render Graph", type="primary"):
        with st.spinner("Building graph from ontology schema..."):
            try:
                from streamlit_agraph import agraph, Node, Edge, Config
                
                schema_data = requests.get(f"{API_URL}/api/schema",
                                           params={"domain": active_domain}, timeout=5).json()
                
                nodes = []
                edges = []
                colors = {"sales": "#4CAF50", "hr": "#2196F3", "core": "#FF9800"}
                
                for type_name, type_def in schema_data.get("object_types", {}).items():
                    pack = type_def.get("pack", "")
                    color = colors.get(pack, "#9C27B0")
                    prop_count = len(type_def.get("properties", {}))
                    nodes.append(Node(
                        id=type_name,
                        label=f"{type_name}\n({prop_count} props)",
                        size=30 + prop_count * 5,
                        shape="dot",
                        color=color
                    ))
                
                for lt in schema_data.get("link_types", []):
                    if lt["from_type"] in schema_data.get("object_types", {}) and \
                       lt["to_type"] in schema_data.get("object_types", {}):
                        edges.append(Edge(
                            source=lt["from_type"],
                            target=lt["to_type"],
                            label=lt["link_type"],
                            color="#666"
                        ))
                
                if nodes:
                    config = Config(
                        width=1000, height=500,
                        directed=True, physics=True, hierarchical=False,
                        nodeHighlightBehavior=True,
                        highlightColor="#F7A7A6"
                    )
                    agraph(nodes=nodes, edges=edges, config=config)
                    
                    st.caption(f"Showing {len(nodes)} types, {len(edges)} links for domain '{active_domain}'")
                else:
                    st.warning("No object types found for this domain.")
                    
            except ImportError:
                st.error("Install `streamlit-agraph`: pip install streamlit-agraph")
            except Exception as e:
                st.error(f"Error: {e}")


# ============================================================
# TAB 4: Data Browser
# ============================================================
with tabs[3]:
    st.header("📊 Data Browser")
    
    if active_domain:
        try:
            schema_data = requests.get(f"{API_URL}/api/schema",
                                       params={"domain": active_domain}, timeout=5).json()
            type_names = list(schema_data.get("object_types", {}).keys())
        except Exception:
            type_names = []
        
        if type_names:
            selected_type = st.selectbox("Select Object Type", type_names)
            
            if st.button("Load Data", type="primary"):
                with st.spinner(f"Loading {selected_type} data..."):
                    try:
                        resp = requests.get(f"{API_URL}/api/data/{selected_type}", timeout=5).json()
                        
                        if resp.get("rows"):
                            df = pd.DataFrame(resp["rows"])
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            st.caption(f"Showing {resp.get('total', 0)} rows from table `{resp.get('table')}`")
                        else:
                            st.info(f"No data rows found for {selected_type}. "
                                    "Upload seed data or check the datasource mapping.")
                    except Exception as e:
                        st.error(f"Error loading data: {e}")
        else:
            st.info("No object types found for this domain.")


# ============================================================
# TAB 5: Agent Chat
# ============================================================
with tabs[4]:
    st.header("🤖 Semantic Agent")
    
    if active_domain:
        info = domain_info.get(active_domain, {})
        if info.get("flagship"):
            st.info(f"💡 **Flagship question:** _{info['flagship']}_")
        
        # Show sample queries
        samples = info.get("samples", [])
        if samples:
            st.caption("Try one of these:")
            sample_cols = st.columns(min(len(samples), 4))
            for i, s in enumerate(samples[:4]):
                if sample_cols[i].button(f"_{s}_", key=f"sample_{i}"):
                    st.session_state["agent_question"] = s
        
        question = st.text_input("Ask a question:",
                                 value=st.session_state.get("agent_question", ""),
                                 placeholder="Which accounts have deals over $200,000?",
                                 key="agent_input")
        
        col_run, col_llm = st.columns([1, 3])
        use_llm = col_llm.checkbox("Use Gemini LLM", value=bool(api_key),
                                    help="Requires a Gemini API key in the sidebar.")
        
        if col_run.button("🚀 Run Query", type="primary"):
            with st.spinner("🤖 Agent is reasoning over the semantic graph..."):
                try:
                    payload = {"question": question, "domain": active_domain, "use_llm": use_llm}
                    resp = requests.post(f"{API_URL}/api/ask", json=payload, timeout=30).json()
                    
                    if resp.get("status") == "CLARIFY":
                        st.warning(f"🤔 The agent needs clarification: **{resp['clarification']['surface']}**")
                        st.json(resp.get("clarification", {}))
                    elif resp.get("status") == "SEMANTIC_GAP":
                        st.error(f"🚫 Semantic gap detected: {resp.get('error', 'Unknown')}")
                    else:
                        st.success("✅ Query resolved!")
                        st.markdown(f"### Answer\n{resp.get('answer', 'No answer generated.')}")
                        
                        mcol1, mcol2 = st.columns(2)
                        mcol1.metric("Confidence", f"{resp.get('confidence', 0):.0%}")
                        mcol2.metric("Agent", f"{resp.get('agent', {}).get('source', '?')} / "
                                     f"{resp.get('agent', {}).get('model', '?')}")
                        
                        # Reasoning Stages
                        with st.expander("📊 Reasoning Pipeline Stages"):
                            for stage in resp.get("stages", []):
                                st.markdown(f"**Stage {stage['n']}: {stage['name']}**")
                                for line in stage.get("lines", []):
                                    st.text(f"  {line}")
                        
                        with st.expander("🔗 Grounding Entities"):
                            st.json(resp.get("citations", []))
                        
                        with st.expander("📝 Ontology Context Block"):
                            st.code(resp.get("context_block", ""), language="text")
                        
                        if resp.get("action_card"):
                            with st.expander("⚡ Proposed Action"):
                                st.json(resp["action_card"])
                                
                except Exception as e:
                    st.error(f"API Error: {e}")
    else:
        st.info("Select a domain from the sidebar.")


# ============================================================
# TAB 6: Domain Manager
# ============================================================
with tabs[5]:
    st.header("📂 Domain Manager")
    
    col_upload, col_rebuild = st.columns(2)
    
    with col_upload:
        st.subheader("Upload Domain Pack")
        st.markdown("Upload YAML files (`objects.yaml`, `functions.yaml`, `actions.yaml`, "
                     "`domain.yaml`) to create or extend a domain.")
        
        uploaded_files = st.file_uploader("Upload YAML files", type=["yaml", "yml"],
                                          accept_multiple_files=True)
        pack_name = st.text_input("Target Pack Directory",
                                  placeholder="e.g., marketing, logistics, finance")
        
        if st.button("📤 Upload & Rebuild", type="primary"):
            if uploaded_files and pack_name:
                for uf in uploaded_files:
                    save_dir = os.path.join("packs", pack_name)
                    os.makedirs(save_dir, exist_ok=True)
                    file_path = os.path.join(save_dir, uf.name)
                    with open(file_path, "wb") as f:
                        f.write(uf.getbuffer())
                    st.success(f"✅ Saved `{uf.name}` → `{file_path}`")
                
                with st.spinner("Recompiling Semantic Registry..."):
                    try:
                        resp = requests.post(f"{API_URL}/api/rebuild", timeout=10).json()
                        if resp.get("status") == "success":
                            st.success(f"✅ Registry rebuilt! Domains: {resp.get('domains', [])}")
                            st.balloons()
                        else:
                            st.error(f"❌ Compilation Error: {resp.get('message')}")
                    except Exception as e:
                        st.error(f"Failed: {e}")
            else:
                st.warning("Upload at least one YAML file and specify a pack name.")
    
    with col_rebuild:
        st.subheader("Quick Actions")
        
        if st.button("🔄 Rebuild Registry"):
            try:
                resp = requests.post(f"{API_URL}/api/rebuild", timeout=10).json()
                if resp.get("status") == "success":
                    st.success(f"✅ Rebuilt! Active domains: {resp.get('domains', [])}")
                else:
                    st.error(f"Error: {resp.get('message')}")
            except Exception as e:
                st.error(f"Failed: {e}")
        
        st.divider()
        st.subheader("Pack Structure Guide")
        st.code("""
packs/
└── your_domain/
    ├── domain.yaml      # Domain manifest (required)
    ├── objects.yaml      # Object types + properties
    ├── links.yaml        # Standalone link definitions
    ├── functions.yaml    # Computed metrics & object sets
    ├── actions.yaml      # Tier-based action definitions
    └── events.yaml       # Event type rules
        """, language="text")


# ============================================================
# TAB 7: Lineage
# ============================================================
with tabs[6]:
    st.header("🔗 Data Lineage")
    
    if active_domain:
        try:
            schema_data = requests.get(f"{API_URL}/api/schema",
                                       params={"domain": active_domain}, timeout=5).json()
            type_names = list(schema_data.get("object_types", {}).keys())
        except Exception:
            type_names = []
        
        if type_names:
            sel_type = st.selectbox("Select Object Type for Lineage", type_names, key="lineage_type")
            
            if st.button("Show Lineage", type="primary"):
                try:
                    resp = requests.get(f"{API_URL}/api/lineage/{sel_type}", timeout=5).json()
                    
                    st.markdown(f"**Datasource:** `{resp.get('datasource', 'N/A')}`")
                    st.markdown(f"**Primary Key:** `{resp.get('primary_key', 'N/A')}`")
                    
                    st.subheader("Property Sources")
                    lineage_rows = []
                    for pname, pdef in resp.get("properties", {}).items():
                        lineage_rows.append({
                            "Property": pname,
                            "Type": pdef.get("type", ""),
                            "Binding": pdef.get("binding", ""),
                            "Table": pdef.get("source_table", ""),
                            "Column": pdef.get("source_column", ""),
                            "Function": pdef.get("function", ""),
                            "Formula": pdef.get("formula", "")
                        })
                    if lineage_rows:
                        st.dataframe(pd.DataFrame(lineage_rows), use_container_width=True, hide_index=True)
                    
                    if resp.get("link_dependencies"):
                        st.subheader("Link Dependencies")
                        for lname, ldef in resp["link_dependencies"].items():
                            st.markdown(f"- **{lname}** → `{ldef['to_type']}` "
                                        f"({ldef['cardinality']}) via `{', '.join(ldef['join_columns'])}`")
                except Exception as e:
                    st.error(f"Error: {e}")


# ============================================================
# TAB 8: Audit Log
# ============================================================
with tabs[7]:
    st.header("📜 Audit Log")
    
    if st.button("Refresh Log"):
        pass  # Just triggers rerun
    
    try:
        resp = requests.get(f"{API_URL}/api/audit-log", timeout=5).json()
        log = resp.get("log", [])
        
        if log:
            df = pd.DataFrame(log)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No actions in the audit log yet. Actions are logged when you approve proposed changes through the Agent.")
    except Exception as e:
        st.error(f"Could not fetch audit log: {e}")
