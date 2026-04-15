from dataclasses import dataclass


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    category: str
    region: str


FEED_SOURCES = [
    FeedSource(
        name="Notizie di Prato",
        url="https://www.notiziediprato.it/feed/",
        category="local",
        region="Prato",
    ),
    FeedSource(
        name="La Nazione Prato",
        url="https://www.lanazione.it/prato/rss",
        category="local",
        region="Prato",
    ),
    FeedSource(
        name="Corriere Milano",
        url="https://www.corriere.it/dynamic-feed/rss/section/Milano.xml",
        category="metro",
        region="Milano",
    ),
    FeedSource(
        name="Corriere Roma",
        url="https://www.corriere.it/dynamic-feed/rss/section/Roma.xml",
        category="metro",
        region="Roma",
    ),
    FeedSource(
        name="ANSA Toscana",
        url="https://www.ansa.it/toscana/notizie/toscana_rss.xml",
        category="region",
        region="Toscana",
    ),
    FeedSource(
        name="ANSA Lombardia",
        url="https://www.ansa.it/lombardia/notizie/lombardia_rss.xml",
        category="region",
        region="Lombardia",
    ),
    FeedSource(
        name="ANSA China",
        url="https://www.ansa.it/china/notizie/china_nr_rss.xml",
        category="international",
        region="China",
    ),
]


CHINESE_KEYWORDS = [
    "cina",
    "cinese",
    "cinesi",
    "cittadino cinese",
    "cittadina cinese",
    "comunita cinese",
    "comunità cinese",
    "made in china",
    "wholesale cinese",
    "imprenditore cinese",
    "imprenditori cinesi",
    "ditta cinese",
    "azienda cinese",
    "societa cinese",
    "società cinese",
    "gang cinese",
    "mafia cinese",
    "triade",
    "triadi",
    "chinatown",
    "prato cinese",
    "pratesi cinesi",
    "cnr cinese",
    "cinesi a prato",
]


CRIME_AND_ENFORCEMENT_KEYWORDS = [
    "aggressione",
    "arrestato",
    "arrestata",
    "arresti",
    "armi",
    "assalto",
    "blitz",
    "carabinieri",
    "clandestino",
    "clandestini",
    "confisca",
    "criminale",
    "criminalita",
    "criminalità",
    "decreto flussi",
    "detenuto",
    "droga",
    "espulsione",
    "espulso",
    "espulsa",
    "estorsione",
    "evasione fiscale",
    "frode",
    "frode fiscale",
    "furto",
    "gdf",
    "giro illecito",
    "guardia di finanza",
    "immigrazione",
    "immigrati",
    "indagine",
    "indagato",
    "indagata",
    "ispezione",
    "lavoro nero",
    "manodopera",
    "omicidio",
    "operazione",
    "perquisizione",
    "rapina",
    "riciclaggio",
    "sequestro",
    "sfruttamento",
    "sfruttamento del lavoro",
    "smantellata",
    "smantellato",
    "spaccio",
    "tratta",
    "traffico illecito",
    "usura",
    "violenza",
]


VIRAL_ATTENTION_KEYWORDS = [
    "allarme",
    "caos",
    "choc",
    "clamoroso",
    "dramma",
    "emergenza",
    "esclusivo",
    "giallo",
    "maxi",
    "paura",
    "scandalo",
    "shock",
    "svolta",
]
