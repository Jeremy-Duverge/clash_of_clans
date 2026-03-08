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


class DriverManager:
    """Manages the Selenium WebDriver lifecycle.

    Can be used as a context manager for automatic cleanup::

        with DriverManager() as driver:
            driver.get(url)
            ...

    Or manually::

        dm = DriverManager()
        driver = dm.get_driver()
        ...
        dm.quit()
    """

    def __init__(self):
        self._driver = None

    def get_driver(self):
        """Lazily create and return the WebDriver instance."""
        if self._driver is None:
            self._driver = webdriver.Chrome(service=CSERVICE, options=OPTIONS)
        return self._driver

    def quit(self):
        """Quit the driver if it was created."""
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    def __enter__(self):
        return self.get_driver()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()
        return False


driver_manager = DriverManager()



####################
## IN GAME PARAMS ##

LVL = 17

BONUS = 20      # 15(%)


#############
## CLASSES ##

class PageInfo:
    """Base class for wiki page data.

    Loads stats from a local JSON cache file, or scrapes the Clash of Clans
    wiki page and caches the result on first access.

    Attributes:
        name: The page/entity name (e.g. 'Cannon', 'Barbarian').
        file: Path to the local JSON cache file.
        url: Full wiki URL for this page.
        info: Dict of parsed stats (column_name -> list of values per level).
    """

    def __init__(self, name):
        """Load page data from cache or scrape the wiki.

        Args:
            name: Entity name used for the filename and wiki URL.
        """
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
                            .replace("6/2*", "2")\
                            .replace("9/2*", "2")\
                            .replace("7/3*", "3")\
                            .replace("8/4*", "4")
            print(json_dumps_str, file=fp)
            print(json_dumps_str)
            self.info = json.loads(json_dumps_str)
    def __repr__(self):
        return f"{self.name}\n"+json.dumps(self.info).replace("{", "{\n    ").replace("}", "\n}").replace("], ", "],\n    ")

class BuildingInfo(PageInfo):
    """Page info for buildings and defenses.

    Provides building-specific lookups: max count, max level, and upgrade
    time based on Town Hall level.
    """

    def number_max(self, hdv):
        """Return the maximum number of this building allowed at the given Town Hall level.

        Args:
            hdv: Town Hall level (1-indexed).

        Returns:
            Maximum instance count as an int.
        """
        try:
            return int(self.info["Number available"][hdv-1])
        except Exception:
            print(f"Error: cannot find number max for {self.name} at HDV {hdv}\n{self.info}\n{self.url}")
            raise
    def level_max(self, hdv):
        """Return the maximum upgrade level for this building at the given Town Hall level.

        Args:
            hdv: Town Hall level.

        Returns:
            Maximum level as an int.
        """
        if self.name == "Town_Hall":
            return hdv
        try:
            return sum([int(toto) <= hdv for toto in self.info["Town_Hall_Level_Required"]])
        except Exception:
            print(f"Error: cannot find max level for {self.name} at HDV {hdv}\n{self.info}\n{self.url}")
            raise
    def get_upgrade_time(self, level):
        """Return the build/upgrade time string for the given level.

        Args:
            level: Target upgrade level (1-indexed).

        Returns:
            Duration string (e.g. '1d12h').
        """
        try:
            return self.info["Build_Time"][level-1]
        except KeyError:
            print(f"Error: cannot find build time for {self.name} at level {level}\n{self.info}\n{self.url}")
            raise

class TroopInfo(PageInfo):
    """Page info for troops, spells, and siege machines.

    Max level is determined by the Laboratory level achievable at a given
    Town Hall level.
    """

    def level_max(self, hdv):
        """Return the max troop level achievable at the given Town Hall level.

        Args:
            hdv: Town Hall level.

        Returns:
            Maximum level as an int, based on the Laboratory level at that TH.
        """
        try:
            labo = db["Laboratory"]
            return sum([int(toto) <= labo.level_max(hdv) for toto in self.info["Laboratory_Level_Required"]])
        except Exception:
            print(f"Error: cannot find max level for {self.name} at HDV {hdv}\n{self.info}\n{self.url}")
            raise
    def number_max(self, _):
        """Troops are unique so always return 1."""
        return 1
    def get_upgrade_time(self, level):
        """Return the research time string for the given level.

        Args:
            level: Target upgrade level (1-indexed).

        Returns:
            Duration string (e.g. '2d').
        """
        try:
            return self.info["Research_Time"][level-1]
        except KeyError:
            print(f"Error: cannot find upgrade time for {self.name} at level {level}\n{self.info}\n{self.url}")
            raise

class HeroInfo(PageInfo):
    """Page info for heroes.

    Max level is determined by the Hero Hall level achievable at a given
    Town Hall level.
    """

    def level_max(self, hdv):
        """Return the max hero level achievable at the given Town Hall level.

        Args:
            hdv: Town Hall level.

        Returns:
            Maximum level as an int, based on the Hero Hall level at that TH.
        """
        try:
            hero_hall = db["Hero_Hall"]
            return sum([int(toto) <= hero_hall.level_max(hdv) for toto in self.info["Hero_Hall_Level_Required"]])
        except Exception:
            print(f"Error: cannot find max level for {self.name} at HDV {hdv}\n{self.info}\n{self.url}")
            raise
    def number_max(self, _):
        """Heroes are unique so always return 1."""
        return 1
    def get_upgrade_time(self, level):
        """Return the upgrade time string for the given hero level.

        Args:
            level: Target upgrade level (1-indexed).

        Returns:
            Duration string (e.g. '5d12h').
        """
        try:
            return self.info["Upgrade_Time"][level-1]
        except KeyError:
            print(f"Error: cannot find upgrade time for {self.name} at level {level}\n{self.info}\n{self.url}")
            raise

class Database:
    """Cache for all entity data (buildings, troops, heroes).

    Lazily loads and caches PageInfo instances on first access.
    Use bracket notation to retrieve entities: ``db["Cannon"]``.

    Attributes:
        _cache: Internal dict of loaded PageInfo instances.
        _building_names: Set of building/defense names.
        _troop_names: Set of troop/spell/siege machine names.
        _hero_names: Set of hero names.
    """

    def __init__(self, building_names, troop_names, hero_names):
        """Initialize the database with entity name lists.

        Args:
            building_names: List of building/defense names.
            troop_names: List of troop/spell/siege machine names.
            hero_names: List of hero names.
        """
        self._cache = {}
        self._building_names = set(building_names)
        self._troop_names = set(troop_names)
        self._hero_names = set(hero_names)

    def __getitem__(self, name):
        """Retrieve a PageInfo instance by name, loading it lazily if needed.

        Args:
            name: Entity name (e.g. 'Cannon', 'Barbarian').

        Returns:
            The corresponding BuildingInfo, TroopInfo, or HeroInfo instance.

        Raises:
            KeyError: If the name is not recognized.
        """
        if name not in self._cache:
            if name in self._building_names:
                self._cache[name] = BuildingInfo(name)
            elif name in self._troop_names:
                self._cache[name] = TroopInfo(name)
            elif name in self._hero_names:
                self._cache[name] = HeroInfo(name)
            else:
                raise KeyError(f"Unknown entity: {name}")
        return self._cache[name]

    def __contains__(self, name):
        """Check if a name is a known entity."""
        return name in self._building_names or name in self._troop_names or name in self._hero_names

    def load_all(self):
        """Eagerly load all entities into the cache."""
        for name in list(self._building_names) + list(self._troop_names) + list(self._hero_names):
            _ = self[name]

class IdMap:
    """Bidirectional mapping between numeric data IDs and entity names.

    Loaded from 'id_map.json'. Supports lookup in both directions via
    bracket notation: ``id_map[1000008]`` -> ``'Cannon'`` and
    ``id_map['Cannon']`` -> ``1000008``.

    Attributes:
        id_to_name: Dict mapping dataId (int) to name (str).
        name_to_id: Dict mapping name (str) to dataId (int).
    """

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
    """A single building instance in a village with a name and current level."""

    def __init__(self, name, level=0):
        """Create a building instance.

        Args:
            name: Building name (e.g. 'Cannon').
            level: Current upgrade level (default 0 = not yet built).
        """
        self.name = name
        self.level = level
    def __repr__(self):
        return f"Building {self.name} ({self.level})"
    def set_level(self, level):
        self.level = level
    def level_max(self, hdv):
        ref = db[self.name]
        return ref.level_max(hdv)

class Troop:
    """A single troop/spell/siege machine with a name and current level."""

    def __init__(self, name, level=1):
        """Create a troop instance.

        Args:
            name: Troop name (e.g. 'Barbarian').
            level: Current research level (default 1).
        """
        self.name = name
        self.level = level
    def __repr__(self):
        return f"Troop {self.name} ({self.level})"
    def set_level(self, level):
        self.level = level
    def level_max(self, hdv):
        ref = db[self.name]
        return ref.level_max(hdv)

class Hero:
    """A single hero instance with a name and current level."""

    def __init__(self, name, level=1):
        """Create a hero instance.

        Args:
            name: Hero name (e.g. 'Barbarian_King').
            level: Current hero level (default 1).
        """
        self.name = name
        self.level = level
    def __repr__(self):
        return f"Hero {self.name} ({self.level})"
    def set_level(self, level):
        self.level = level
    def level_max(self, hdv):
        ref = db[self.name]
        return ref.level_max(hdv)

class Village:
    """Represents a player's village: buildings, heroes, and troops.

    Can be populated from an exported JSON snapshot and compared against
    the max levels for a given Town Hall to plan upgrades.

    Attributes:
        hdv_level: Current Town Hall level.
        buildings: Dict mapping building name to list of Building instances.
        heroes: List of Hero instances.
        troops: List of Troop instances.
    """

    def __init__(self, hdv_level=0):
        """Create an empty village.

        Args:
            hdv_level: Town Hall level (default 0).
        """
        self.hdv_level = hdv_level
        self.buildings = {}
        self.heroes = []
        self.troops = []
    def load_from_exported_json(self):
        """Populate the village from 'exported_village.json'.

        Reads buildings, traps, heroes, troops, spells, and siege machines.
        Walls and the Town Hall entry are removed from the buildings dict
        (the TH level is stored in ``self.hdv_level`` instead).
        """
        with open('exported_village.json', 'r') as fp:
            data = json.load(fp)
        id_map = IdMap()
        for building in data["buildings"] + data["traps"]:
            if building["data"] not in id_map.id_to_name:
                print(f"Warning: cannot find name for {building}")
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
        del self.buildings["Town_Hall"]
        for hero in data["heroes"]:
            self.heroes.append(Hero(id_map[hero["data"]], hero["lvl"]))
        for troop in data["units"] + data["spells"] + data["siege_machines"]:
            self.troops.append(Troop(id_map[troop["data"]], troop["lvl"]))
    def check_nb_buildings(self, hdv):
        """Ensure the village has the correct number of each building for the given TH level.

        Adds missing buildings at level 0 and prints warnings for mismatches.

        Args:
            hdv: Town Hall level to validate against.
        """
        for building, instances in self.buildings.items():
            if len(instances) > db[building].number_max(hdv):
                print(f"Warning: too many {building} (have {len(instances)}, max {db[building].number_max(hdv)})")
            elif len(instances) < db[building].number_max(hdv):
                self.buildings[building] += [Building(building, 0) for _ in range(db[building].number_max(hdv) - len(instances))]
                print(f"Warning: too few {building}, adding {db[building].number_max(hdv) - len(instances)} of them at level 0")
        for building in BUILDINGS:
            if building not in self.buildings and db[building].number_max(hdv) > 0:
                self.buildings[building] = [Building(building, 0) for _ in range(db[building].number_max(hdv))]
                print(f"Warning: missing {building}, adding {db[building].number_max(hdv)} of them at level 0")
    def to_max(self, hdv):
        """Print the full upgrade plan to max everything for the given TH level.

        Args:
            hdv: Target Town Hall level.
        """
        self.check_nb_buildings(hdv)
        upgrader = Upgrader()
        my_string = f"Village (HDV {self.hdv_level})\n\nBUILDINGS:\n"
        for building, instances in self.buildings.items():
            if building == "Archer_Tower":
                continue
            level_max = db[building].level_max(hdv)
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
    """Represents the sequence of upgrades needed to bring one entity to a target level.

    Computes each upgrade step with its duration (accounting for the builder
    boost bonus) and the total time.

    Attributes:
        name: Entity name.
        list_upgrades: List of (level, duration_str) tuples, highest level first.
        time_total: Total upgrade time in seconds.
        offset: Display offset for alignment in the Upgrader output.
    """

    def __init__(self, building, level_max):
        """Compute all upgrade steps from the entity's current level to level_max.

        Args:
            building: A Building, Troop, or Hero instance.
            level_max: Target level to reach.
        """
        self.name = building.name
        self.list_upgrades = []
        self.time_total = 0
        self.offset = 0
        for i in range(level_max, building.level, -1):
            try:
                upgrade_time = int((1.-0.01*BONUS)*in_seconds(db[building.name].get_upgrade_time(i)))
            except KeyError:
                print(f"Error: cannot find upgrade time for {building.name} at level {i}\n{db[building.name].info}\n{db[building.name].url}")
                raise
            self.list_upgrades.append((i, in_date(upgrade_time)))
            self.time_total += upgrade_time
    def set_offset(self, offset):
        """Set the display offset for aligned output."""
        self.offset = offset
    def __lt__(self, other):
        return self.time_total < other.time_total
    def __repr__(self):
        string = f"[{self.name.rjust(21)}|"
        for upgrade in self.list_upgrades:
            string += f" {str(upgrade[0]).rjust(3)}: {upgrade[1].ljust(9)} |"
        for _ in range(self.offset):
            string += " "*(17)
        string += f" TOTAL: {in_date(self.time_total).ljust(12)}]"
        cursor = 158
        while cursor+40 < len(string):
            string = string[:cursor] + "\n" + " "*22 + string[cursor:]
            cursor += 176
        return string

class Upgrader:
    """Collects and displays all upgrades needed across buildings, heroes, and troops.

    Sorts upgrades by total time (longest first) and displays a formatted
    summary with per-category and overall totals.
    """

    def __init__(self):
        self.max_buildings = 0
        self.max_heroes = 0
        self.max_troops = 0
        self.buildings = []
        self.heroes = []
        self.troops = []
    def add(self, building, level_max):
        """Add an entity's upgrade plan to the appropriate category.

        Args:
            building: A Building, Troop, or Hero instance.
            level_max: Target level to reach.

        Raises:
            ValueError: If the entity type is not recognized.
        """
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
        """Sort upgrades by total time (descending) and compute display offsets."""
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
        my_string += f"\nTOTAL BUILDINGS: {in_date(total_buildings).ljust(12)}"
        my_string += f"\nTOTAL HEROES   : {in_date(total_heroes).ljust(12)}"
        my_string += f"\nTOTAL TROOPS   : {in_date(total_troops).ljust(12)}"
        return my_string

###############
## FUNCTIONS ##

def extract_from_page(page):
    """Scrape stats for a given entity from its Clash of Clans wiki page.

    Navigates to the wiki, extracts the stats table, parses columns and
    content, and returns a dict of {column_name: [values_per_level]}.

    Args:
        page: Entity name (e.g. 'Cannon', 'Barbarian').

    Returns:
        Dict mapping column names to lists of string values.
    """
    url = BASE_URL + page
    print(f'Downloading content for {page} : {url}')
    driver = driver_manager.get_driver()
    driver.get(url)
    if driver.title == 'Privacy error':
        driver.find_element(By.ID, "details-button").click()
        driver.find_element(By.ID, "proceed-link").click()
        time.sleep(1)
    if driver.title == "Just a moment...":
        exit("Error: Cloudflare protection is on, please disable it and try again.")
    if page in TROOPS or page in HEROES or page == "Town_Hall":
        if page in ["Bat_Spell", "Skeleton_Spell"]:
            text = driver.find_elements(By.CLASS_NAME, "wikitable")[2].text.splitlines()
        else:
            text = driver.find_elements(By.CLASS_NAME, "wikitable")[1].text.splitlines()
        index = 2
    elif page == "Revenge_Tower":
        text = driver.find_elements(By.CLASS_NAME, "wikitable")[6].text.splitlines()
        index = 3
    else:
        print(driver.title)
        text = driver.find_element(By.CLASS_NAME, "wikitable").text.splitlines()
        index = 3
    print(f"text =\n{text}")
    columns = extract_columns(page, text)
    print(f"columns =\n{columns}")
    return extract_content(page, text, columns, index)

def extract_columns(page, text):
    """Parse column headers from the raw wiki table text.

    Applies page-specific overrides for pages whose table layout doesn't
    follow the standard pattern.

    Args:
        page: Entity name.
        text: List of text lines from the wiki table.

    Returns:
        List of column name strings.
    """
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

def fuse_date_in_list(i_list, pos):
    """Try to merge two adjacent duration fragments in a list (e.g. '1d' + '12h' -> '1d12h').

    Args:
        i_list: List of string tokens.
        pos: Index of the first token to check.

    Returns:
        Tuple of (modified list, True if a merge was performed).
    """
    string1 = i_list[pos]
    string2 = i_list[pos+1]
    if string1[-1] not in ['d', 'h', 'm', 's'] or string2[-1] not in ['d', 'h', 'm', 's']:
        return i_list, False
    for char in string1:
        if char not in string.digits and char not in ['d', 'h', 'm', 's']:
            return i_list, False
    for char in string2:
        if char not in string.digits and char not in ['d', 'h', 'm', 's']:
            return i_list, False
    i_list[pos] += i_list[pos+1]
    del i_list[pos+1]
    return i_list, True

def extract_content(page, text, columns, index):
    """Parse the data rows from the wiki table into a column-oriented dict.

    Applies page-specific cleanup (removing unit words, fusing split dates,
    etc.) and also fetches the 'Number available' row from the page.

    Args:
        page: Entity name.
        text: List of text lines from the wiki table.
        columns: List of column name strings.
        index: Number of trailing columns to handle specially (2 or 3).

    Returns:
        Dict mapping column names to lists of string values per level.
    """
    driver = driver_manager.get_driver()
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
    table = driver.find_elements(By.ID, "number-available-data-row")
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
    """Eagerly load all entities into the database cache."""
    db.load_all()

def download_my_village():
    """Fetch the player's village data from the Clash of Clans API.

    Returns:
        Dict of the player's village data as returned by the API.
    """
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjU1NGQ2NDlmLWE4MTQtNGMzYi05OWVjLWIwNmNlNzJmMTg5OSIsImlhdCI6MTc0NjI4NTMzOSwic3ViIjoiZGV2ZWxvcGVyL2RlN2NlMjIxLWU2ZTgtNjY0Ni01YmQ5LWIwMTMyZWIxNTEyOCIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjgxLjY1LjE2My4xMjAiXSwidHlwZSI6ImNsaWVudCJ9XX0.2xuufB2wE2PJOyz7sap7l1W2GR37g2oisG9gIteCQC1auxnxhIPde4shfltj8t1RSMWECywaYw6anqa8-rya1A"
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://api.clashofclans.com/v1/players/%23GPQUUY989"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response:
        print(response.status)
        return json.load(response)


def in_seconds(date):
    """Convert a duration string (e.g. '1d12h30m') to total seconds.

    Args:
        date: Duration string with optional d/h/m/s components.

    Returns:
        Total duration in seconds as an int.
    """
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
    """Convert a number of seconds to a human-readable duration string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string (e.g. '1d12h30m'), or empty string if 0.
    """
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


##############
## DATABASE ##

BUILDINGS = ['Cannon', 'Archer_Tower', 'Mortar', 'Air_Defense', 'Wizard_Tower', 'Air_Sweeper', 'Hidden_Tesla', 'Bomb_Tower',
             'X-Bow', 'Inferno_Tower', 'Eagle_Artillery', 'Scattershot', "Builder's_Hut", 'Spell_Tower', 'Monolith',
             "Bomb", "Spring_Trap", "Giant_Bomb", "Air_Bomb", "Seeking_Air_Mine", "Skeleton_Trap", "Tornado_Trap", "Giga_Bomb",
             "Army_Camp", "Barracks", "Dark_Barracks", "Laboratory", "Hero_Hall", "Dark_Spell_Factory",
             "Workshop", "Pet_House", "Blacksmith", "Spell_Factory", "Gold_Mine", "Elixir_Collector", "Dark_Elixir_Drill", 
             "Gold_Storage", "Elixir_Storage", "Dark_Elixir_Storage", "Clan_Castle", "Firespitter", "Multi-Archer_Tower",
             "Ricochet_Cannon", "Multi-Gear_Tower", "Super_Wizard_Tower", "Revenge_Tower"]

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

db = Database(BUILDINGS, TROOPS, HEROES)

PROUT = Village(17)
PROUT.load_from_exported_json()


def main():
    pass

if __name__ == "__main__":
    main()
