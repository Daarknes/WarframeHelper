from core import wikiscaper, constants
import os
import json


_FILE_LOC = constants.res_loc() + "item_data.json"

_item_data = None
_updated = False


class Category:
    WEAPONS = "weapons"
    WARFRAMES = "warframes"
    ARCHWINGS = "archwings"
    MODS = "mods"
    COMPANIONS = "companions"
    RELICS = "relics"


def _create_item_data():
    with wikiscaper.Scraper() as scraper:
        item_data = {
            Category.WEAPONS: scraper.parse_weapons(),
            Category.WARFRAMES: scraper.parse_warframes(),
            Category.ARCHWINGS: scraper.parse_archwings(),
            Category.MODS: scraper.parse_mods(),
            Category.COMPANIONS: scraper.parse_companions(),
            Category.RELICS: scraper.parse_relics()
        }
    
    return item_data


def update():
    "updates (recreates) the item data and saves it."
    print("[ItemData] Updating Item-data.")

    global _item_data, _updated
    _item_data = _create_item_data()

    with open(_FILE_LOC, "w") as f:
        json.dump(_item_data, f, indent=2)
    
    _updated = True


def item_data():
    """returns the loaded item data. Output structure:
    {
        Category.WEAPONS: {...},
        Category.WARFRAMES: {...},
        Category.ARCHWINGS: {...},
        Category.MODS: [...],
        Category.COMPANIONS: {...},
        Category.RELICS: {}
    }
    """
    return _item_data


def updated():
    "whether the item_data was updated on load (i.e. when the file didn't exist) or by a call to 'update()' earlier."
    return _updated


if os.path.exists(_FILE_LOC):
    with open(_FILE_LOC, "r") as f:
        _item_data = json.load(f)
else:
    update()
