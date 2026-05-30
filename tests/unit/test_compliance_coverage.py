"""Compliance coverage computation tests."""

from packages.compliance.coverage import compute_coverage, load_framework_controls


def test_load_nist_controls():
    controls = load_framework_controls("NIST_CSF_2")
    assert len(controls) >= 4
    assert controls[0]["id"]


def test_compute_coverage_with_findings():
    findings = [{"severity": "critical", "mitre_ttps": ["T1078"]}]
    result = compute_coverage("NIST_CSF_2", findings)
    assert "coverage_pct" in result
    assert result["controls"]
    assert "T1078" in result["attck_techniques"]
