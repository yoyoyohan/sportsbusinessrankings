"""Sport catalog. Drive is read-only — file IDs are for GET downloads only."""

from __future__ import annotations

DRIVE_FOLDER_ID = "1jRwUeH8mRB6gH_Gm4Rjc2IdIlYSX_cHO"
DRIVE_FOLDER_URL = f"https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}"

# Never include helpers or backups. Never write these IDs with upload APIs.
SPORTS = [
    {
        "slug": "baseball",
        "name": "Baseball",
        "group": "Spring",
        "file": "Baseball_Spread_OffDef.xlsm",
        "drive_id": "19rNSYMfiqJuVkp_WQ6eMvUkxFc2eTHxo",
        "kind": "offdef",
    },
    {
        "slug": "softball",
        "name": "Softball",
        "group": "Spring",
        "file": "Softball_Spread_OffDef.xlsm",
        "drive_id": "17GyeJ5s2C8pom9lz-NLnk4egrX0ZI5ET",
        "kind": "offdef",
    },
    {
        "slug": "boys-lacrosse",
        "name": "Boys Lacrosse",
        "group": "Spring",
        "file": "BLax_Spread_OffDef.xlsm",
        "drive_id": "1WIW1LjeozAURFmaz3Ra2zY9M4ycuQx9I",
        "kind": "offdef",
    },
    {
        "slug": "girls-lacrosse",
        "name": "Girls Lacrosse",
        "group": "Spring",
        "file": "GLax_Spread_OffDef.xlsm",
        "drive_id": "1PGFZesTx2EYa0R96KM0jOao2zqxUe8rc",
        "kind": "offdef",
    },
    {
        "slug": "boys-tennis",
        "name": "Boys Tennis",
        "group": "Spring",
        "file": "BoysTennis_Spread.xlsm",
        "drive_id": "1dU5XhTtd-LsMOUi6EybMx-YBtJzkiKDX",
        "kind": "lines",
    },
    {
        "slug": "girls-tennis",
        "name": "Girls Tennis",
        "group": "Spring",
        "file": "GirlsTennis_Spread.xlsm",
        "drive_id": "1GN6ymJiR7d9XdyEmGNOEpriwBL0g24U_",
        "kind": "lines",
    },
    {
        "slug": "boys-golf",
        "name": "Boys Golf",
        "group": "Spring",
        "file": "BoysGolf_Spread.xlsm",
        "drive_id": "1AG2zjsmW0cBn6f918pssX_Gxd3nsVnkV",
        "kind": "rating",
    },
    {
        "slug": "boys-volleyball",
        "name": "Boys Volleyball",
        "group": "Spring",
        "file": "BoysVolleyball_Spread.xlsm",
        "drive_id": "13jpQl40OoWND45SWhQ19einaAKJWUlrI",
        "kind": "rating",
    },
    {
        "slug": "flag-football",
        "name": "Flag Football",
        "group": "Spring",
        "file": "FlagFootball_Spread_OffDef.xlsm",
        "drive_id": "1kQKt6xqlVudYiv6V0cJjV3D6a5cwT_o8",
        "kind": "offdef",
    },
    {
        "slug": "football",
        "name": "Football",
        "group": "Fall",
        "file": "Football_Spread_OffDef.xlsm",
        "drive_id": "1S7CPi8bRyLx8ofrScoB3RYmzWqZuaYo1",
        "kind": "offdef",
    },
    {
        "slug": "boys-soccer",
        "name": "Boys Soccer",
        "group": "Fall",
        "file": "BoysSoccer_Spread_OffDef.xlsm",
        "drive_id": "1fjRKNRzvqpXSzhaqWVu6N0k9W-cWdNd1",
        "kind": "offdef",
    },
    {
        "slug": "girls-soccer",
        "name": "Girls Soccer",
        "group": "Fall",
        "file": "GirlsSoccer_Spread_OffDef.xlsm",
        "drive_id": "1GnS66xoCZj4bbp67UsjDueuET21BvSze",
        "kind": "offdef",
    },
    {
        "slug": "field-hockey",
        "name": "Field Hockey",
        "group": "Fall",
        "file": "FieldHockey_Spread_OffDef.xlsm",
        "drive_id": "1bIEy0MGbIzSVyZcbk5e65cb2C7PGiuQH",
        "kind": "offdef",
    },
    {
        "slug": "girls-volleyball",
        "name": "Girls Volleyball",
        "group": "Fall",
        "file": "GirlsVolleyball_Spread.xlsm",
        "drive_id": "166ffIOBZ6YNB1CT1lsIHhOSDyVFLWbsX",
        "kind": "rating",
    },
    {
        "slug": "girls-gymnastics",
        "name": "Girls Gymnastics",
        "group": "Fall",
        "file": "GirlsGymnastics_Spread.xlsm",
        "drive_id": "1lJHutvUJGElh843nZzh9OFw5zuq3RvSW",
        "kind": "rating",
    },
    {
        "slug": "boys-basketball",
        "name": "Boys Basketball",
        "group": "Winter",
        "file": "BoysBasketball_Spread_OffDef.xlsm",
        "drive_id": "1BdSgMkCa4EnkgKR010oB5GkaO8xeiy-V",
        "kind": "offdef",
    },
    {
        "slug": "girls-basketball",
        "name": "Girls Basketball",
        "group": "Winter",
        "file": "GBB_Spread_OffDef.xlsm",
        "drive_id": "15NmhA8cx0OfKSxcJK6x7ncsJVanqmLoI",
        "kind": "offdef",
    },
    {
        "slug": "boys-bowling",
        "name": "Boys Bowling",
        "group": "Winter",
        "file": "BoysBowling_Spread.xlsm",
        "drive_id": "1fCVag2nMcamHrw_tytDWFQN9BnVTYx65",
        "kind": "rating",
    },
    {
        "slug": "girls-bowling",
        "name": "Girls Bowling",
        "group": "Winter",
        "file": "GirlsBowling_Spread.xlsm",
        "drive_id": "1Co8sfgoitAuzt8M_se1NLWwn__3tjnMO",
        "kind": "rating",
    },
    {
        "slug": "boys-fencing",
        "name": "Boys Fencing",
        "group": "Winter",
        "file": "BoysFencing_Spread.xlsm",
        "drive_id": "1Ime1vCb74Kl-vYu0Hcr2f9gAE9t3bMXt",
        "kind": "rating",
    },
    {
        "slug": "girls-fencing",
        "name": "Girls Fencing",
        "group": "Winter",
        "file": "GirlsFencing_Spread.xlsm",
        "drive_id": "1doZzIX89ch-flus87sIxZCYCZXNCRfMl",
        "kind": "rating",
    },
    {
        "slug": "boys-hockey",
        "name": "Boys Ice Hockey",
        "group": "Winter",
        "file": "BoysHockey_Spread_OffDef.xlsm",
        "drive_id": "1VE-pwFQ8zYkNJ2w6RN5SBKqjXQ-bgRb_",
        "kind": "offdef",
    },
    {
        "slug": "girls-hockey",
        "name": "Girls Ice Hockey",
        "group": "Winter",
        "file": "GirlsHockey_Spread_OffDef.xlsm",
        "drive_id": "1LlV6Oc5Zh7IEDiiAcsRemxzrKf_RuixO",
        "kind": "offdef",
    },
    {
        "slug": "boys-swimming",
        "name": "Boys Swimming",
        "group": "Winter",
        "file": "BoysSwimming_Spread.xlsm",
        "drive_id": "1t2jqDYnCQSpr4TclaDS0pKwgBWh7xTeW",
        "kind": "rating",
    },
    {
        "slug": "girls-swimming",
        "name": "Girls Swimming",
        "group": "Winter",
        "file": "GirlsSwimming_Spread.xlsm",
        "drive_id": "12v-IbPhiMLT7N2zOh6dDgvT9agXXNxWb",
        "kind": "rating",
    },
    {
        "slug": "boys-wrestling",
        "name": "Boys Wrestling",
        "group": "Winter",
        "file": "BoysWrestling_Spread_OffDef.xlsm",
        "drive_id": "1zwoKHcksdHqF5_jtJ4QAQtu01Qj0N0Bo",
        "kind": "offdef",
    },
    {
        "slug": "girls-wrestling",
        "name": "Girls Wrestling",
        "group": "Winter",
        "file": "GirlsWrestling_Spread_OffDef.xlsm",
        "drive_id": "1CIWm7wPISRVl2yZtx7ZjdsNwpZ61k9fL",
        "kind": "offdef",
    },
]


# Native engine mode (Calc family). Used by recompute.
# offdef | margin | margin_cap25 | absolute | golf | lines
for _s in SPORTS:
    kind = _s["kind"]
    slug = _s["slug"]
    if kind == "offdef":
        _s["engine"] = "offdef"
        _s["games_delta"] = 0.75
        _s["games_cap"] = 15.0
    elif kind == "lines":
        _s["engine"] = "lines"
        _s["games_delta"] = 0.75
    elif "volleyball" in slug:
        _s["engine"] = "margin_cap25"
        _s["games_delta"] = 0.25
    elif "bowling" in slug or "gymnastics" in slug:
        _s["engine"] = "absolute"
        _s["games_delta"] = 0.25
    elif "golf" in slug:
        _s["engine"] = "golf"
        _s["games_delta"] = 0.75
    else:
        # fencing, swimming
        _s["engine"] = "margin"
        _s["games_delta"] = 0.75

# Football (coach): Games weight starts 2.75, +0.5/game, cap 8.25 (P1 in Calc).
for _s in SPORTS:
    if _s["slug"] == "football":
        _s["games_delta"] = 0.5
        _s["games_cap"] = 8.25


def sport_by_slug(slug: str) -> dict | None:
    for s in SPORTS:
        if s["slug"] == slug:
            return s
    return None
