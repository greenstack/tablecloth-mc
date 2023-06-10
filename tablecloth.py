#!/usr/bin/python3

# Tablecloth Alpha 0.2

# ===================================LICENSE====================================
# Copyright © 2022-2023 GreenstackJ

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

# Tablecloth is a software designed to automatically download jars for Minecraft
# servers modded with Fabric from the CLI.

import argparse
import collections.abc
import copy
import json
import os
import requests
import shutil
import subprocess
import sys

TABLECLOTH_CONFIG_PATH = 'tablecloth.json'

DEFAULT_MINECRAFT_VERSION = "1.20"
DEFAULT_FABRIC_LOADER = "0.14.21"
DEFAULT_FABRIC_INSTALLER = "0.11.2"

# This is only used when no jar name has been provided in the settings or that
# name is otherwise empty. The default configuration doesn't use this string;
# the default is server.jar
SERVER_JAR_NAME_PATTERN = "fabric-server-mc.{}-loader.{}-launcher.{}.jar"

CONFIG_PROFILES = "profiles"
CONFIG_SETTINGS = "settings"

CONFIG_MODS = "mods"
CONFIG_MINECRAFT_VERSION = "minecraft-version"
CONFIG_FABRIC = "fabric"
CONFIG_FABRIC_LOADER_VERSION = "loader-version"
CONFIG_FABRIC_INSTALLER_VERSION = "installer-version"
CONFIG_SERVER_JAR_NAME = "jar-name"

CONFIG_MOD_NAME = "name"
CONFIG_MOD_VERSION = "version"
CONFIG_MOD_MODRINTH = "modrinth"
CONFIG_MOD_MODRINTH_PROJECT_ID = "project-id"
CONFIG_MOD_MODRINTH_VERSION_ID = "version-id"
CONFIG_MOD_MODRINTH_DOWNLOAD_URL = "download-url"
CONFIG_MOD_MODRINTH_FILENAME = "filename"
CONFIG_MOD_MODRINTH_HASHES = "hashes"
CONFIG_MOD_MODRINTH_HASHES_SHA512 = "sha512"
CONFIG_MOD_MODRINTH_HASHES_SHA1 = "sha1"

MODRINTH_API_BASE = "https://api.modrinth.com/v2/"
MODRINTH_PROJECT_API = MODRINTH_API_BASE + "project/{}"
MODRINTH_VERSION_API = MODRINTH_API_BASE + "project/{}/version"

class TableclothArgparseFactory:
	def __init__(self, argparser):
		self.__commandStack = [argparser.add_subparsers()]
		self.__currentParser = None
	
	def _current(self):
		return self.__commandStack[-1]

	def StartGroup(self, parserName):
		# I have this mixed up. A Parser is given Subparsers; subparsers are given
		# parsers. They aren't given each other the thing.
		parser = self._current().add_parser(parserName)
		self.__commandStack.append(parser.add_subparsers())

	def StartParser(self, commandName: str, description: str) -> None:
		self.__currentParser = self._current().add_parser(commandName)

	def AddArgument(self, argName: str, help: str) -> None:
		self.__currentParser.add_argument(argName, help)

	def EndParser(self, actionType: type) -> None:
		self.__currentParser.set_defaults(func = lambda argv, config: actionType(config).Perform(argv))
		self.__currentParser = None

	def EndGroup(self) -> None:
		self.__commandStack.pop()
	
# Represents a Tablecloth installation profile.
class TableclothProfile:
	def __init__(self, name: str, mcVer:str = DEFAULT_MINECRAFT_VERSION, fabricLoaderVer:str = DEFAULT_FABRIC_LOADER, fabricInstallerVer:str = DEFAULT_FABRIC_INSTALLER) -> None:
		self.__name = name
		self.__minecraftVersion = mcVer
		self.__fabricLoaderVersion = fabricLoaderVer
		self.__fabricInstallerVersion = fabricInstallerVer
		self.__mods = {}
		self.__jarName = None
		self.__javaPath = None
		self.__javaArgs = []

	def Name(self):
		return self.__name

	def SetMinecraftVersion(self, minecraftVersion: str) -> None:
		self.__minecraftVersion = minecraftVersion

	# Returns the Minecraft version of this profile.
	def GetMinecraftVersion(self) -> str:
		return self.__minecraftVersion

	def SetFabricInstallerVersion(self, fabricInstallerVersion: str) -> None:
		self.__fabricInstallerVersion = fabricInstallerVersion

	def GetFabricInstallerVersion(self) -> str:
		return self.__fabricInstallerVersion

	def SetFabricLoaderVersion(self, fabricLoaderVersion: str) -> None:
		self.__fabricLoaderVersion = fabricLoaderVersion

	def GetFabricLoaderVersion(self) -> str:
		return self.__fabricLoaderVersion

	def FromDict(name: str, data: dict):
		#todo: data validation
		profile = TableclothProfile(
			name,
			data['minecraft']['version'],
			data["fabric"]["loader"],
			data["fabric"]["installer"]
		)

		for mod, settings in data["mods"].items():
			profile.__deserializeMod(mod, settings)

		profile.SetJarName(data["overrides"]["jar-name"])
		profile.SetJavaPath(data["overrides"]["java-path"])
		profile.__javaArgs = data["overrides"]["java-args"]

		return profile

	def Mods(self) -> dict:
		return self.__mods

	def ToDict(self) -> dict:
		return {
			"minecraft": {
				"version": self.__minecraftVersion
			},
			"fabric": {
				"loader": self.__fabricLoaderVersion,
				"installer": self.__fabricInstallerVersion,
			},
			"mods": self.__mods,
			"overrides": {
				"jar-name": self.__jarName,
				"java-path": self.__javaPath,
				"java-args": self.__javaArgs,
			}
		}
		
	def __deserializeMod(self, modName, settings) -> None:
		self.__mods[modName] = settings

	def AddMod(self, modName, version) -> bool:
		if modName in self.__mods:
			print("{} is already registered to profile {}!".format(modName, self.__name))
			return False

		modInfo = ModrinthHostService().GetHostModInfo(
			self.GetMinecraftVersion(),
			modName,
			version
		)

		if not modInfo:
			print("Couldn't add the mod")
			return False

		self.__mods[modName] = {
			"version": version,
			"enabled": True,
			"modrinth": modInfo,
		}
		return True

	def UpdateMod(self, modName, version) -> bool:
		if not modName in self.__mods:
			print("Mod {} hasn't been added to this profile!".format(modName))
			return False

		modInfo = ModrinthHostService().GetHostModInfo(
			self.GetMinecraftVersion(),
			modName,
			version
		)

		if not modInfo:
			return
		
		self.__mods[modName] = {
			"version": version,
			"enabled": self.__mods[modName]["enabled"],
			"modrinth": modInfo,
		}

		if not self.__mods[modName]["enabled"]:
			print("Updated the mod, but it's still disabled")

	def RemoveMod(self, modName) -> None:
		self.__mods.pop(modName)

	# Gets a list of all mods in this profile.
	def ListMods(self) -> list:
		return self.__mods.keys()

	# Determines if a mod exists in this profile.
	def HasMod(self, modName) -> bool:
		return modName in self.ListMods()

	def SetJarName(self, jarName) -> None:
		self.__jarName = jarName

	def GetJarName(self) -> str:
		return self.__jarName

	def DoesOverrideJarName(self) -> bool:
		return self.GetJarName() is not None

	def SetJavaPath(self, javaPath) -> None:
		self.__javaPath = javaPath

	def GetJavaPath(self) -> str:
		return self.__javaPath

	def DoesOverrideJavaPath(self) -> bool:
		return self.GetJavaPath() is not None

# Represents and provides methods for Tablecloth configuration.
class TableclothConfig:
	def __defaultConfig() -> dict:
		return {
			CONFIG_PROFILES: {
				"default": TableclothProfile("default")
			},
			CONFIG_SETTINGS: {
				"assume-current-profile": True,
				"current-profile": "default",
				"launch": {
					"jar-name": "server.jar",
					"java-path": None,
					"min-ram": "1G",
					"max-ram": "2G",
					"java-args": []
				},
				"validation": {
					"hashes": True,
					"size": True,
				}
			}
		}

	def __init__(self):
		if (not os.path.exists(TABLECLOTH_CONFIG_PATH)):
			self.__config = TableclothConfig.__defaultConfig()
			self.__isDirty = True
			return

		self.__config = TableclothConfig.Load(TABLECLOTH_CONFIG_PATH)
		self.__isDirty = False

	def IsDirty(self) -> bool:
		return self.__isDirty
	
	def MarkDirty(self) -> None:
		self.__isDirty = True

	def Load(filePath) -> dict:
		with open(filePath, 'r') as configFile:
			config = json.load(configFile)
		profiles = {}
		for profile, data in config[CONFIG_PROFILES].items():
			profiles[profile] = TableclothProfile.FromDict(profile, data)
		config.pop(CONFIG_PROFILES)
		config[CONFIG_PROFILES] = profiles
		return config

	def Save(self):
		with open(TABLECLOTH_CONFIG_PATH, 'w') as configFile:
			# We indent because we need the config to be more easily human-readable
			json.dump(self.ToDict(), configFile, indent=4)

	def GetLaunchInfo(self):
		return self.__config[CONFIG_SETTINGS]["launch"]

	def AddProfile(self, profileName: str, mcVersion: str, fabLoaderVer: str, fabInstallerVer: str):
		self.__config[CONFIG_PROFILES][profileName] = TableclothProfile(mcVersion, fabLoaderVer, fabInstallerVer)
		self.MarkDirty()

	def RenameProfile(self, oldProfileName: str, newProfileName: str):
		self.__config[CONFIG_PROFILES][newProfileName] = self.__config[CONFIG_PROFILES][oldProfileName]
		del self.__config[CONFIG_PROFILES][oldProfileName]
		self.MarkDirty()

	def CopyProfile(self, oldProfileName: str, newProfileName: str) -> bool:
		if newProfileName in self.__config[CONFIG_PROFILES]:
			print("Profile {0:s} already exists!".format(newProfileName))
			return False
		if not oldProfileName in self.__config[CONFIG_PROFILES]:
			print("Profile {0:s} doesn't exist!".format(oldProfileName))
			return False

		self.MarkDirty()
		self.__config[CONFIG_PROFILES][newProfileName] = copy.deepcopy(self.__config[CONFIG_PROFILES][oldProfileName])
		return True

	def DeleteProfile(self, profileName: str) -> None:
		self.__config[CONFIG_PROFILES].pop(profileName)
		self.MarkDirty()

	def GetProfile(self, profileName: str) -> TableclothProfile:
		return self.__config[CONFIG_PROFILES][profileName]

	def GetCurrentProfileName(self) -> str:
		return self.__config[CONFIG_SETTINGS]["current-profile"]

	def GetCurrentProfile(self) -> TableclothProfile:
		if self.__config[CONFIG_SETTINGS]["assume-current-profile"]:
			return self.GetProfile(self.GetCurrentProfileName())
		else:
			print("Can't get default profile: assume-current-profile is FALSE. (The current profile is {})".format(self.GetCurrentProfileName()))
			exit(1)

	def GetProfileNames(self) -> list:
		return self.__config[CONFIG_PROFILES].keys()

	def GetDefaultJarName(self) -> str:
		#TODO: If the name is null, this should get the default constructed name
		name = self.__config[CONFIG_SETTINGS]["launch"][CONFIG_SERVER_JAR_NAME]

		# Treat empty/whitespace names as not names
		if not name or name == "" or str(name).isspace():
			return None
		# Force name to have jar at the end
		elif name[-4:] != ".jar":
			name += ".jar"

		return name

	def ToDict(self) -> dict:
		config = copy.deepcopy(self.__config)
		
		# Convert the profiles to dictionaries for JSON serialization
		profiles = {}
		for profile, settings in config[CONFIG_PROFILES].items():
			profiles[profile] = settings.ToDict()

		config[CONFIG_PROFILES] = profiles
		return config

# Base class to support other mod hosts down the line.
class ModHostService:
	def __init__(self, apiBase: str):
		self.__apiBase = apiBase

	def GetApiUrl(self):
		return self.__apiBase
	
	# Responsible for getting all the information needed to download the mod.
	def GetHostModInfo(self, gameVersion: str, modName: str, modVersion: str):
		pass

	# Used by serve-up
	def DownloadMods(self, profile: TableclothProfile):
		pass

class ModrinthHostService(ModHostService):
	def __init__(self):
		super().__init__("https://api.modrinth.com/v2/")

	def __findModVersion(self, gameVersion: str, modName: str, modVersion: str) -> dict:
		#TODO: Want to use Modrinth's search api. Should let us get this easier.
		versionResponse = requests.get(
			self.GetApiUrl() + "project/" + modName + "/version",
			params = {
				# TODO: This isn't working - gameVersion isn't
				# being properly filtered. Can't figure out why.
				'loaders' : '["fabric"]',
				'game_versions': '["{}"]'.format(gameVersion),
			})
		
		if not versionResponse.status_code == 200:
			print("Could not get version data for the mod! HTTP {}".format(versionResponse.status_code))
			return None
		
		versionData = versionResponse.json()
		
		# This helps to find the version ID of the mod.
		if (len(versionData) == 1 and
				"version_number" in versionData[0] and
				versionData[0]["version_number"] == modVersion):
			return versionData[0]
		else:
			versionList = []
			for versionInfo in versionData:
				# Grab the first version found. Modrinth returns mod versions from
				# newest to oldest (this is rare, but does happen).
				if versionInfo["version_number"] == modVersion:
					return versionInfo
				else:
					versionList.append(versionInfo["version_number"])
			return versionList

	def GetHostModInfo(self, gameVersion: str, modName: str, modVersion: str):
		modInfo = self.__findModVersion(gameVersion, modName, modVersion)

		if isinstance(modInfo, collections.abc.Sequence):
			if len(modInfo) == 0:
				print("No versions supporting this profile's Minecraft version ({}) were found!".format(gameVersion))
				return None
			else:
				print("Version wasn't found. Valid versions are:")
				print(modInfo)
				return None
		
		return {
			"project-id": modInfo["project_id"],
			"version-id": modInfo["id"],
			"files": modInfo["files"],
			# Will be used to check for updates... eventually
			"publish_date": modInfo["date_published"],
		}
	
	def DownloadMods(self, profile: TableclothProfile):
		for mod, info in profile.Mods().items():
			if not info["enabled"]:
				# TODO: I don't want to remove them because files required by multiple
				# mods may exist here. Probably need to map files to the mods that need
				# them - probably an issue for when tablecloth.lock is introduced here
				print("Skipping disabled mod [{}]. Jars associated with this mod may still be present, however.".format(mod))
				continue

			print("Downloading " + mod)
			for file in info["modrinth"]["files"]:
				modJarResponse = requests.get(file["url"]) 
				if not modJarResponse.status_code == 200:
					print("Couldn't download file for mod [{}]: HTTP {}".format(mod, modJarResponse.status_code))
					continue
				path = "mods/" + file["filename"]
				open(path, 'wb').write(modJarResponse.content)
				print("Downloaded mod file to " + path)

# Base class for all actions in tablecloth.
class TableclothActionBase:
	def __init__(self, argv: argparse.Namespace, config: TableclothConfig) -> None:
		self._config = config
		self._argv = argv

	def Perform(self) -> None:
		pass

class ProfileRequiredActionBase(TableclothActionBase):
	def __init__(self, argv: argparse.Namespace, config: TableclothConfig):
		super().__init__(argv, config)
		if argv.profile:
			self.profile = config.GetProfile(argv.profile)
		else:
			self.profile = config.GetCurrentProfile()
			if self.profile is None:
				print("config.assume-current-profile is set to FALSE. A profile must be provided")
				exit(1)

	def GetProfile(self):
		return self._config.GetProfile(self.profile.Name())

def CreateActionGroup(argparser: argparse.ArgumentParser, subparsers: argparse._SubParsersAction, groupName, groupHelp):
	parser = subparsers.add_parser(groupName, help=groupHelp)
	# Set default behavior for the group with no arguments (show help)
	parser.set_defaults(func = lambda args, config: argparser.parse_args([groupName, '-h']))
	# This creates the group itself
	return parser.add_subparsers()

def CallbackFromClass(action: type):
	return lambda argv, config: action(argv, config).Perform()

# ============================argument parser setup=============================
argparser = argparse.ArgumentParser(prog="Tablecloth MC Alpha 0.2", description="A CLI-based Minecraft Server launcher and Fabric mod installer ([WIP] commands can't be used)")
argparser.add_argument("--showResult", help="Displays the config when the command completes.", action="store_true")
argparser.add_argument("--profile", "-p", help="The name of the profile to operate on or use. Ignored by the profile actions. If omitted, will use config.current-profile if config.assume-current-profile is true.")
argparser.add_argument("--dry-run", help="[WIP] Performs a dry run and shows what the result would be without saving the config", action="store_true")
subparsers = argparser.add_subparsers()

# ==============================================================================
# PROFILE COMMANDS
# ==============================================================================
# Base class for profile-based actions. Work in progress; here to remind me
class ProfileActions:
	class __ProfileActionBase(TableclothActionBase):
		def __init__(self, argv: argparse.Namespace, config: TableclothConfig) -> None:
			super().__init__(argv, config)
			self._profileName = self._argv.profileName

	class Create(__ProfileActionBase):
		def Perform(self) -> None:
			# Check for argument values in args
			# If they're not there, ask user for them
			minecraftVersion = self._argv.minecraft or input("Enter Minecraft version:")
			fabricLoaderVersion = self._argv.fabric_loader or input("Fabric Loader version:")
			fabricInstallerVersion = self._argv.fabric_installer or input("Fabric Installer version:")

			self._config.AddProfile(self._profileName, minecraftVersion, fabricLoaderVersion, fabricInstallerVersion)

	class Copy(__ProfileActionBase):
		def Perform(self) -> None:
			self._config.CopyProfile(self._profileName, self._argv.newProfile)

	class Rename(__ProfileActionBase):
		def Perform(self) -> None:
			self._config.RenameProfile(self._profileName, self._argv.newProfileName)

	class Remove(__ProfileActionBase):
		def Perform(self) -> None:
			self._config.DeleteProfile(self._profileName)

	class List(TableclothActionBase):
		def Perform(self) -> None:
			for profile in self._config.GetProfileNames():
				print(profile)

profile_parsers = CreateActionGroup(
	argparser,
	subparsers,
	"profile",
	"Manage profiles. None of the profile commands will assume a profile, regardless of settings."
)

current_subparser = profile_parsers.add_parser("add", help="Adds a profile")
current_subparser.add_argument('profileName', metavar="Profile Name", help="The name of the profile to create", type=str)
current_subparser.add_argument('--minecraft', '-m', metavar="Minecraft Version", help='The version of Minecraft this profile uses', type=str)
current_subparser.add_argument('--fabric-loader', '-l', metavar="Fabric Loader", help="The version of the Fabric Loader this profile uses", type=str)
current_subparser.add_argument('--fabric-installer', '-i', metavar="Fabric Installer", help="The version of the Fabric installer this profile uses", type=str)
current_subparser.set_defaults(func = CallbackFromClass(ProfileActions.Create))

current_subparser = profile_parsers.add_parser("copy", help="Copies one profile to another")
current_subparser.add_argument('profileName', metavar="Profile Name", help="The name of the original profile", type=str)
current_subparser.add_argument('newProfile', metavar="New Profile Name", help="The name of the new profile", type=str)
current_subparser.set_defaults(func = CallbackFromClass(ProfileActions.Copy))

current_subparser = profile_parsers.add_parser("rename", help="Renames an existing profile")
current_subparser.add_argument('profileName', metavar="Profile Name", help="The name of the profile", type=str)
current_subparser.add_argument('newProfileName', metavar="Profile New Name", help="The new name of the profile", type=str)
current_subparser.set_defaults(func = CallbackFromClass(ProfileActions.Rename))

current_subparser = profile_parsers.add_parser("remove", help="Removes a profile")
current_subparser.add_argument('profileName', metavar="Profile Name", help="The name of the profile to remove", type=str)
current_subparser.set_defaults(func = CallbackFromClass(ProfileActions.Remove))

current_subparser = profile_parsers.add_parser("list", help="Lists all profiles")
current_subparser.set_defaults(func = CallbackFromClass(ProfileActions.List))
# ==============================================================================
# END PROFILE ACTIONS
# ==============================================================================


# ==============================================================================
# MOD ACTIONS
# ==============================================================================
class ModActions:
	class __ModActionBase(ProfileRequiredActionBase):
		def __init__(self, argv: argparse.Namespace, config: TableclothConfig) -> None:
			super().__init__(argv, config)

	class Add(__ModActionBase):
		def Perform(self) -> None:
			self.GetProfile().AddMod(self._argv.modName, self._argv.modVersion)
			#TODO: Config needs to pay attention to its profiles to mark itself dirty.
			# Set up some observer pattern there.
			self._config.MarkDirty()

	# Lists all mods in the profile.
	class List(__ModActionBase):
		def Perform(self) -> None:
			for mod in self.GetProfile().ListMods():
				print(mod)

	# Removes the mod from the profile.
	class Remove(__ModActionBase):
		def Perform(self) -> None:
			self.GetProfile().RemoveMod(self._argv.modName)
			self._config.MarkDirty()

	# Finds all profiles that use the given mod.
	class Search(TableclothActionBase):
		def Perform(self) -> None:
			profiles = self._config.GetProfileNames()
			mod = self._argv.modName
			print("Mod [{}] is found in the following profiles:".format(mod))
			for profileName in profiles:
				profile = self._config.GetProfile(profileName)
				if profile.HasMod(mod):
					print("  - " + profileName)

	# Sets the version for the mod. The mod must exist first however.
	class SetVersion(__ModActionBase):
		def Perform(self) -> None:
			self.GetProfile().UpdateMod(self._argv.modName, self._argv.modVersion)
			self._config.MarkDirty()

mod_parsers = CreateActionGroup(
	argparser,
	subparsers,
	"mod",
	"Manages mods for a profile"
)

current_subparser = mod_parsers.add_parser("add", help="Adds the mod to the profile. Doesn't download the mod, however.")
current_subparser.add_argument("modName", help="The name of the mod to add.")
# Maybe someday we want to make this optional - help the user gind what they want - but not today
current_subparser.add_argument("modVersion", help="The version of the mod to add.")
current_subparser.set_defaults(func = CallbackFromClass(ModActions.Add))

current_subparser = mod_parsers.add_parser("list", help="Lists all the mods in the profile.")
current_subparser.set_defaults(func = CallbackFromClass(ModActions.List))

current_subparser = mod_parsers.add_parser("remove", aliases=["rm"], help="Removes the mod from the profile.")
current_subparser.add_argument("modName", help="The name of the mod to remove.")
current_subparser.set_defaults(func = CallbackFromClass(ModActions.Remove))

current_subparser = mod_parsers.add_parser("search", help="Reports each profile that has the mod.")
current_subparser.add_argument("modName", help="The name of the mod to search for.")
current_subparser.set_defaults(func = CallbackFromClass(ModActions.Search))

current_subparser = mod_parsers.add_parser("set-version", aliases=["sv"], help="Sets the version of the mod.")
current_subparser.add_argument("modName", help="The name of the mod to set the version for")
current_subparser.add_argument("modVersion", help="The version of the mod.")
current_subparser.set_defaults(func = CallbackFromClass(ModActions.SetVersion))

# ==============================================================================
# END MOD ACTIONS
# ==============================================================================

class CleanupAction(TableclothActionBase):
	def __squeakyCleanup(self):
		if not self._argv.yes:
				response = ""
				while response != "y" and response != "n":
					response = input("This will remove the server jar, .fabric, and mods folders. Continue? Y/N ").lower()
				if response == "n":
					print("Aborting cleanup")
					return

		serverJar = self._config.GetDefaultJarName()
		profile = self._config.GetCurrentProfile()

		if serverJar == None:
			serverJar = SERVER_JAR_NAME_PATTERN.format(
				profile.GetMinecraftVersion(),
				profile.GetFabricLoaderVersion(),
				profile.GetFabricInstallerVersion()
			)
		if os.path.exists(serverJar):
			os.remove(serverJar)
		if os.path.exists("mods"):
			shutil.rmtree("mods")
		if os.path.exists(".fabric"):
			shutil.rmtree(".fabric")
		return

	def Perform(self) -> None:
		if self._argv.spotless:
			self.__squeakyCleanup()
		else:
			print("Cleanup is still a work in progress.")

current_subparser = subparsers.add_parser("cleanup", help="Cleans up jars related to removed and disabled mods")
current_subparser.add_argument("--spotless", help="Clean up all jars installed or created by Tablecloth", action='store_true')
current_subparser.add_argument("--yes", "-y", help="Skips the prompt when doing a spotless cleanup", action='store_true')
current_subparser.set_defaults(func=CallbackFromClass(CleanupAction))

class InitAction(TableclothActionBase):
	def Perform(self) -> None:
		if os.path.exists("tablecloth.json"):
			print("tablecloth.json already exists!")
			return
		self._config.MarkDirty()

current_subparser = subparsers.add_parser("init", help="Creates the default Tablecloth.py if one doesn't exist.")
current_subparser.set_defaults(func=CallbackFromClass(InitAction))

class LaunchAction(TableclothActionBase):
	def __craftLaunchArgs(self) -> list:
		config = self._config
		javaArgs = config.GetLaunchInfo()
		args = []

		#TODO: Ensure that these values are valid.
		if "min-ram" in javaArgs:
			print("Using {} as the minimum ram".format(javaArgs["min-ram"]))
			args.append("-Xms{}".format(javaArgs["min-ram"]))
		if "max-ram" in javaArgs:
			print("Using {} as the maximum ram".format(javaArgs["max-ram"]))
			args.append("-Xmx{}".format(javaArgs["max-ram"]))

		# At present, these must be added manually to config. Not great at all.
		for arg in javaArgs["java-args"]:
			args.append[arg]

		args += ["-jar", config.GetDefaultJarName(), "--nogui"]
		return args

	def Perform(self) -> None:
		print("Starting server...")
		complete = subprocess.run(["java"] + self.__craftLaunchArgs())
		print("Server run aborted (return code {}). Check the server logs for more info.".format(complete.returncode))

current_subparser = subparsers.add_parser("launch", help="Launches the Minecraft server")
current_subparser.set_defaults(func = CallbackFromClass(LaunchAction))

class ServeUpAction(ProfileRequiredActionBase):
	def Perform(self) -> None:
		profile = self.GetProfile()
		gameVersion = profile.GetMinecraftVersion()
		loaderVersion = profile.GetFabricLoaderVersion()
		installerVersion = profile.GetFabricInstallerVersion()

		fabricInstallerUrl = "https://meta.fabricmc.net/v2/versions/loader/{}/{}/{}/server/jar".format(gameVersion, loaderVersion, installerVersion)
		jarName = self._config.GetDefaultJarName()
		if jarName is None:
			downloadName = "fabric-server-mc.{}-loader.{}-launcher.{}.jar".format(gameVersion, loaderVersion, installerVersion)
		else:
			downloadName = jarName

		serverJar = requests.get(fabricInstallerUrl).content
		open(downloadName, 'wb').write(serverJar)

		print("Server jar created. You may need to change its permissions.")
		if not os.path.exists("mods"):
			os.mkdir("mods")

		print("Installing mods...")
		modrinthService = ModrinthHostService()
		modrinthService.DownloadMods(profile)
		print("Done!")

current_subparser = subparsers.add_parser("serve-up", help="Downloads the mods according to the desired profile")
current_subparser.set_defaults(func = CallbackFromClass(ServeUpAction))

class SetVersionAction(ProfileRequiredActionBase):
	def Perform(self) -> None:
		profile = self.GetProfile()
		if self._argv.minecraft:
			# TODO: This should go through the mods and disable the ones that are
			# incompatible.
			profile.SetMinecraftVersion(self._argv.minecraft)
			self._config.MarkDirty()
		
		if self._argv.fabric_installer:
			profile.SetFabricInstallerVersion(self._argv.fabric_installer)
			self._config.MarkDirty()

		if self._argv.fabric_loader:
			profile.SetFabricLoaderVersion(self._argv.fabric_loader)
			self._config.MarkDirty()

current_subparser = subparsers.add_parser("set-version", help="Allows you to set the versions of Minecraft and the Fabric Installer/Loader")
current_subparser.add_argument("--minecraft", "-m", help="The Minecraft version to use")
current_subparser.add_argument("--fabric-installer", "-i", help="The Fabric Installer version to use")
current_subparser.add_argument("--fabric-loader", "-l", help="The Fabric Loader version to use")
current_subparser.set_defaults(func = CallbackFromClass(SetVersionAction))

# ================================main function=================================
def main():
	if (len(sys.argv) == 1):
		argparser.parse_args(['-h'])
		return

	config = TableclothConfig()
	args = argparser.parse_args()
	try:
		args.func(args, config)
	except EOFError:
		print("Operation aborted (user input)")

	if args.showResult or args.dry_run:
		print(json.dumps(config.ToDict(), indent=2))
	if not args.dry_run and config.IsDirty():
		config.Save()

if __name__ == "__main__":
	main()
