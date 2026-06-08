"""Fallback map: lower-cased outlet name fragment → ISO 3166-1 alpha-2 country code.

Used when a source name cannot be matched against the curated registry.
Keys are lower-case substrings; the first key that appears anywhere in the
lower-cased source name wins.  Keep entries sorted by specificity (longer /
more specific first within a country block) so substring matches don't fire
too broadly.
"""

from __future__ import annotations

# fmt: off
_FRAGMENT_TO_ISO2: list[tuple[str, str]] = [
    # United States
    ("new york times",      "US"), ("nyt",                 "US"),
    ("washington post",     "US"), ("wall street journal",  "US"),
    ("wsj",                 "US"), ("los angeles times",    "US"),
    ("chicago tribune",     "US"), ("usa today",            "US"),
    ("newsweek",            "US"), ("the atlantic",         "US"),
    ("time magazine",       "US"), ("time.com",             "US"),
    ("politico",            "US"), ("the hill",             "US"),
    ("axios",               "US"), ("buzzfeed",             "US"),
    ("business insider",    "US"), ("cnbc",                 "US"),
    ("bloomberg",           "US"), ("fortune",              "US"),
    ("forbes",              "US"), ("wired",                "US"),
    ("techcrunch",          "US"), ("the verge",            "US"),
    ("vice",                "US"), ("vox",                  "US"),
    ("huffpost",            "US"), ("huffington",           "US"),
    ("msnbc",               "US"), ("cbs news",             "US"),
    ("nbc news",            "US"), ("abc news",             "US"),
    ("market watch",        "US"), ("marketwatch",          "US"),
    ("associated press",    "US"), ("ap news",              "US"),

    # United Kingdom
    ("bbc",                 "GB"), ("the guardian",         "GB"),
    ("the independent",     "GB"), ("the telegraph",        "GB"),
    ("daily mail",          "GB"), ("daily mirror",         "GB"),
    ("the sun",             "GB"), ("the times",            "GB"),
    ("financial times",     "GB"), ("sky news",             "GB"),
    ("reuters",             "GB"), ("evening standard",     "GB"),
    ("the economist",       "GB"),

    # France
    ("le monde",            "FR"), ("le figaro",            "FR"),
    ("liberation",          "FR"), ("france 24",            "FR"),
    ("france24",            "FR"), ("rfi",                  "FR"),
    ("l'express",           "FR"),

    # Germany
    ("spiegel",             "DE"), ("die welt",             "DE"),
    ("frankfurter",         "DE"), ("sueddeutsche",         "DE"),
    ("deutsche welle",      "DE"), ("dw.com",               "DE"),
    ("focus online",        "DE"), ("bild",                 "DE"),

    # Russia
    ("rt.com",              "RU"), ("russia today",         "RU"),
    ("tass",                "RU"), ("ria novosti",          "RU"),
    ("pravda",              "RU"), ("kommersant",           "RU"),
    ("interfax",            "RU"),

    # China
    ("xinhua",              "CN"), ("global times",         "CN"),
    ("china daily",         "CN"), ("people's daily",       "CN"),
    ("cgtn",                "CN"), ("south china morning",  "CN"),

    # Qatar / Middle East
    ("al jazeera",          "QA"), ("aljazeera",            "QA"),
    ("al arabiya",          "SA"), ("arab news",            "SA"),
    ("the national",        "AE"), ("gulf news",            "AE"),
    ("times of israel",     "IL"), ("haaretz",              "IL"),
    ("jerusalem post",      "IL"), ("al monitor",           "US"),
    ("middle east eye",     "GB"),

    # India
    ("times of india",      "IN"), ("the hindu",            "IN"),
    ("hindustan times",     "IN"), ("ndtv",                 "IN"),
    ("india today",         "IN"), ("economic times",       "IN"),
    ("firstpost",           "IN"), ("scroll.in",            "IN"),

    # Japan
    ("nhk",                 "JP"), ("the japan times",      "JP"),
    ("asahi shimbun",       "JP"), ("yomiuri",              "JP"),
    ("nikkei",              "JP"),

    # Australia
    ("abc australia",       "AU"), ("the sydney morning",   "AU"),
    ("the age",             "AU"), ("the australian",       "AU"),
    ("news.com.au",         "AU"), ("abc.net.au",           "AU"),

    # Canada
    ("cbc",                 "CA"), ("globe and mail",       "CA"),
    ("toronto star",        "CA"), ("national post",        "CA"),
    ("la presse",           "CA"),

    # Brazil
    ("folha",               "BR"), ("globo",                "BR"),
    ("estadao",             "BR"), ("veja",                 "BR"),

    # South Korea
    ("korea herald",        "KR"), ("joongang",             "KR"),
    ("chosun",              "KR"), ("yonhap",               "KR"),

    # Turkey
    ("hurriyet",            "TR"), ("daily sabah",          "TR"),
    ("anadolu",             "TR"),

    # Iran
    ("press tv",            "IR"), ("irna",                 "IR"),
    ("tasnim",              "IR"), ("mehr news",            "IR"),

    # Pakistan
    ("dawn",                "PK"), ("the news international","PK"),
    ("geo news",            "PK"),

    # Singapore
    ("straits times",       "SG"), ("channel news asia",    "SG"),
    ("cna",                 "SG"),

    # South Africa
    ("mail & guardian",     "ZA"), ("daily maverick",       "ZA"),
    ("news24",              "ZA"), ("timeslive",             "ZA"),
]
# fmt: on


def country_for_name(name: str) -> str | None:
    """Return best-guess ISO alpha-2 country for a source name, or None."""
    lower = name.lower()
    for fragment, iso2 in _FRAGMENT_TO_ISO2:
        if fragment in lower:
            return iso2
    return None
