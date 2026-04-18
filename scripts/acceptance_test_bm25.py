"""
Acceptance test for Phase 8 — Multi-Index BM25.

Usage:
    python scripts/acceptance_test_bm25.py

No external services required — runs entirely on synthetic data.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.assembly.models import PageRecord
from src.bm25.indexer import doc_count, open_or_create
from src.bm25.pipeline import IndexPipeline
from src.bm25.schemas import page_schema
from src.bm25.searcher import IndexSearcher
from src.features.models import FeatureRecord
from src.section_tree.models import SectionTree, TreeNode
from src.tables.models import TableOutput


# ── synthetic data builders ───────────────────────────────────────────────────

def _page(page_number, doc_id, heading, body, table_text="", quality=0.9):
    return PageRecord(
        doc_id=doc_id, source_file=f"{doc_id}.pdf",
        page_number=page_number,
        heading_text=heading, body_text=body, table_text=table_text,
        page_search_text=f"{heading} {body} {table_text}".strip(),
        quality_floor=quality, block_count=3,
    )


def _tree(doc_id):
    root = TreeNode(f"{doc_id}::root", doc_id, "__root__", "", 0, 0, None, page_spans=(1, 10))
    h1 = TreeNode(f"{doc_id}::h1::b1", doc_id, "Network Configuration", "b1", 1, 1,
                  root.node_id, page_spans=(1, 5), summary="Overview of network setup.")
    h2 = TreeNode(f"{doc_id}::h2::b2", doc_id, "Firewall Rules", "b2", 2, 2,
                  h1.node_id, page_spans=(2, 3), summary="Detailed firewall rule definitions.")
    h1b = TreeNode(f"{doc_id}::h1::b3", doc_id, "Server Inventory", "b3", 1, 1,
                   root.node_id, page_spans=(6, 10), summary="List of managed servers.")
    root.children = [h1, h1b]
    h1.children = [h2]
    return SectionTree(doc_id=doc_id, source_file=f"{doc_id}.pdf", root=root, total_pages=10)


def _features(doc_id):
    return {
        "named_entity": [
            FeatureRecord("named_entity", "192.168.10.1", "b10", doc_id, 2, entity_subtype="ip"),
            FeatureRecord("named_entity", "192.168.10.2", "b11", doc_id, 2, entity_subtype="ip"),
            FeatureRecord("named_entity", "gw.corp.internal", "b12", doc_id, 3, entity_subtype="hostname"),
            FeatureRecord("named_entity", "dns.corp.internal", "b13", doc_id, 3, entity_subtype="hostname"),
        ],
        "key_value_pair": [
            FeatureRecord("key_value_pair", "Ubuntu 22.04 LTS", "b14", doc_id, 4, key="OS"),
            FeatureRecord("key_value_pair", "nginx/1.24", "b15", doc_id, 5, key="Webserver"),
        ],
    }


def _tables(doc_id):
    return [
        TableOutput(
            table_id=f"{doc_id}_t1", doc_id=doc_id,
            source_pages=[6, 7],
            headers=["Hostname", "IP Address", "Role", "Status"],
            structured=[
                {"Hostname": "web01", "IP Address": "10.0.1.10", "Role": "web", "Status": "active"},
                {"Hostname": "db01", "IP Address": "10.0.1.20", "Role": "database", "Status": "active"},
                {"Hostname": "cache01", "IP Address": "10.0.1.30", "Role": "cache", "Status": "standby"},
            ],
            search_rows=[
                "Hostname web01 IP Address 10.0.1.10 Role web Status active",
                "Hostname db01 IP Address 10.0.1.20 Role database Status active",
                "Hostname cache01 IP Address 10.0.1.30 Role cache Status standby",
            ],
        ),
    ]


def _pages(doc_id):
    return [
        _page(1, doc_id, "Network Configuration", "This document covers network setup and configuration."),
        _page(2, doc_id, "Firewall Rules", "Inbound rules allow HTTPS and SSH traffic from trusted subnets."),
        _page(3, doc_id, "Firewall Rules", "Outbound rules restrict access to approved destinations."),
        _page(4, doc_id, "Operating System", "All servers run Ubuntu with automated patch management."),
        _page(5, doc_id, "Web Server", "nginx handles load balancing and SSL termination."),
        _page(6, doc_id, "Server Inventory", "Complete inventory of production servers and their roles.",
              table_text="web01 10.0.1.10 active db01 10.0.1.20 active"),
        _page(7, doc_id, "Server Inventory", "Cache servers run Redis in cluster mode.", quality=0.75),
        _page(8, doc_id, "Monitoring", "Prometheus collects metrics from all production hosts."),
        _page(9, doc_id, "Alerting", "PagerDuty integration for on-call escalation."),
        _page(10, doc_id, "Backup Policy", "Daily snapshots retained for 30 days."),
    ]


# ── assertion helper ──────────────────────────────────────────────────────────

_pass = _fail = 0


def check(label, result):
    global _pass, _fail
    if result:
        print(f"  [PASS] {label}")
        _pass += 1
    else:
        print(f"  [FAIL] {label}")
        _fail += 1


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        index_root = str(Path(tmpdir) / "index")
        doc_id = "netdoc"

        # Write fake source file for hash tracking
        src_file = Path(tmpdir) / "netdoc.pdf"
        src_file.write_bytes(b"fake pdf content v1")
        source_files = {doc_id: str(src_file)}

        pipeline = IndexPipeline(index_root=index_root)
        searcher_factory = lambda: IndexSearcher(index_root)

        print("\n=== Phase 8 Acceptance Test ===\n")

        # ── Build initial index ───────────────────────────────────────────────
        print("Building initial index...")
        stats = pipeline.build(
            records=_pages(doc_id),
            trees=[_tree(doc_id)],
            feature_indices=[_features(doc_id)],
            tables=_tables(doc_id),
            source_files=source_files,
        )
        print(f"  Stats: {stats['indices']}\n")

        s = searcher_factory()

        # ── page_index queries ────────────────────────────────────────────────
        print("[page_index] — 5 matching queries + 1 non-match:")
        check("firewall -> matches inbound/outbound pages", len(s.search_pages("firewall")) >= 1)
        check("nginx -> matches web server page", len(s.search_pages("nginx")) >= 1)
        check("monitoring -> matches monitoring page", len(s.search_pages("monitoring")) >= 1)
        check("backup -> matches backup policy page", len(s.search_pages("backup")) >= 1)
        check("Ubuntu patch -> matches OS page", len(s.search_pages("Ubuntu patch")) >= 1)
        check("xyzqqqnotexist -> zero results", s.search_pages("xyzqqqnotexist") == [])

        # ── section_index queries ─────────────────────────────────────────────
        print("\n[section_index] — 5 matching queries + 1 non-match:")
        check("network -> matches 'Network Configuration'", len(s.search_sections("network")) >= 1)
        check("firewall -> matches 'Firewall Rules'", len(s.search_sections("firewall")) >= 1)
        check("inventory -> matches 'Server Inventory'", len(s.search_sections("inventory")) >= 1)
        check("overview -> matches summary text", len(s.search_sections("overview")) >= 1)
        check("detailed -> matches firewall summary", len(s.search_sections("detailed")) >= 1)
        check("xyzqqqnotexist -> zero results", s.search_sections("xyzqqqnotexist") == [])

        # ── feature_index queries (stemmed + exact) ───────────────────────────
        print("\n[feature_index] — 5 matching queries + 1 non-match:")
        check("stemmed: ubuntu -> matches 'Ubuntu 22.04 LTS'",
              len(s.search_features("ubuntu")) >= 1)
        check("stemmed: nginx -> matches nginx feature",
              len(s.search_features("nginx")) >= 1)
        check("exact IP: 192.168.10.1 -> matches",
              len(s.search_features("192.168.10.1", exact=True)) >= 1)
        check("exact hostname: gw.corp.internal -> matches",
              len(s.search_features("gw.corp.internal", exact=True)) >= 1)
        check("feature_type filter: named_entity -> only named_entity results",
              all(r["feature_type"] == "named_entity"
                  for r in s.search_features("192", feature_type="named_entity")))
        check("exact: 10.99.99.99 -> zero results (not indexed)",
              s.search_features("10.99.99.99", exact=True) == [])

        # ── table_index queries ───────────────────────────────────────────────
        print("\n[table_index] — 5 matching queries + 1 non-match:")
        check("Hostname -> matches table header", len(s.search_tables("Hostname")) >= 1)
        check("database -> matches db01 row", len(s.search_tables("database")) >= 1)
        check("cache -> matches cache01 row", len(s.search_tables("cache")) >= 1)
        check("active -> matches status column", len(s.search_tables("active")) >= 1)
        check("standby -> matches standby status", len(s.search_tables("standby")) >= 1)
        check("xyzqqqnotexist -> zero results", s.search_tables("xyzqqqnotexist") == [])

        # ── section_path populated in page_index ─────────────────────────────
        print("\n[section_path] — page_index gets breadcrumb from tree:")
        page_results = s.search_pages("firewall")
        if page_results:
            sp = page_results[0].get("section_path", "")
            check(f"section_path non-empty: '{sp}'", sp != "")
        else:
            check("firewall page found for section_path check", False)

        # ── incremental update: hash changed -> re-indexes ─────────────────────
        print("\n[incremental] — changed hash triggers re-index:")
        src_file.write_bytes(b"completely new document content version 2")
        new_pages = [_page(1, doc_id, "Completely New Topic", "Redis cluster configuration details.")]
        pipeline.build(new_pages, [_tree(doc_id)], [_features(doc_id)], [], source_files)
        s2 = searcher_factory()
        check("new content findable after re-index", len(s2.search_pages("Redis cluster")) >= 1)
        check("old content gone after re-index", len(s2.search_pages("backup policy")) == 0)

        # ── incremental skip: same hash -> no re-index ─────────────────────────
        print("\n[incremental] — same hash skips re-index:")
        idx = open_or_create(index_root, "page", page_schema)
        count_before = doc_count(idx)
        pipeline.build(new_pages, [_tree(doc_id)], [_features(doc_id)], [], source_files)
        count_after = doc_count(idx)
        check("doc count unchanged when hash unchanged", count_before == count_after)

        # ── metadata stats ────────────────────────────────────────────────────
        print("\n[metadata] — index build stats:")
        from src.bm25.metadata import IndexMetadata
        meta = IndexMetadata(index_root)
        for idx_name in ("page", "section", "feature", "table"):
            stats = meta.index_stats(idx_name)
            print(f"  {idx_name}: {stats}")
            check(f"{idx_name} metadata recorded", bool(stats))

        # ── summary ───────────────────────────────────────────────────────────
        print(f"\n{'='*40}")
        print(f"Results: {_pass} passed, {_fail} failed")
        if _fail:
            sys.exit(1)
        else:
            print("All assertions passed.")


if __name__ == "__main__":
    main()
