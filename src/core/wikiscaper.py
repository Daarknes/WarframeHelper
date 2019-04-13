import pickle
import re
import unicodedata

from lupa import LuaRuntime
import lupa
from lxml import html
import requests
from requests.exceptions import Timeout
import time
import os


def _get_dict_from_lua_source(code):
    def recursice_dict(lua_dict):
        d = {}
        is_list = True
        for key, value in lua_dict.items():
            if not isinstance(key, int):
                is_list = False
    
            if lupa.lua_type(value) == "table":
                value = recursice_dict(value)
            d[key] = value
        
        if is_list:
            return list(d.values())
        else:
            return d
    
    lua = LuaRuntime(unpack_returned_tuples=True)
    l_table = lua.execute(code)
    return recursice_dict(l_table)


class Scraper():
    def __init__(self):
        self._cache = {}

    def __enter__(self):
        self._cache = {}
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        del self._cache
    
    def _parse_data(self, url):
        if url in self._cache:
            return self._cache[url]

        while True:
            try:
                response = requests.get(url, timeout=10)
            except Timeout:
                response = None
    
            if response is not None:
                if response.status_code == requests.codes["not_found"]:
                    raise Exception("[Wikiscraper] '{}' not found.".format(url))
                elif response.status_code == requests.codes["ok"]:
                    break
            else:
                print("[Wikiscraper] Couldn't request data from '{}'. Trying again in 5s".format(url))
                time.sleep(5)

        print("[Wikiscraper] Downloaded data from '{}'.".format(url))
        tree = html.fromstring(response.content)
        lua_source = tree.xpath('//pre[@id="theme-solarized-light"]')[0]
        code = unicodedata.normalize("NFKD", lua_source.text_content())
        
        self._cache[url] = _get_dict_from_lua_source(code)
        return self._cache[url]

    def parse_weapons(self):
        """
        output structure:
        {
            "Ack & Brunt": {
                "family": "Ack & Brunt",
                "type": "Melee"
            },
            ...,
            "Ankyros": {
                "family": "Ankyros",
                "type": "Melee"
            },
            "Ankyros Prime": {
                "family": "Ankyros",
                "type": "Melee",
                "components": {
                    "Blade": {"count": 2},
                    ...
                ]
            },
            ...
        }
        """
        data = self._parse_data("http://warframe.fandom.com/wiki/Module:Weapons/data")['Weapons']
    
        # post-processing
        # stupid wiki-errors
        data['Twin Vipers Wraith']['Cost']['Parts'][0]["Name"] = "Barrels"
        data['Twin Vipers Wraith']['Cost']['Parts'][1]['Name'] = "Receivers"
        data['Fluctus']['Cost']['Parts'][1]['Name'] = "Limbs"
        data['Rathbone']['Cost']['Parts'][0]['Name'] = "Head"
        data['Ballistica Prime']['Traits'] = ["Prime"]
        data['Kogake Prime']['Traits'] = ["Prime"]
        data['Kronen Prime']['Traits'] = ["Prime"]
        data['Tiberon Prime']['Traits'] = ["Prime"]
        data['Akbolto Prime']['Traits'] = ["Prime"]
        data['Nami Skyla Prime']['Traits'] = ["Prime"]
        data['Snipetron Vandal']['Traits'].append("Invasion Reward")
        data['Sheev']['Traits'].append("Invasion Reward")
        data['Dera Vandal']['Traits'].append("Invasion Reward")
        data['Agkuza']['Cost']['Parts'].append({"Name": "Guard", "Type": "Item", "Count": 1})
    
        bonus_weapons = {"Gorgon Wraith", "Wolf Sledge", "Braton Vandal", "Lato Vandal", "Furax Wraith"}
        
        weapons = {}
        for info in data.values():
            relevant_info = {
                "family": info['Family'] if 'Family' in info else info['Name'],
                "type": info['Type'],
            }
            
            is_arch = info['Type'] == "Arch-Gun" or info['Type'] == "Arch-Melee"
            is_trait = "Traits" in info and ("Prime" in info['Traits'] or "Invasion Reward" in info['Traits'])
    
            if "Cost" in info and (is_arch or is_trait or info['Name'] in bonus_weapons):
                parts = {part['Name']: {"count": part['Count']} for part in info['Cost']['Parts'] if part['Type'] == "PrimePart" or part['Type'] == "Item"}
    
                if parts:
                    if "BPCost" not in info['Cost']:
                        parts['Blueprint'] = {"count": 1}
                    relevant_info['components'] = parts
    
            weapons[info['Name']] = relevant_info
        
        # zaws and kitguns (modular)
        data = self._parse_data("http://warframe.fandom.com/wiki/Module:Modular/data")
        
        for name in data['Kitgun']['Chamber']:
            weapons[name] = {'family': name, "type": "Kitgun"}
        
        for name in data['Zaw']['Strike']:
            weapons[name] = {'family': name, "type": "Zaw"}
        
        return weapons
    
    
    def parse_warframes(self):
        """
        output structure:
        {
            "Ash": {"family": "Ash"},
            "Ash Prime": {"family": "Ash"},
            ...
        }
        """
        data = self._parse_data("http://warframe.fandom.com/wiki/Module:Warframes/data")
    
        # post-processing
        warframes = {}
        # for now we only need the names of each warframe (-group)
        for name in data['Warframes'].keys():
            family = re.search("(.*?)(?:Prime|Umbra)", name)
            family = ((family and family.group(1).strip()) or name)
            
            relevant_data = {"family": family}
            warframes[name] = relevant_data
                
        return warframes


    def parse_archwings(self):
        """
        output structure:
        {
            "Amesha": {"family": "Amesha"},
            ...
        }
        """
        archwings = {
            "Amesha": {"family": "Amesha"},
            "Elytron": {"family": "Elytron"},
            "Itzal": {"family": "Itzal"},
            "Odonata": {"family": "Odonata"},
            "Odonata Prime": {"family": "Odonata"},
        }
        
        return archwings
    
    
    def parse_mods(self):
        """
        output structure:
        [
            "Push & Pull",
            ...
        ]
        """
        data = self._parse_data("http://warframe.fandom.com/wiki/Module:Mods/data")
    
        # post-processing
        mods = [mod['Name'] for mod in data['Mods'].values()]
        return mods
    
    
    def parse_companions(self):
        """
        output structure:
        {
            "Carrier": {"family": "Carrier", "type": "Sentinel"},
            "Carrier Prime": {"family": "Carrier", "type": "Sentinel"},
            ...
        }
        """
        # TODO: there is no wiki data for companions yet
        companions = {
            "Carrier": {"family": "Carrier", "type": "Sentinel"},
            "Carrier Prime": {"family": "Carrier", "type": "Sentinel"},
            "Dethcube": {"family": "Dethcube", "type": "Sentinel"},
            "Diriga": {"family": "Diriga", "type": "Sentinel"},
            "Djinn": {"family": "Djinn", "type": "Sentinel"},
            "Helios": {"family": "Helios", "type": "Sentinel"},
            "Helios Prime": {"family": "Helios", "type": "Sentinel"},
            "Oxylus": {"family": "Oxylus", "type": "Sentinel"},
            "Shade": {"family": "Shade", "type": "Sentinel"},
            "Prisma Shade": {"family": "Shade", "type": "Sentinel"},
            "Taxon": {"family": "Taxon", "type": "Sentinel"},
            "Wyrm": {"family": "Wyrm", "type": "Sentinel"},
            "Wyrm Prime": {"family": "Wyrm", "type": "Sentinel"},
            
            "Chesa Kubrow": {"family": "Chesa Kubrow", "type": "Kubrow"},
            "Helminth Charger": {"family": "Helminth Charger", "type": "Kubrow"},
            "Huras Kubrow": {"family": "Huras Kubrow", "type": "Kubrow"},
            "Raksa Kubrow": {"family": "Raksa Kubrow", "type": "Kubrow"},
            "Sahasa Kubrow": {"family": "Sahasa Kubrow", "type": "Kubrow"},
            "Sunika Kubrow": {"family": "Sunika Kubrow", "type": "Kubrow"},
    
            "Adarza Kavat": {"family": "Adarza Kavat", "type": "Kavat"},
            "Smeeta Kavat": {"family": "Smeeta Kubrow", "type": "Kavat"},
            "Venari": {"family": "Venari", "type": "Kavat"}
        }
    
        # moas
        data = self._parse_data("http://warframe.fandom.com/wiki/Module:Modular/data")
        for moa_name in data['MOA']['Model']:
            companions[moa_name] = {"family": moa_name, "type": "moa"}
        
        return companions


    def parse_relics(self):
        """
        output structure:
        {
            "Lith A1": {
                "drops": [
                    {"item": "Braton", "part": "Barrel", "rarity": "Common"},
                    ...
                ]
            },
            ...
        }
        """
        data = self._parse_data("http://warframe.fandom.com/wiki/Module:Void/data")
    
        # post-processing
        relics = {}
        rarity_by_reward = {}
        
        rarity_to_int = {"Common": 0b1, "Uncommon": 0b10, "Rare": 0b100}
    
        for info in data['Relics']:
            name = info['Tier'] + " " + info['Name']    
    
            drops = []
            for raw_drop in info['Drops']:
                part = raw_drop['Part'].title()
                if part != "Blueprint":
                    part = part.replace("Blueprint", "").strip()
    
                drop = {"item": raw_drop['Item'].title(), "part": part, "rarity": raw_drop['Rarity'].title()}
                drops.append(drop)
                
                full_name = drop['item'] + " " + drop['part']
                if full_name in rarity_by_reward:
                    rarity_by_reward[full_name] |= rarity_to_int[drop['rarity']]
                else:
                    rarity_by_reward[full_name] = rarity_to_int[drop['rarity']]
            
            relics[name] = {"drops": drops}
        
        return relics
    
    
    def parse_arcanes(self):
        """
        output structure:
        [
            "Arcane Acceleration",
            ...
        ]
        """
        data = self._parse_data("http://warframe.fandom.com/wiki/Module:Arcane/data")
    
        # post-processing
        arcanes = [arcane['Name'] for arcane in data['Arcanes'].values()]
        return arcanes

# TODO: Companion armor, 


def get_ducat_values(relics):
    """
    output structure:
    {
        "Ankyros": {
            "Blade": 65,
            ...
        },
        ...,
        "Ash": {
            "Neuroptics": 45,
            ...
        },
        ...
    }
    """
    rarity_by_reward = {}
    rarity_to_int = {"Common": 0b1, "Uncommon": 0b10, "Rare": 0b100}

    for relic in relics.values():
        for drop in relic['drops']:
            # ignore Forma
            if drop['item'] == "Forma":
                continue
            
            if drop['item'] not in rarity_by_reward:
                rarity_by_reward[drop['item']] = {}

            if drop['part'] not in rarity_by_reward[drop['item']]:
                rarity_by_reward[drop['item']][drop['part']] = 0

            rarity_by_reward[drop['item']][drop['part']] |= rarity_to_int[drop['rarity']]
    
    def ducat_value(name, rarities):
        # exceptions
        if name == "Soma Blueprint" or name == "Braton Stock":
            return 15
        elif name == "Ankyros Blade" or name == "Rhino Chassis":
            return 65

        num_rarities = (rarities >> 2) + ((rarities >> 1) & 1) + (rarities & 1)

        # if this item only occurs as a single rarity, the ducat is the ducat value of that rarity
        if num_rarities == 1:
            if rarities & 0b1:
                return 15
            elif rarities & 0b10:
                return 45
            else:
                return 100
        # if it occurs in two rarities, it is either ("Common", "Uncommon") -> 25 or ("Uncommon", "Rare") -> 65
        elif num_rarities == 2:
            return 65 if rarities & 0b100 else 25
        else:
            return 25
    
    for item_name, parts in rarity_by_reward.items():
        for part_name, rarities in parts.items():
            rarity_by_reward[item_name][part_name] = ducat_value(item_name + " " + part_name, rarities)

    return rarity_by_reward


# debugging
_o_parse_data = Scraper._parse_data
_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "tmp")) + os.path.sep + "{}.pick"
def _open_data(_, url):
    with open(_path.format(url[40:-5].lower()), "rb") as f:
        return pickle.load(f)

def _save_data(_, url):
    data = _o_parse_data(url)
    with open(_path.format(url[40:-5].lower()), "wb") as f:
        pickle.dump(data, f)
    return data

#Scraper._parse_data = _open_data
