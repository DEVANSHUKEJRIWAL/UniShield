"""Blast radius helpers — re-exported from path analyzer for spec layout."""

from unishield.attack_path.path_analyzer import AttackPathAnalyzer

compute_blast_radii = AttackPathAnalyzer.compute_blast_radii

__all__ = ["compute_blast_radii", "AttackPathAnalyzer"]
