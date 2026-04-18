import pytest
from src.query.normalizer import normalize


def test_lowercase():
    assert normalize("Firewall CONFIG") == "firewall config"


def test_strip_exclamation():
    assert normalize("auth!!!") == "auth"


def test_preserve_ip():
    assert normalize("show 192.168.1.1 rules") == "show 192.168.1.1 rules"


def test_preserve_hostname():
    assert normalize("dns.corp.internal lookup") == "dns.corp.internal lookup"


def test_preserve_version():
    assert normalize("nginx/1.24 config") == "nginx/1.24 config"


def test_preserve_hyphen_in_node():
    assert normalize("server-01 status") == "server-01 status"


def test_strip_trailing_punctuation():
    result = normalize("what is the firewall?")
    assert "?" in result  # ? is wildcard char — preserved


def test_strip_bare_comma():
    assert "," not in normalize("auth, config, backup")


def test_collapse_spaces():
    assert normalize("auth  config   backup") == "auth config backup"


def test_strip_leading_trailing():
    assert normalize("  firewall  ") == "firewall"


def test_empty_string():
    assert normalize("") == ""


def test_preserve_wildcard_star():
    result = normalize("web* server")
    assert "*" in result


def test_semicolon_stripped():
    assert ";" not in normalize("auth; config")


def test_bare_dot_stripped():
    result = normalize("end of sentence. next word")
    assert ". " not in result


def test_dot_in_ip_preserved():
    result = normalize("10.0.0.1")
    assert "10.0.0.1" in result
