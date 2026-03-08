#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import json
import string
import urllib
import time

CSERVICE = webdriver.ChromeService(executable_path='/usr/bin/chromedriver')
OPTIONS = webdriver.ChromeOptions()
OPTIONS.add_argument('--incognito')
BASE_URL = "https://clashofclans.fandom.com/wiki/"
TAG = "https://api.clashofclans.com/v1/players/%23GPQUUY989"
DRIVER = None
DB = {}



####################
## IN GAME PARAMS ##

LVL = 17

BONUS = 20      # 15(%)


#############
## CLASSES ##

class PageInfo:
    def __init__(self, name):
        self.name = name
        self.file = 'data/'+name+'.json'
        self.url = BASE_URL + name
        try:
            with open(self.file, 'r') as fp:
                self.info = json.load(fp)
            return
        except FileNotFoundError:
            pass
        self.info = extract_from_page(name)
        with open(self.file, 'w') as fp:
            json_dumps_str = json.dumps(self.info)\
                            .replace("{", "{\n    ")\
                            .replace("}", "\n}")\
                            .replace("], ", "],\n    ")\
                            .replace("N/A", "0")\
                            .replace("5*", "5")\
                            .replace("7/0*", "0")\
                            .replace("9/2*", "2")\
                            .replace("7/3*", "3")\
                            .replace("8/4*", "4")
            print(json_dumps_str, file=fp)
            print(json_dumps_str)
            self.info = json.loads(json_dumps_str)
    def __repr__(self):
        return f"{self.name}\n"+json.dumps(self.info).replace("{", "{\n    ").replace("}", "\n}").replace("], ", "],\n    ")

class BuildingInfo(PageInfo):
    def number_max(self, hdv):
        try:
            return int(self.info["Number available"][hdv-1])
        except:
            print(f"Error: cannot find number max for {self.name} at HDV {hdv}\n{self.info}\n{self.url}")
            raise
    def level_max(self, hdv):
        if self.name == "Town_Hall":
            return hdv
        try:
            return sum([int(toto) <= hdv for toto in self.info["Town_Hall_Level_Required"]])
        except:
            print(f"Error: cannot find max level for {self.name} at HDV {hdv}\n{self.info}\n{self.url}")
            raise
    def get_upgrade_time(self, level):
        try:
            return self.info["Build_Time"][level-1]
        except KeyError:
            print(f"Error: cannot find build time for {self.name} at level {level}\n{self.info}\n{self.url}")
            raise

class TroopInfo(PageInfo):
    def level_max(self, hdv):
        try:
            labo = DB["Laboratory"]
            return sum([int(toto) <= labo.level_max(hdv) for toto in self.info["Laboratory_Level_Required"]])
        except:
            print(f"Error: cannot find max level for {self.name} at HDV {hdv}\n{self.info}\n{self.url}")
            raise
    def number_max(self, _):
        return 1
    def get_upgrade_time(self, level):
        try:
            return self.info["Research_Time"][level-1]
        except KeyError:
            print(f"Error: cannot find upgrade time for {self.name} at level {level}\n{self.info}\n{self.url}")
            raise

class HeroInfo(PageInfo):
    def level_max(self, hdv):
        try:
            hero_hall = DB["Hero_Hall"]
            return sum([int(toto) <= hero_hall.level_max(hdv) for toto in self.info["Hero_Hall_Level_Required"]])
        except:
            print(f"Error: cannot find max level for {self.name} at HDV {hdv}\n{self.info}\n{self.url}")
            raise
    def number_max(self, _):
        return 1
    def get_upgrade_time(self, level):
        try:
            return self.info["Upgrade_Time"][level-1]
        except KeyError:
            print(f"Error: cannot find upgrade time for {self.name} at level {level}\n{self.info}\n{self.url}")
            raise

class IdMap:
    def __init__(self):
        with open('id_map.json', 'r') as fp:
            buffer = json.load(fp)
            self.id_to_name = {}
            self.name_to_id = {}
            for item in buffer:
                self.id_to_name[item["dataId"]] = item["name"].replace(" ", "_")
                self.name_to_id[item["name"].replace(" ", "_")] = item["dataId"]
    def __getitem__(self, key):
        try:
            return self.id_to_name[key]
        except KeyError:
            return self.name_to_id[key]

class Building:
    def __init__(self, name, level=0):
        self.name = name
        self.level = level
    def __repr__(self):
        return f"Building {self.name} ({self.level})"
    def set_level(self, level):
        self.level = level
    def level_max(self, hdv):
        ref = DB[self.name]
        return ref.level_max(hdv)

class Troop:
    def __init__(self, name, level=1):
        self.name = name
        self.level = level
    def __repr__(self):
        return f"Troop {self.name} ({self.level})"
    def set_level(self, level):
        self.level = level
    def level_max(self, hdv):
        ref = DB[self.name]
        return ref.level_max(hdv)

class Hero:
    def __init__(self, name, level=1):
        self.name = name
        self.level = level
    def __repr__(self):
        return f"Hero {self.name} ({self.level})"
    def set_level(self, level):
        self.level = level
    def level_max(self, hdv):
        ref = HeroInfo(self.name)
        return ref.level_max(hdv)

class Village:
    def __init__(self, hdv_level=0):
        self.hdv_level = hdv_level
        self.buildings = {}
        self.heroes = []
        self.troops = []
    def load_from_exported_json(self):
        with open('exported_village.json', 'r') as fp:
            data = json.load(fp)
        id_map = IdMap()
        for building in data["buildings"] + data["traps"]:
            if building["data"] not in id_map.id_to_name:
                print(f"Warning: cannot find name for id {building['data']}")
                continue
            if id_map[building["data"]] not in self.buildings:
                self.buildings[id_map[building["data"]]] = []
            try:
                building_number = building["cnt"]
            except KeyError:
                building_number = 1
            for _ in range(building_number):
                self.buildings[id_map[building["data"]]].append(Building(id_map[building["data"]], building["lvl"]))
        del self.buildings["Wall"]
        self.hdv_level = self.buildings["Town_Hall"][0].level
        for hero in data["heroes"]:
            self.heroes.append(Hero(id_map[hero["data"]], hero["lvl"]))
        for troop in data["units"] + data["spells"] + data["siege_machines"]:
            self.troops.append(Troop(id_map[troop["data"]], troop["lvl"]))
    def check_nb_buildings(self):
        for building in self.buildings:
            if len(self.buildings[building]) > DB[building].number_max(self.hdv_level):
                print(f"Warning: too many {building} (have {len(self.buildings[building])}, max {DB[building].number_max(self.hdv_level)})")
            elif len(self.buildings[building]) < DB[building].number_max(self.hdv_level):
                print(f"Warning: too few {building} (have {len(self.buildings[building])}, max {DB[building].number_max(self.hdv_level)})")
    def to_max(self, hdv):
        self.check_nb_buildings()
        upgrader = Upgrader()
        my_string = f"Village (HDV {self.hdv_level})\n\nBUILDINGS:\n"
        for building, instances in self.buildings.items():
            if building == "Archer_Tower":
                continue
            level_max = DB[building].level_max(hdv)
            for instance in instances:
                upgrader.add(instance, level_max)
        for hero in self.heroes:
            upgrader.add(hero, hero.level_max(hdv))
        for troop in self.troops:
            upgrader.add(troop, troop.level_max(hdv))
        print(upgrader)
    def __repr__(self):
        my_string = f"Village (HDV {self.hdv_level})\n\nBUILDINGS:\n"
        for building in self.buildings:
            my_string += f"{building} : {[instance.level for instance in self.buildings[building]]} (/{self.buildings[building][0].level_max(self.hdv_level)})\n"
        my_string += f"\nHEROES:\n"
        for hero in self.heroes:
            my_string += f"{hero} (/{hero.level_max(self.hdv_level)})\n"
        my_string += f"\nTROOPS:\n"
        for troop in self.troops:
            my_string += f"{troop} (/{troop.level_max(self.hdv_level)})\n"
        return my_string
    def __iter__(self):
        for building_list in self.buildings.values():
            for building in building_list:
                yield building
        for hero in self.heroes:
            yield hero
        for troop in self.troops:
            yield troop

class Upgrade:
    def __init__(self, building, level_max):
        self.name = building.name
        self.list_upgrades = []
        self.time_total = 0
        self.offset = 0
        for i in range(level_max, building.level, -1):
            try:
                upgrade_time = int((1.-0.01*BONUS)*in_seconds(DB[building.name].get_upgrade_time(i)))
            except KeyError:
                print(f"Error: cannot find upgrade time for {building.name} at level {i}\n{DB[building.name].info}\n{DB[building.name].url}")
                raise
            self.list_upgrades.append((i, in_date(upgrade_time)))
            self.time_total += upgrade_time
    def set_offset(self, offset):
        self.offset = offset
    def __lt__(self, other):
        return self.time_total < other.time_total
    def __repr__(self):
        string = f"[{self.name.rjust(21)}|"
        for upgrade in self.list_upgrades:
            string += f" {str(upgrade[0]).rjust(3)}: ({upgrade[1].ljust(9)}) |"
        for _ in range(self.offset):
            string += " "*(19)
        string += f" Total: {in_date(self.time_total).rjust(12)}]"
        return string

class Upgrader:
    def __init__(self):
        self.max_buildings = 0
        self.max_heroes = 0
        self.max_troops = 0
        self.buildings = []
        self.heroes = []
        self.troops = []
    def add(self, building, level_max):
        if isinstance(building, Building):
            self.buildings.append(Upgrade(building, level_max))
            self.max_buildings = max(self.max_buildings, level_max - building.level)
        elif isinstance(building, Hero):
            self.heroes.append(Upgrade(building, level_max))
            self.max_heroes = max(self.max_heroes, level_max - building.level)
        elif isinstance(building, Troop):
            self.troops.append(Upgrade(building, level_max))
            self.max_troops = max(self.max_troops, level_max - building.level)
        else:
            raise ValueError(f"Cannot add {building} to upgrader")
    def refresh(self):
        self.buildings.sort(reverse=True)
        self.heroes.sort(reverse=True)
        self.troops.sort(reverse=True)
        for building in self.buildings:
            building.set_offset(self.max_buildings - len(building.list_upgrades))
        for hero in self.heroes:
            hero.set_offset(self.max_heroes - len(hero.list_upgrades))
        for troop in self.troops:
            troop.set_offset(self.max_troops - len(troop.list_upgrades))
    def __repr__(self):
        self.refresh()
        my_string = f"Upgrader\n\nBUILDINGS:\n"
        for building in self.buildings:
            my_string += f"{building}\n"
        total_buildings = sum(building.time_total for building in self.buildings)
        my_string += f"\nHEROES:\n"
        for hero in self.heroes:
            my_string += f"{hero}\n"
        total_heroes = sum(hero.time_total for hero in self.heroes)
        my_string += f"\nTROOPS:\n"
        for troop in self.troops:
            my_string += f"{troop}\n"
        total_troops = sum(troop.time_total for troop in self.troops)
        my_string += f"\nTOTAL BUILDINGS: {in_date(total_buildings).rjust(12)}"
        my_string += f"\nTOTAL HEROES: {in_date(total_heroes).rjust(12)}"
        my_string += f"\nTOTAL TROOPS: {in_date(total_troops).rjust(12)}"
        return my_string

###############
## FUNCTIONS ##

def init_driver():
    global DRIVER, CSERVICE, OPTIONS
    try:
        DRIVER.title
    except AttributeError:
        DRIVER = webdriver.Chrome(service=CSERVICE, options=OPTIONS)
    return DRIVER

def extract_from_page(page):
    url = BASE_URL + page
    print(f'Downloading content for {page} : {url}')
    DRIVER = init_driver()
    DRIVER.get(url)
    if DRIVER.title == 'Privacy error':
        DRIVER.find_element(By.ID, "details-button").click()
        DRIVER.find_element(By.ID, "proceed-link").click()
        time.sleep(1)
    if DRIVER.title == "Just a moment...":
        exit("Error: Cloudflare protection is on, please disable it and try again.")
    if page in TROOPS or page in HEROES:
        if page in ["Bat_Spell", "Skeleton_Spell"]:
            text = DRIVER.find_elements(By.CLASS_NAME, "wikitable")[2].text.splitlines()
        else:
            text = DRIVER.find_elements(By.CLASS_NAME, "wikitable")[1].text.splitlines()
        index = 2
    else:
        print(DRIVER.title)
        text = DRIVER.find_element(By.CLASS_NAME, "wikitable").text.splitlines()
        index = 3
    print(f"text =\n{text}")
    columns = extract_columns(page, text)
    print(f"columns =\n{columns}")
    return extract_content(page, text, columns, index)

def extract_columns(page, text):
    columns = [i.replace(" ", "_") for i in text if not any(j in i for j in string.digits) and i != '']
    match page:
        case "Witch":
            columns[3] = "Skeletons_per_Summon"
            columns.insert(4, "Maximum_Skeletons_Summoned")
        case "Wall_Breaker":
            columns[4] = "Damage_when_destroyed_vs._Walls"
            columns.insert(4, "Hitpoints")
        case "Headhunter":
            columns[5] = "Speed_Decrease"
            columns.insert(5, "Attack_Rate_Decrease")
            columns.insert(6, "Hitpoints")
        case "Stone_Slammer":
            columns[2] = "Damage_per_Attack"
            columns.insert(3, "Damage_when_Destroyed")
            columns.insert(3, "Poison")
        case "Troop_Launcher":
            columns = ['Level', 'Hitpoints', 'Lifetime', 'Barrel_Count', 'Barbarian_Level', 'Archer_Level', 'Giant_Level',\
                       'Wall_Breaker_Level', 'Troop_Level', 'Research_Cost', 'Research_Time', 'Laboratory_Level_Required']
        case "Siege_Barracks":
            columns = ['Level', 'Hitpoints', 'P.E.K.K.As', 'Wizards', 'Research_Cost', 'Research_Time', 'Laboratory_Level_Required']
        case "Clone_Spell":
            columns = ["Level", "Cloned_Capacity", "Research_Cost", "Research_Time", "Laboratory_Level_Required"]
        case "Freeze_Spell":
            columns = ["Level", "Freeze_Time", "Research_Cost", "Research_Time", "Laboratory_Level_Required"]
        case "Blacksmith":
            columns = ['Level', 'Equipment_Unlocked', 'Hitpoints', 'Ore_Capacity_Shiny', 'Ore_Capacity_Glowy', 'Ore_Capacity_Starry',\
                       'Maximum_Equipment_Level_Common', 'Maximum_Equipment_Level_Epic', 'Build_Cost', 'Build_Time', 'Experience_Gained', 'Town_Hall_Level_Required']
        case "Spell_Factory" | "Dark_Spell_Factory":
            columns[-2] += "_"+columns[-1]
            if page == "Dark_Spell_Factory":
                columns.remove(columns[1]) # toFix: why no hitpoints ?
            columns.remove(columns[-1])
        case "Army_Camp":
            columns = ['Level', 'Troop_Capacity', 'Hitpoints', 'Build_Cost', 'Build_Time', 'Experience_Gained', 'Town_Hall_Level_Required']
        case "Barracks" | "Dark_Barracks":
            columns = ['Level', 'Unlocked_Unit', 'Hitpoints', 'Build_Cost', 'Build_Time', 'Experience_Gained', 'Town_Hall_Level_Required']
        case "Hero_Hall":
            columns = ['Level', 'Unlocked_Hero', 'Hero_Slots', 'Hitpoints', 'Build_Cost', 'Build_Time', 'Experience_Gained', 'Town_Hall_Level_Required']
        case "Pet_House":
            columns = ['Level', 'Unlocked_Pet', 'Hitpoints', 'Build_Cost', 'Build_Time', 'Experience_Gained', 'Town_Hall_Level_Required']
        case "Workshop":
            columns = ['Level', 'Unlocked_Siege_Machine', 'Siege_Machine_Capacity', 'Hitpoints', 'Build_Cost', 'Build_Time', 'Experience_Gained', 'Town_Hall_Level_Required']
        case "Grand_Warden":
            columns = ['Level', 'Damage_per_Second', 'Damage_per_Hit', 'Hitpoints', 'Health_Recovery', 'Upgrade_Cost', 'Upgrade_Time', 'Hero_Hall_Level_Required']
        case "Ice_Golem":
            columns = ["Level", "Damage_per_Second", "Damage_per_Attack", "Freeze_Time_After_Death_ATK", "Freeze_Time_After_Death_DEF",\
                       "Hitpoints", "Research_Cost", "Research_Time", "Laboratory_Level_Required"]
        case "Lava_Hound":
            columns = ["Level", "Damage_per_Second", "Damage_per_Hit", "Damage_Upon_Death", "Lava_Pups_Spawned_ATK",\
                       "Lava_Pups_Spawned_DEF", "Hitpoints", "Research_Cost", "Research_Time", "Laboratory_Level_Required"]
        case "Electro_Dragon":
            columns.remove("(Primary_Target)")
        case "Meteor_Golem":
            columns[columns.index("Upgrade_Time")] = "Research_Time"
        case "Elixir_Collector" | "Gold_Mine" | "Dark_Elixir_Drill":
            columns = ["Level", "Capacity", "Production_Rate", "Hitpoints", "Boost_Cost", "Time_to_Fill", "Build_Cost", "Build_Time", "Experience_Gained", "Catch-Up_Point*", "Town_Hall_Level_Required"]
    return columns

def fuse_date_in_list(list, pos):
    string1 = list[pos]
    string2 = list[pos+1]
    if string1[-1] not in ['d', 'h', 'm', 's'] or string2[-1] not in ['d', 'h', 'm', 's']:
        return list, False
    for char in string1:
        if char not in string.digits and char not in ['d', 'h', 'm', 's']:
            return list, False
    for char in string2:
        if char not in string.digits and char not in ['d', 'h', 'm', 's']:
            return list, False
    list[pos] += list[pos+1]
    del list[pos+1]
    return list, True

def extract_content(page, text, columns, index):
    global DRIVER
    content_tmp = [i.split() for i in text if any(j in i for j in string.digits)]
    match page:
        case "Elixir_Collector" | "Gold_Mine" | "Dark_Elixir_Drill":
            for i in content_tmp:
                cursor = 0
                while cursor < len(i)-1:
                    i, fused = fuse_date_in_list(i, cursor)
                    if not fused:
                        cursor += 1
        case "Stone_Slammer":
            content_tmp.remove(content_tmp[0])
        case "Air_Sweeper" | "Giant_Bomb" | "Earthquake_Spell":
            _ = [toto.remove("tiles") for toto in content_tmp]
        case "Tornado_Trap" | "Haste_Spell" | "Jump_Spell" | "Freeze_Spell":
            _ = [toto.remove("seconds") for toto in content_tmp]
            if page == "Haste_Spell":
                _ = [toto.remove("tiles") for toto in content_tmp]
        case "Spell_Tower":
            _ = [toto.remove("Spell") for toto in content_tmp]
        case "Inferno_Tower":
            content_tmp.remove(content_tmp[0])
            content_tmp = [[content_tmp_i[0]] + ['/'.join([str(toto) for toto in content_tmp_i[1:4]])] + ['/'.join([str(toto) for toto in content_tmp_i[4:7]])] + content_tmp_i[7:] for content_tmp_i in content_tmp]
            #_ = [toto.remove("x6") for toto in content_tmp]
        case "Blacksmith":
            content_tmp = content_tmp[:2]+[content_tmp[2]+content_tmp[3]]+[content_tmp[4]]+[content_tmp[5]+content_tmp[6]]+content_tmp[7:]
            content_tmp = [[a[0]] + ['_'.join([b for b in a if not any(c in b for c in string.digits)])] + [c for c in a[2:] if any(d in c for d in string.digits)] for a in content_tmp]
        case "Spell_Factory":
            content_tmp = content_tmp[:3]+[content_tmp[3]+content_tmp[4]]+content_tmp[5:]
            content_tmp = [a[0:2] + ['_'.join([b for b in a if not any(c in b for c in string.digits)])] + [c for c in a[3:] if any(d in c for d in string.digits)] for a in content_tmp]
        case "Barracks" | "Dark_Barracks" | "Dark_Spell_Factory" | "Hero_Hall" | "Pet_House" | "Workshop":
            content_tmp = [[a[0]] + ['_'.join([b for b in a if not any(c in b for c in string.digits)])] + [c for c in a[2:] if any(d in c for d in string.digits)] for a in content_tmp]
    content = [content_tmp_i[:len(columns)-index] + [''.join(content_tmp_i[len(columns)-index:-index+1])] + content_tmp_i[-index+1:] for content_tmp_i in content_tmp]
    table = DRIVER.find_elements(By.ID, "number-available-data-row")
    nb_buildings = ' '.join([i.text for i in table]).split()[2:]
    # print(content)
    toto = {columns[i]: [content[j][i] for j in range(len(content))] for i in range(len(columns))}
    toto["Number available"] = nb_buildings
    if page == "Barracks":
        toto["Town_Hall_Level_Required"][1] = "1"
        toto["Town_Hall_Level_Required"][2] = "1"
    if page == "Clan_Castle":
        toto["Number available"][0] = "1"
        toto["Number available"][1] = "1"
        toto["Town_Hall_Level_Required"][0] = "2"
    return toto



def retrieve_all_data():
    global DB, ALL_PAGES
    for page in ALL_PAGES:
        DB[page] = Page(page).data

def download_my_village():
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjU1NGQ2NDlmLWE4MTQtNGMzYi05OWVjLWIwNmNlNzJmMTg5OSIsImlhdCI6MTc0NjI4NTMzOSwic3ViIjoiZGV2ZWxvcGVyL2RlN2NlMjIxLWU2ZTgtNjY0Ni01YmQ5LWIwMTMyZWIxNTEyOCIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjgxLjY1LjE2My4xMjAiXSwidHlwZSI6ImNsaWVudCJ9XX0.2xuufB2wE2PJOyz7sap7l1W2GR37g2oisG9gIteCQC1auxnxhIPde4shfltj8t1RSMWECywaYw6anqa8-rya1A"
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://api.clashofclans.com/v1/players/%23GPQUUY989"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response:
        print(response.status)
        return json.load(response)


def in_seconds(date):
    seconds = 0
    a, b, c = date.partition('d')
    if b == 'd':
        seconds += int(a)
        a, b, c = c.partition('h')
    else:
        a, b, c = a.partition('h')
    seconds *= 24
    if b == 'h':
        seconds += int(a)
        a, b, c = c.partition('m')
    else:
        a, b, c = a.partition('m')
    seconds *= 60
    if b == 'm':
        seconds += int(a)
        a, b, c = c.partition('s')
    else:
        a, b, c = a.partition('s')
    seconds *= 60
    if b == 's':
        seconds += int(a)
    return seconds

def in_date(seconds):
    result = ""
    if seconds == 0:
        return result
    d = seconds // (60*60*24)
    seconds -= d*60*60*24
    h = seconds // (60*60)
    seconds -= h*60*60
    m = seconds // 60
    seconds -= m*60
    if d:
        result += str(d) + "d"
    if h:
        result += str(h) + "h"
    if m:
        result += str(m) + "m"
    if seconds:
        result += str(seconds) + "s"
    return result


def number_max(page, hdv):
    try:
        return int(DB[page]["Number available"][hdv-1])
    except IndexError:
        return 1

def level_max(page, hdv):
    try:
        return sum([int(toto) <= hdv for toto in DB[page]["Town_Hall_Level_Required"]])
    except KeyError:
        pass
    try:
        return sum([int(toto) <= level_max("Laboratory", hdv) for toto in DB[page]["Laboratory_Level_Required"]])
    except KeyError:
        pass
    try:
        return sum([int(toto) <= level_max("Hero_Hall", hdv) for toto in DB[page]["Hero_Hall_Level_Required"]])
    except KeyError:
        print(f"Warning: cannot find max level for {page} at HDV {hdv}")
        raise

##############
## DATABASE ##

BUILDINGS = ["Town_Hall", 'Cannon', 'Archer_Tower', 'Mortar', 'Air_Defense', 'Wizard_Tower', 'Air_Sweeper', 'Hidden_Tesla', 'Bomb_Tower',
             'X-Bow', 'Inferno_Tower', 'Eagle_Artillery', 'Scattershot', "Builder's_Hut", 'Spell_Tower', 'Monolith',
             "Bomb", "Spring_Trap", "Giant_Bomb", "Air_Bomb", "Seeking_Air_Mine", "Skeleton_Trap", "Tornado_Trap", "Giga_Bomb",
             "Army_Camp", "Barracks", "Dark_Barracks", "Laboratory", "Hero_Hall", "Dark_Spell_Factory",
             "Workshop", "Pet_House", "Blacksmith", "Spell_Factory", "Gold_Mine", "Elixir_Collector", "Dark_Elixir_Drill", 
             "Gold_Storage", "Elixir_Storage", "Dark_Elixir_Storage", "Clan_Castle", "Firespitter", "Multi-Archer_Tower",
             "Ricochet_Cannon", "Multi-Gear_Tower"]

HEROES = ["Barbarian_King", "Archer_Queen", "Minion_Prince", "Grand_Warden", "Royal_Champion", "Dragon_Duke"]

TROOPS = ["Barbarian", "Archer", "Giant", "Goblin", "Wall_Breaker", "Balloon", "Wizard", "Healer", "Dragon", "P.E.K.K.A",
          "Baby_Dragon", "Miner", "Electro_Dragon", "Yeti", "Dragon_Rider", "Electro_Titan", "Root_Rider", "Thrower",
          "Minion", "Hog_Rider", "Valkyrie", "Golem", "Witch", "Lava_Hound", "Bowler", "Ice_Golem", "Headhunter",
          "Apprentice_Warden", "Druid", "Furnace", "Meteor_Golem",
          "Wall_Wrecker", "Battle_Blimp", "Stone_Slammer", "Siege_Barracks", "Log_Launcher", "Flame_Flinger", "Battle_Drill", "Troop_Launcher",
          "Lightning_Spell", "Healing_Spell", "Rage_Spell", "Jump_Spell", "Freeze_Spell", "Clone_Spell", "Invisibility_Spell",
          "Recall_Spell", "Revive_Spell", "Poison_Spell", "Earthquake_Spell", "Haste_Spell", "Skeleton_Spell", "Bat_Spell",
          "Overgrowth_Spell", "Ice_Block_Spell", "Totem_Spell"]

CATEGORIES = ["BUILDINGS", "HEROES", "TROOPS"]

ALL_PAGES = BUILDINGS + HEROES + TROOPS

for building in BUILDINGS:
    DB[building] = BuildingInfo(building)
for troop in TROOPS:
    DB[troop] = TroopInfo(troop)
for hero in HEROES:
    DB[hero] = HeroInfo(hero)

PROUT = Village(17)
PROUT.load_from_exported_json()


def main():
    pass

if __name__ == "__main__":
    main()
