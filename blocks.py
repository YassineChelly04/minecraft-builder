"""
Back-compat shim. The valid-block set now lives in the version-aware registry
(knowledge.blocks_registry). This module re-exports the set resolved for the
configured TARGET_MC_VERSION so existing importers (`from blocks import
VALID_BLOCKS`) keep working unchanged, while the set tracks the target version.
"""
from config import TARGET_MC_VERSION
from knowledge.blocks_registry import resolve

VALID_BLOCKS = resolve(TARGET_MC_VERSION)
