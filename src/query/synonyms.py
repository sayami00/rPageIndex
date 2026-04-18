"""
Domain synonym dictionary — derived from document vocabulary:
heading words, key-value keys, and section titles observed in corpus.

Observed vocabulary includes:
  authentication, configuration, firewall, network, server, database,
  monitoring, backup, deployment, interface, management, certificate,
  connection, service, environment, production, infrastructure, inventory,
  performance, operating system, gateway, address, password, encryption.

Format: token (lowercase) -> list of expansions to OR into query.
The original token is always included by the expander; this dict
only lists *additional* terms to add.
"""

SYNONYMS: dict[str, list[str]] = {
    # network / connectivity
    "fw":      ["firewall"],
    "net":     ["network"],
    "nw":      ["network"],
    "vlan":    ["network"],
    "vpn":     ["network", "tunnel"],
    "acl":     ["access control"],
    "dns":     ["name resolution", "nameserver"],
    "dhcp":    ["address assignment", "configuration"],
    "iface":   ["interface"],
    "int":     ["interface"],
    "gw":      ["gateway"],
    "addr":    ["address"],
    "subnet":  ["network", "address"],

    # auth / security
    "auth":    ["authentication", "authorization"],
    "sec":     ["security"],
    "ssl":     ["certificate", "tls", "encryption"],
    "tls":     ["certificate", "ssl", "encryption"],
    "cert":    ["certificate"],
    "certs":   ["certificate"],
    "pw":      ["password"],
    "pwd":     ["password"],
    "cred":    ["credentials", "password"],
    "creds":   ["credentials", "password"],

    # configuration / ops
    "cfg":     ["configuration"],
    "conf":    ["configuration"],
    "config":  ["configuration"],
    "mgmt":    ["management"],
    "mon":     ["monitoring"],
    "bkp":     ["backup"],
    "bak":     ["backup"],
    "deploy":  ["deployment"],
    "ci":      ["continuous integration", "pipeline"],
    "cd":      ["deployment", "pipeline"],
    "env":     ["environment"],
    "prod":    ["production"],
    "dev":     ["development"],
    "infra":   ["infrastructure"],
    "repo":    ["repository"],

    # servers / services
    "srv":     ["server"],
    "svc":     ["service"],
    "db":      ["database"],
    "lb":      ["load balancer", "load balancing"],
    "conn":    ["connection"],
    "svc":     ["service"],

    # system / performance
    "os":      ["operating system"],
    "ver":     ["version"],
    "perf":    ["performance"],
    "mem":     ["memory"],
    "cpu":     ["processor"],
    "api":     ["interface"],
    "http":    ["web"],
    "https":   ["web", "secure"],

    # inventory / status
    "inv":     ["inventory"],
    "info":    ["information"],
    "stat":    ["status", "statistics"],
    "stats":   ["statistics", "status"],
    "err":     ["error"],
    "errs":    ["errors"],
    "warn":    ["warning"],
    "crit":    ["critical"],
    "alert":   ["alerting", "monitoring"],
}
