"""
Configuration constants for the SCB-only employment data pipeline.
"""

from typing import Dict, List, Literal, Tuple

# ======================================================
#  DATA SOURCES / CONSTANTS
# ======================================================
TAXONOMY: Literal["ssyk2012"] = "ssyk2012"

TRANSLATION_URL: str = (
    "https://raw.githubusercontent.com/joseph-data/07_translate_ssyk/main/"
    "02_translation_files/ssyk2012_en.xlsx"
)

# SCB table definitions
TABLES: Dict[str, Tuple[str, str, str, str, str]] = {
    "14_to_18": ("en", "AM", "AM0208", "AM0208E", "YREG51"),
    "19_to_21": ("en", "AM", "AM0208", "AM0208E", "YREG51N"),
    "20_to_23": ("en", "AM", "AM0208", "AM0208E", "YREG51BAS"),
}

AGE_EXCLUSIONS: List[str] = ["65-69 years"]
EXCLUDED_CODES: List[str] = ["0002", "0000"]

# ======================================================
#  UI DEFAULTS
# ======================================================
LEVEL_OPTIONS: List[Tuple[str, str]] = [
    ("Level 4 (4-digit)", "4"),
    ("Level 3 (3-digit)", "3"),
    ("Level 2 (2-digit)", "2"),
    ("Level 1 (1-digit)", "1"),
]

DEFAULT_LEVEL: str = "3"

GLOBAL_YEAR_MIN: int = 2014
GLOBAL_YEAR_MAX: int = 2023
DEFAULT_YEAR_RANGE: Tuple[int, int] = (GLOBAL_YEAR_MIN, GLOBAL_YEAR_MAX)

AGE_ORDER: List[str] = [
    "16-24",
    "25-29",
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
    "55-59",
    "60-64",
]
