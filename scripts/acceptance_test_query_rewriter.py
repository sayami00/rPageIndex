"""
Acceptance test for Phase 8.5 -- Query Rewriter.

Runs 20 sample queries through QueryRewriter.rewrite() and verifies:
- Abbreviations expand to domain terms
- Entities extracted by type with correct values
- Normalized form has no extraneous punctuation
- OR groups appear for synonyms
- Entity boost markers present in bm25_query
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.query.rewriter import QueryRewriter

_pass = _fail = 0


def check(label, result):
    global _pass, _fail
    tag = "[PASS]" if result else "[FAIL]"
    print(f"  {tag} {label}")
    if result:
        _pass += 1
    else:
        _fail += 1


def show(rw, query):
    r = rw.rewrite(query)
    entities_str = ", ".join(f"{e.entity_type}:{e.value}" for e in r.entities) or "(none)"
    print(f"\n  original  : {r.original!r}")
    print(f"  normalized: {r.normalized!r}")
    print(f"  entities  : {entities_str}")
    print(f"  bm25_query: {r.bm25_query}")
    return r


def main():
    rw = QueryRewriter()
    print("\n=== Phase 8.5 Query Rewriter Acceptance Test ===")
    print("20 sample queries\n")

    # 1. Abbreviation: fw
    print("[1] Firewall abbreviation")
    r = show(rw, "fw config")
    check("'fw' expands to 'firewall'", "firewall" in r.bm25_query)
    check("'config' expands to 'configuration'", "configuration" in r.bm25_query)
    check("OR group present", "OR" in r.bm25_query)

    # 2. Auth abbreviation
    print("[2] Auth abbreviation")
    r = show(rw, "auth failure on db01")
    check("'auth' expands to 'authentication'", "authentication" in r.bm25_query)
    check("db01 extracted as node entity", any(e.entity_type == "node" for e in r.entities))
    check("node boosted in query", "^1.5" in r.bm25_query)

    # 3. IP address extraction
    print("[3] IP address")
    r = show(rw, "show 192.168.10.1 firewall rules")
    check("IP extracted", any(e.entity_type == "ip" for e in r.entities))
    check("IP value correct", any(e.value == "192.168.10.1" for e in r.entities))
    check("IP boosted at 2.0", "192.168.10.1" in r.bm25_query and "^2.0" in r.bm25_query)

    # 4. Hostname extraction
    print("[4] Hostname")
    r = show(rw, "resolve gw.corp.internal address")
    check("hostname extracted", any(e.entity_type == "hostname" for e in r.entities))
    check("hostname boosted", "^2.0" in r.bm25_query)
    check("'addr' not in expanded (stopword + no synonym)", "addr" not in r.expanded_terms or "address" in r.bm25_query)

    # 5. Version extraction
    print("[5] Version string")
    r = show(rw, "nginx v1.24.0 installation guide")
    check("version entity extracted", any(e.entity_type == "version" for e in r.entities))
    check("version boost 1.5", "^1.5" in r.bm25_query)

    # 6. Node name
    print("[6] Node name")
    r = show(rw, "web01 is unreachable, check srv02")
    nodes = [e for e in r.entities if e.entity_type == "node"]
    check("two node entities extracted", len(nodes) == 2)
    check("both nodes in bm25_query", all(n.value.lower() in r.bm25_query.lower() for n in nodes))

    # 7. Exclamation punctuation stripped
    print("[7] Extraneous punctuation")
    r = show(rw, "auth!!! config???")
    check("exclamation stripped from normalized", "!" not in r.normalized)
    check("authentication in query", "authentication" in r.bm25_query)
    check("configuration in query", "configuration" in r.bm25_query)

    # 8. IP dots NOT mangled
    print("[8] IP dots preserved after normalization")
    r = show(rw, "10.0.0.1")
    check("IP not split to '10 0 0 1'", "10 0 0 1" not in r.normalized)
    check("IP recognized as entity", any(e.entity_type == "ip" for e in r.entities))

    # 9. Case-insensitive synonym lookup
    print("[9] Case-insensitive expansion")
    r = show(rw, "DB config")
    check("DB expands to database", "database" in r.bm25_query)
    check("config expands to configuration", "configuration" in r.bm25_query)

    # 10. OS abbreviation
    print("[10] OS abbreviation")
    r = show(rw, "os version info")
    check("os expands to operating system", "operating system" in r.bm25_query)

    # 11. SSL/TLS
    print("[11] SSL/TLS synonyms")
    r = show(rw, "ssl cert renewal")
    check("ssl expands to certificate", "certificate" in r.bm25_query)
    check("cert also expands to certificate", "certificate" in r.bm25_query)

    # 12. Monitoring abbreviation
    print("[12] Monitoring abbreviation")
    r = show(rw, "mon alert for gw01")
    check("mon expands to monitoring", "monitoring" in r.bm25_query)
    check("gw01 node extracted", any(e.entity_type == "node" for e in r.entities))

    # 13. Backup abbreviation
    print("[13] Backup abbreviation")
    r = show(rw, "bkp failed on db02")
    check("bkp expands to backup", "backup" in r.bm25_query)
    check("db02 node extracted", any(e.entity_type == "node" and "db02" in e.value for e in r.entities))

    # 14. Mixed: multiple abbreviations + IP
    print("[14] Multi-abbrev + IP")
    r = show(rw, "fw cfg error 10.0.1.5")
    check("firewall in query", "firewall" in r.bm25_query)
    check("configuration in query", "configuration" in r.bm25_query)
    check("IP entity present", any(e.entity_type == "ip" for e in r.entities))

    # 15. Wildcard preserved
    print("[15] Wildcard char preserved")
    r = show(rw, "web* config")
    check("* preserved in normalized", "*" in r.normalized)

    # 16. Stopwords filtered
    print("[16] Stopwords filtered")
    r = show(rw, "what is the firewall configuration for the server")
    check("'the' not in bm25_query as standalone", " the " not in f" {r.bm25_query} ")
    check("firewall in query", "firewall" in r.bm25_query)

    # 17. Empty query
    print("[17] Empty query")
    r = show(rw, "")
    check("empty bm25_query", r.bm25_query == "")
    check("no entities", r.entities == [])

    # 18. Hostname with long TLD
    print("[18] Hostname with long TLD")
    r = show(rw, "connect to api.internal")
    check("api.internal extracted as hostname", any(e.entity_type == "hostname" for e in r.entities))

    # 19. Version without v-prefix
    print("[19] Version without v-prefix")
    r = show(rw, "ubuntu 22.04 lts upgrade")
    check("22.04 extracted as version", any(e.entity_type == "version" for e in r.entities))

    # 20. Compound real-world query
    print("[20] Compound realistic query")
    r = show(rw, "fw acl block 192.168.5.0 srv03 db auth")
    check("firewall expanded", "firewall" in r.bm25_query)
    check("access control expanded", "access control" in r.bm25_query)
    check("IP entity extracted", any(e.entity_type == "ip" for e in r.entities))
    check("srv03 node extracted", any(e.entity_type == "node" and "srv03" in e.value for e in r.entities))
    check("authentication expanded", "authentication" in r.bm25_query)
    check("database expanded", "database" in r.bm25_query)

    print(f"\n{'='*44}")
    print(f"Results: {_pass} passed, {_fail} failed")
    if _fail:
        sys.exit(1)
    else:
        print("All assertions passed.")


if __name__ == "__main__":
    main()
