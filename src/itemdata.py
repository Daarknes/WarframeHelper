import json

item_types = ["Melee", "Warframes", "Secondary", "Sentinels", "Primary", "Archwing"]
# the game apends 'Blueprint' after each warframe part -> adjust data
warframe_parts = ["CHASSIS", "SYSTEMS", "NEUROPTICS"]
exclude_type = ["MiscItems"]

with open("raw_item_data.json", "r", encoding="utf-8") as f:
    data = json.loads(f.read())
 
# start with the forma blueprint
items = {"FORMA BLUEPRINT"}
 
for item in data:
    if item["category"] in item_types and "Prime" in item["name"] and "components" in item:
        for component in item["components"]:
            component_type = component["uniqueName"].split("/")[-2]
            if component_type in exclude_type:
                continue
            
            component_name = component["name"].upper()
            # append 'BLUEPRINT' when the part is one of the warframe parts
            if component_name in warframe_parts:
                component_name += " BLUEPRINT"
                 
            items.add(item["name"].upper() + " " + component_name)
 
with open("item_data.json", "w") as f:
    json.dump(list(items), f, indent="  ")