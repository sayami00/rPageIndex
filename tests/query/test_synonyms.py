from src.query.synonyms import SYNONYMS


def test_fw_expands_to_firewall():
    assert "firewall" in SYNONYMS["fw"]


def test_auth_expands_to_authentication():
    assert "authentication" in SYNONYMS["auth"]


def test_db_expands_to_database():
    assert "database" in SYNONYMS["db"]


def test_config_expands_to_configuration():
    assert "configuration" in SYNONYMS["config"]


def test_cfg_expands_to_configuration():
    assert "configuration" in SYNONYMS["cfg"]


def test_os_expands_to_operating_system():
    assert "operating system" in SYNONYMS["os"]


def test_all_values_are_lists():
    for key, val in SYNONYMS.items():
        assert isinstance(val, list), f"SYNONYMS[{key!r}] is not a list"
        assert all(isinstance(v, str) for v in val), f"SYNONYMS[{key!r}] contains non-str"


def test_no_empty_expansion_lists():
    for key, val in SYNONYMS.items():
        assert len(val) > 0, f"SYNONYMS[{key!r}] is empty"


def test_keys_are_lowercase():
    for key in SYNONYMS:
        assert key == key.lower(), f"Key {key!r} not lowercase"


def test_ssl_and_tls_both_present():
    assert "ssl" in SYNONYMS
    assert "tls" in SYNONYMS


def test_mon_expands_to_monitoring():
    assert "monitoring" in SYNONYMS["mon"]
