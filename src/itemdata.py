import json

relic_types = ["Melee", "Warframes", "Secondary", "Sentinels", "Primary", "Archwing"]

with open("raw_item_data.json", "r", encoding="utf-8") as f:
    data = json.loads(f.read())

# start with the forma blueprint
items = {"FORMA BLUEPRINT"}
# the game apends 'Blueprint' after each warframe part -> adjust data
blueprint_types = ["CHASSIS", "SYSTEMS", "NEUROPTICS"]

for item in data:
    if item["category"] in relic_types and "Prime" in item["name"] and "components" in item:
        for component in item["components"]:
            component_type = component["name"].upper()
            # append 'BLUEPRINT' when the part is one of the warframe parts
            if component_type in blueprint_types:
                component_type += " BLUEPRINT"
                
            items.add(item["name"].upper() + " " + component_type)

with open("item_data.json", "w") as f:
    json.dump(list(items), f, indent="  ")