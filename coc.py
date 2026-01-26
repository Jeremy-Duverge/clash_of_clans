#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import json
import string
import urllib

CSERVICE = webdriver.ChromeService(executable_path='/usr/bin/chromedriver')
OPTIONS = webdriver.ChromeOptions()
OPTIONS.add_argument('--incognito')
BASE_URL = "https://clashofclans.fandom.com/wiki/"
TAG = "https://api.clashofclans.com/v1/players/%23GPQUUY989"


####################
## IN GAME PARAMS ##

LVL = 10

BONUS = 20      # 15(%)


#############
## CLASSES ##

class Page:
    def __init__(self, name, level=0):
        self.name = name
        self.data = {}
        if level == 0:
            if name in BUILDINGS:
                self.level = 0
            else:
                self.level = 1
        else:
            self.level = level
        try:
            self.get_info_from_file()
        except FileNotFoundError:
            self.data = extract_from_page(self.name)
            self.update(self.data)
    def __repr__(self):
        return f"{self.name}({self.level})"
    def update(self, info):
        with open('data/'+self.name+'.json', 'w') as fp:
            json_dumps_str = json.dumps(info)\
                            .replace("{", "{\n    ")\
                            .replace("}", "\n}")\
                            .replace("], ", "],\n    ")\
                            .replace("N/A", "0")\
                            .replace("5*", "5")\
                            .replace("/0*", "")\
                            .replace("/2*", "")\
                            .replace("/3*", "")\
                            .replace("/4*", "")
            print(json_dumps_str, file=fp)
    def get_info_from_file(self):
        with open('data/'+self.name+'.json', 'r') as fp:
            self.data = json.load(fp)
    def set_level(self, level):
        self.level = level

class HDV:
    def __init__(self, level=0):
        global BUILDINGS, TROOPS
        self.level = level
        self.buildings = {a: [] for a in BUILDINGS}
        self.troops = {a: 0 for a in TROOPS}
    def set_max(self):
        for page in BUILDINGS:
            self.buildings[page] = [level_max(page, self.level)]*number_max(page, self.level)
        for page in TROOPS:
            self.troops[page] = level_max(page, self.level)
        return self
    def get_page(self, page):
        try:
            return self.buildings[page]
        except KeyError:
            try:
                return self.troops[page]
            except KeyError:
                return []
    def to_max(self, hdv):
        buildings = []
        troops = []
        max_diff = 0
        max_diff_hero = 0
        for page in BUILDINGS:
            my_page = self.buildings[page]
            max_page = [level_max(page, hdv)]*number_max(page, hdv)
            a = len(my_page)
            b = len(max_page)
            if a == 0 or b == 0:
                continue
            my_page[a:b] = [0]*(b-a)
            if page in HEROES:
                max_diff_hero = max(max([max_page[i]-my_page[i] for i in range(len(my_page))]), max_diff_hero)
            else:
                max_diff = max(max([max_page[i]-my_page[i] for i in range(len(my_page))]), max_diff)
            for i in range(b):
                if my_page[i] >= max_page[i]:
                    continue
                buildings.append([page.rjust(18)])
                building_time = 0
                for j in range(my_page[i], max_page[i]):
                    try:
                        upgrade_time = int((1.-0.01*BONUS)*in_seconds(DB[page]["Build_Time"][j]))
                    except KeyError:
                        upgrade_time = int((1.-0.01*BONUS)*in_seconds(DB[page]["Upgrade_Time"][j]))
                    buildings[-1] += [str(j+1).rjust(2), in_date(upgrade_time).rjust(8)]
                    building_time += upgrade_time
                buildings[-1] += ["Total:", in_date(building_time).rjust(8)]
        buildings.sort(key=lambda x: in_seconds(x[-1]), reverse=True)
        buildings.sort(key=lambda x: int(x[1]) == 1, reverse=True)
        for i in range(len(buildings)):
            if buildings[i][0].lstrip() in HEROES:
                buildings[i] = buildings[i][:-2] + ['  ', '        ']*int(max_diff_hero+1.5-0.5*len(buildings[i])) + buildings[i][-2:]
            else:
                buildings[i] = buildings[i][:-2] + ['  ', '        ']*int(max_diff+1.5-0.5*len(buildings[i])) + buildings[i][-2:]
        max_diff = 0
        for page in TROOPS:
            my_page = self.troops[page]
            max_page = level_max(page, hdv)
            max_diff = max(max_page-my_page, max_diff)
            if my_page >= max_page:
                continue
            troops.append([page.rjust(18)])
            troop_time = 0
            for j in range(my_page, max_page):
                upgrade_time = int((1.-0.01*BONUS)*in_seconds(DB[page]["Research_Time"][j]))
                troops[-1] += [str(j+1).rjust(2), in_date(upgrade_time).rjust(8)]
                troop_time += upgrade_time
            troops[-1] += ["Total:", in_date(troop_time).rjust(8)]
        troops.sort(key=lambda x: in_seconds(x[-1]), reverse=True)
        for i in range(len(troops)):
            troops[i] = troops[i][:-2] + ['  ', '        ']*int(max_diff+1.5-0.5*len(troops[i])) + troops[i][-2:]
        print()
        print("BUILDINGS:")
        for i in buildings:
            print(i)
        print("TOTAL: ", in_date(sum([in_seconds(buildings[i][-1]) for i in range(len(buildings))])))
        print("\nTROOPS:")
        for i in troops:
            print(i)
        print("TOTAL: ", in_date(sum([in_seconds(troops[i][-1]) for i in range(len(troops))])))
        print()

###############
## FUNCTIONS ##

def init_driver():
    global DRIVER, CSERVICE, OPTIONS
    try:
        DRIVER.title
    except AttributeError:
        DRIVER = webdriver.Chrome(service=CSERVICE, options=OPTIONS)

def extract_from_page(page):
    global DRIVER, LABO, SPELLS
    print(f'Downloading content for {page}')
    init_driver()
    url = BASE_URL + page
    DRIVER.get(url)
    if page in LABO or page in SPELLS or page in HEROES:
        if page in ["Bat_Spell", "Skeleton_Spell"]:
            text = DRIVER.find_elements(By.CLASS_NAME, "wikitable")[2].text.splitlines()
        else:
            text = DRIVER.find_elements(By.CLASS_NAME, "wikitable")[1].text.splitlines()
        index = 2
    else:
        text = DRIVER.find_element(By.CLASS_NAME, "wikitable").text.splitlines()
        index = 3
    print(text)
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
        case "Clone_Spell":
            columns = ["Level", "Cloned_Capacity", "Research_Cost", "Research_Time", "Laboratory_Level_Required"]
        case "Freeze_Spell":
            columns = ["Level", "Freeze_Time", "Research_Cost", "Research_Time", "Laboratory_Level_Required"]
        case "Blacksmith":
            columns = ['Level', 'Equipment_Unlocked', 'Hitpoints', 'Ore_Capacity_Shiny', 'Ore_Capacity_Glowy', 'Ore_Capacity_Starry', 'Maximum_Equipment_Level_Common', 'Maximum_Equipment_Level_Epic', 'Build_Cost', 'Build_Time', 'Experience_Gained', 'Town_Hall_Level_Required']
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
            columns = ["Level", "Damage_per_Second", "Damage_per_Attack", "Freeze_Time_After_Death_ATK", "Freeze_Time_After_Death_DEF", "Hitpoints", "Research_Cost", "Research_Time", "Laboratory_Level_Required"]
        case "Lava_Hound":
            columns = ["Level", "Damage_per_Second", "Damage_per_Hit", "Damage_Upon_Death", "Lava_Pups_Spawned_ATK", "Lava_Pups_Spawned_DEF", "Hitpoints", "Research_Cost", "Research_Time", "Laboratory_Level_Required"]
    content_tmp = [i.split() for i in text if any(j in i for j in string.digits)]
    match page:
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
        case "Electro_Dragon":
            columns.remove("(Primary_Target)")
            columns.remove("(Primary_Target)")
            _ = [toto.remove("x6") for toto in content_tmp]
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
    toto = {columns[i]: [content[j][i] for j in range(len(content))] for i in range(len(columns))}
    toto["Number available"] = nb_buildings
    if page == "Barracks":
        toto["Town_Hall_Level_Required"][1] = "1"
        toto["Town_Hall_Level_Required"][2] = "1"
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
        try:
            return sum([int(toto) <= level_max("Laboratory", hdv) for toto in DB[page]["Laboratory_Level_Required"]])
        except KeyError:
            return sum([int(toto) <= level_max("Hero_Hall", hdv) for toto in DB[page]["Hero_Hall_Level_Required"]])


##############
## DATABASE ##

CATEGORIES = ["DEFENSE", "ATTACK", "TRAPS", "HEROES", "LABO", "SPELLS"]


DEFENSE = ['Cannon', 'Archer_Tower', 'Mortar', 'Air_Defense', 'Wizard_Tower', 'Air_Sweeper', 'Hidden_Tesla', 'Bomb_Tower',
           'X-Bow', 'Inferno_Tower', 'Eagle_Artillery', 'Scattershot', "Builder's_Hut", 'Spell_Tower', 'Monolith']

ATTACK = ["Army_Camp", "Barracks", "Dark_Barracks", "Laboratory", "Hero_Hall", "Dark_Spell_Factory",
          "Workshop", "Pet_House", "Blacksmith", "Spell_Factory"]

TRAPS = ["Bomb", "Spring_Trap", "Giant_Bomb", "Air_Bomb", "Seeking_Air_Mine", "Skeleton_Trap", "Tornado_Trap", "Giga_Bomb"]


HEROES = ["Barbarian_King", "Archer_Queen", "Minion_Prince", "Grand_Warden", "Royal_Champion"]


LABO = ["Barbarian", "Archer", "Giant", "Goblin", "Wall_Breaker", "Balloon", "Wizard", "Healer", "Dragon", "P.E.K.K.A",
        "Baby_Dragon", "Miner", "Electro_Dragon", "Yeti", "Dragon_Rider", "Electro_Titan", "Root_Rider", "Thrower",
        "Minion", "Hog_Rider", "Valkyrie", "Golem", "Witch", "Lava_Hound", "Bowler", "Ice_Golem", "Headhunter",
        "Apprentice_Warden", "Druid", "Furnace"]

SPELLS = ["Lightning_Spell", "Healing_Spell", "Rage_Spell", "Jump_Spell", "Freeze_Spell", "Clone_Spell", "Invisibility_Spell",
          "Recall_Spell", "Revive_Spell", "Poison_Spell", "Earthquake_Spell", "Haste_Spell", "Skeleton_Spell", "Bat_Spell", "Overgrowth_Spell"]


BUILDINGS = DEFENSE+ATTACK+TRAPS+HEROES

TROOPS = LABO+SPELLS


ALL_PAGES = BUILDINGS + TROOPS


DRIVER = None

DB = {}

def init_my_hdv():
    global MY_HDV, HDV, LVL
    MY_HDV = HDV(LVL)
    with open('my_buildings.json', 'r') as fp:
        my_pages = json.load(fp)
    for category in ["DEFENSE", "ATTACK", "TRAPS", "HEROES"]:
        for page in eval(category):
            MY_HDV.buildings[page] = my_pages[category][page]
    for category in ["LABO", "SPELLS"]:
        for page in eval(category):
            MY_HDV.troops[page] = my_pages[category][page]


if __name__ == "__main__":
    retrieve_all_data()
    
    MAX_VILLAGE = HDV(LVL)
    MAX_VILLAGE.set_max()
    
    MY_HDV = HDV(LVL)
    init_my_hdv()

    MY_HDV.to_max(LVL)
