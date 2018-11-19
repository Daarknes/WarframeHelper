import json
import os

res_path = os.path.join("..", "..", "res", "")

item_types = ["Melee", "Warframes", "Secondary", "Sentinels", "Primary", "Archwing"]
exclude_type = ["MiscItems"]

with open(res_path + "raw_item_data.json", "r", encoding="utf-8") as f:
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
    "&": "and"
}

market_items = {}
 
for item in data:
    if item["category"] in item_types and "Prime" in item["name"] and "components" in item:
        market_name = item["name"].replace(" ", "_").lower()
        for key, value in special_map.items():
            market_name = market_name.replace(key, value)
        
        market_component_names = []
        market_items[market_name] = market_component_names

        for component in item["components"]:
            # not a recipe component
            if component["uniqueName"].find(r"/Recipes/") == -1:
                continue
#             component_type = component["uniqueName"].split("/")[-2]
#             if component_type in exclude_type:
#                 continue
            
            ocr_component_name = component["name"].upper()
            market_component_name = component["name"].replace(" ", "_").lower()
            
            # append 'BLUEPRINT' when the part is one of the warframe parts (ocr)
            if ocr_component_name in warframe_parts:
                ocr_component_name += " BLUEPRINT"
            # replace special characters (market)
            for key, value in special_map.items():
                market_component_name = market_component_name.replace(key, value)
                 
            ocr_items.add(item["name"].upper() + " " + ocr_component_name)
            market_component_names.append(market_component_name)
 
with open(res_path + "ocr_item_data.json", "w") as f:
    json.dump(list(ocr_items), f, indent="  ")

with open(res_path + "market_item_data.json", "w") as f:
    json.dump(market_items, f, indent="  ")


            
            
            

