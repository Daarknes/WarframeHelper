#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
from core import constants

def update():
    #==========================
    # ocr stuff
    #==========================
    # start with the forma blueprint
    ocr_items = {"FORMA BLUEPRINT"}
    ocr_ducats = {}
    
    #=========================
    # market stuff
    #=========================
    special_map = {
        "&": "and",
        "'": "",
        "-": "_"
    }
    
    market_data = {"items": {}, "mods": [], "relics": {}}
    
    
    def get_market_name(entry):
        market_name = entry["name"].replace(" ", "_").lower()
        for key, value in special_map.items():
            market_name = market_name.replace(key, value)
        return market_name
    
    
    _relic_types = ("Intact", "Radiant")
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
            if item["category"] == "Warframes" and ocr_component_name != "BLUEPRINT":
                ocr_component_name += " BLUEPRINT"
            # replace special characters (market)
            for key, value in special_map.items():
                market_component_name = market_component_name.replace(key, value)
            
            ocr_component_name = item["name"].upper() + " " + ocr_component_name
            
            ocr_items.add(ocr_component_name)
            if "ducats" in component:
                ocr_ducats[ocr_component_name] = component["ducats"]
            market_component_names.extend([market_component_name] * component["itemCount"])
            
            # relics
            if "drops" in component:
                for drop in component["drops"]:
                    if drop["type"] != "Relics" or drop["location"].split(" ")[-1] not in _relic_types:
                        continue
                    
                    i = drop["location"].rfind(" ")
                    relic_name = drop["location"][:i].lower().replace(" ", "_")
                    relic_type = drop["location"][i+1:].lower()
                    
                    # this relic has no entry yet
                    if relic_name not in market_data["relics"]:
                        market_data["relics"][relic_name] = {}

                    # the relic type (intact, radiant) is not yet listed
                    if relic_type not in market_data["relics"][relic_name]:
                        market_data["relics"][relic_name][relic_type] = []

                    market_data["relics"][relic_name][relic_type].append((market_name + "_" + market_component_name, drop["chance"]))
        
    
    _special_mods = {
        "ambush_optics": "ambush_optics_(rubico)",
        "brain_storm": "brain_storm_(grakata)",
        "mesas_waltz": "mesa’s_waltz",
        "primed_pistol_ammo_mutation": "primed_pistol_mutation",
        "shrapnel_rounds": "shrapnel_rounds_(marelok)",
        "skull_shots": "skull_shots_(viper)",
        "static_alacrity": "static_alacrity_(staticor)",
        "thundermiter": "thundermiter_(miter)",
        "vermillion_storm": "vermilion_storm"
    }
    def process_mod(mod):
        # ignore rivens
        if not mod["tradable"] or "Riven" in mod["name"].split(" "):
            return
    
        mod_name = get_market_name(mod)
        if mod_name in _special_mods:
            mod_name = _special_mods[mod_name]
        market_data["mods"].append(mod_name)
    
    category_funcs = {
        "Melee": process_item, "Warframes": process_item, "Secondary": process_item, "Sentinels": process_item, "Primary": process_item, "Archwing":process_item,
        "Mods": process_mod
    }
    special_items = ["Kavasa Prime Kubrow Collar"]


    # load raw data and process it
    with open(constants.RES_LOC + "raw_item_data.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())

    for entry in data:
        if entry["category"] in category_funcs:
            category_funcs[entry["category"]](entry)
        elif entry["name"] in special_items:
            process_item(entry)
    
    # save data to corresponding files
    with open(constants.OCR_NAMES_LOC, "w") as f:
        json.dump(list(ocr_items), f, indent=4)
    with open(constants.OCR_DUCATES_LOC, "w") as f:
        json.dump(ocr_ducats, f, indent=4)
    
    with open(constants.MARKET_NAMES_LOC, "w") as f:
        json.dump(market_data, f, indent=4)


if __name__ == "__main__":
    update()

