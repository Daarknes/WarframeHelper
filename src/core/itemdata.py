import json
from core import constants

with open(constants.RES_LOC + "raw_item_data.json", "r", encoding="utf-8") as f:
    data = json.loads(f.read())
 
#==========================
# ocr stuff
#==========================
# the game apends 'Blueprint' after each warframe part -> adjust data
warframe_parts = ["CHASSIS", "SYSTEMS", "NEUROPTICS"]

# start with the forma blueprint
ocr_items = {"FORMA BLUEPRINT"}

#=========================
# market stuff
#=========================
special_map = {
    "&": "and",
    "'": "",
    "-": "_"
}

market_data = {"items": {}, "mods": []}


def get_market_name(entry):
    market_name = entry["name"].replace(" ", "_").lower()
    for key, value in special_map.items():
        market_name = market_name.replace(key, value)
    return market_name

def process_item(item):
    if not ("Prime" in item["name"] and "components" in item):
        return

    market_name = get_market_name(item)
    market_component_names = []
    market_data["items"][market_name] = market_component_names

    for component in item["components"]:
        # not a recipe component
        if component["uniqueName"].find(r"/Recipes/") == -1:
            continue
        
        ocr_component_name = component["name"].upper()
        market_component_name = component["name"].replace(" ", "_").lower()
        
        # append 'BLUEPRINT' when the part is one of the warframe parts (ocr)
        if ocr_component_name in warframe_parts:
            ocr_component_name += " BLUEPRINT"
        # replace special characters (market)
        for key, value in special_map.items():
            market_component_name = market_component_name.replace(key, value)
             
        ocr_items.add(item["name"].upper() + " " + ocr_component_name)
        market_component_names.extend([market_component_name] * component["itemCount"])

_special_mods = {
    "ambush_optics": "ambush_optics_(rubico)",
    "brain_storm": "brain_storm_(grakata)",
    "primed_pistol_ammo_mutation": "primed_pistol_mutation",
    "shrapnel_rounds": "shrapnel_rounds_(marelok)",
    "skull_shots": "skull_shots_(viper)",
    "static_alacrity": "static_alacrity_(staticor)",
    "thundermiter": "thundermiter_(miter)",
    "vermillion_storm": "vermilion_storm"
}
def process_mod(mod):
    # ignore rivens
    if "Riven" in mod["name"].split(" "):
        return

    mod_name = get_market_name(mod)
    if mod_name in _special_mods:
        mod_name = _special_mods[mod_name]
    market_data["mods"].append(mod_name)

category_funcs = {
    "Melee": process_item, "Warframes": process_item, "Secondary": process_item, "Sentinels": process_item, "Primary": process_item, "Archwing":process_item,
    "Mods": process_mod
}


for entry in data:
    if entry["tradable"] and entry["category"] in category_funcs:
        category_funcs[entry["category"]](entry)

with open(constants.OCR_NAMES_LOC, "w") as f:
    json.dump(list(ocr_items), f, indent=4)

with open(constants.MARKET_NAMES_LOC, "w") as f:
    json.dump(market_data, f, indent=4)


            
            
            

