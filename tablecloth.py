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
import copy
import json
import os
import requests
import subprocess
import sys

TABLECLOTH_CONFIG_PATH = 'tablecloth.json'

DEFAULT_MINECRAFT_VERSION = "1.19.4"
DEFAULT_FABRIC_LOADER = "0.14.12"
DEFAULT_FABRIC_INSTALLER = "0.11.1"

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
	def __init__(self, mcVer:str = DEFAULT_MINECRAFT_VERSION, fabricLoaderVer:str = DEFAULT_FABRIC_LOADER, fabricInstallerVer:str = DEFAULT_FABRIC_INSTALLER) -> None:
		self.__minecraftVersion = mcVer
		self.__fabricLoaderVersion = fabricLoaderVer
		self.__fabricInstallerVersion = fabricInstallerVer
		self.__mods = {}
		self.__jarName = None
		self.__javaPath = None
		self.__javaArgs = []

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

	def FromDict(data):
		#todo: data validation
		profile = TableclothProfile(
			data['minecraft']['version'],
			data["fabric"]["loader"],
			data["fabric"]["installer"]
		)

		for mod, settings in data["mods"].items():
			profile.__deserializeMod(mod, settings["version"], settings["modrinth"])

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
		
	def __deserializeMod(self, modName, version, hostInfo) -> None:
		self.__mods[modName] = {
			"version": version,
			"modrinth": hostInfo
		}

	def AddMod(self, modName, version) -> None:
		self.__mods[modName] = {
			"version": version,
			"enabled": True,
			"modrinth": ModrinthHostService().GetHostModInfo(
				self.GetMinecraftVersion(),
				modName,
				version
			),
		}

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
				"default": TableclothProfile()
			},
			CONFIG_SETTINGS: {
				"assume-current-profile": True,
				"current-profile": "default",
				"launch": {
					"jar-name": None,
					"java-path": None,
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
			return

		self.__config = TableclothConfig.Load(TABLECLOTH_CONFIG_PATH)

	def Load(filePath) -> dict:
		with open(filePath, 'r') as configFile:
			config = json.load(configFile)
		profiles = {}
		for profile, data in config[CONFIG_PROFILES].items():
			profiles[profile] = TableclothProfile.FromDict(data)
		config.pop(CONFIG_PROFILES)
		config[CONFIG_PROFILES] = profiles
		return config

	def Save(self):
		with open(TABLECLOTH_CONFIG_PATH, 'w') as configFile:
			json.dump(self.ToDict(), configFile)

	def AddProfile(self, profileName: str, mcVersion: str, fabLoaderVer: str, fabInstallerVer: str):
		self.__config[CONFIG_PROFILES][profileName] = TableclothProfile(mcVersion, fabLoaderVer, fabInstallerVer)

	def RenameProfile(self, oldProfileName: str, newProfileName: str):
		self.__config[CONFIG_PROFILES][newProfileName] = self.__config[CONFIG_PROFILES][oldProfileName]
		del self.__config[CONFIG_PROFILES][oldProfileName]

	def CopyProfile(self, oldProfileName: str, newProfileName: str) -> bool:
		if newProfileName in self.__config[CONFIG_PROFILES]:
			print("Profile {0:s} already exists!".format(newProfileName))
			return False
		if not oldProfileName in self.__config[CONFIG_PROFILES]:
			print("Profile {0:s} doesn't exist!".format(oldProfileName))
			return False

		self.__config[CONFIG_PROFILES][newProfileName] = copy.deepcopy(self.__config[CONFIG_PROFILES][oldProfileName])
		return True

	def DeleteProfile(self, profileName: str) -> None:
		self.__config[CONFIG_PROFILES].pop(profileName)

	def GetProfile(self, profileName: str) -> TableclothProfile:
		return self.__config[CONFIG_PROFILES][profileName]

	def GetCurrentProfileName(self) -> str:
		return self.__config[CONFIG_SETTINGS]["current-profile"]

	def GetCurrentProfile(self) -> TableclothProfile:
		if self.__config[CONFIG_SETTINGS]["assume-current-profile"]:
			return self.__config[CONFIG_PROFILES][self.GetCurrentProfileName()]

	def GetProfileNames(self) -> list:
		return self.__config[CONFIG_PROFILES].keys()

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
				"query": {
					"loaders": ["fabric"],
					"game_versions": [gameVersion],
				}
			})
		
		if not versionResponse.status_code == 200:
			print("Could not get version data for the mod! HTTP {}".format(versionResponse.status_code))
			return {}

		versionData = versionResponse.json()

		# This helps to find the version ID of the mod.
		if len(versionData) == 1:
			return versionData[0]
		else:
			versionList = []
			for versionInfo in versionData:
				if versionInfo["version_number"] == modVersion:
					return versionInfo
				else:
					versionList.append(versionInfo["version_number"])
			return versionList

	def GetHostModInfo(self, gameVersion: str, modName: str, modVersion: str):
		modInfo = self.__findModVersion(gameVersion, modName, modVersion)

		return {
			"project-id": modInfo["project_id"],
			"version-id": modInfo["id"],
			"files": modInfo["files"],
			# Will be used to check for updates... eventually
			"publish_date": modInfo["date_published"],
		}
	
	def DownloadMods(self, profile: TableclothProfile):
		for mod, info in profile.Mods().items():
			print("Downloading " + mod)
			for file in info["modrinth"]["files"]:
				modJarResponse = requests.get(file["url"]) 
				if not modJarResponse.status_code == 200:
					# TODO: Better name
					print("Couldn't download file for mod {mod.name}")
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
		return self._config.GetProfile(self._profileName)

def CreateActionGroup(argparser: argparse.ArgumentParser, subparsers: argparse._SubParsersAction, groupName, groupHelp):
	parser = subparsers.add_parser(groupName, help=groupHelp)
	# Set default behavior for the group with no arguments (show help)
	parser.set_defaults(func = lambda args, config: argparser.parse_args([groupName, '-h']))
	# This creates the group itself
	return parser.add_subparsers()

def CallbackFromClass(action: type):
	return lambda argv, config: action(argv, config).Perform()

# ============================argument parser setup=============================
argparser = argparse.ArgumentParser(prog="Tablecloth MC Alpha 0.2", description="A CLI-based Minecraft Server launcher and Fabric mod installer ([WIP] commands can't be used)", epilog="At present, config isn't saved. Tablecloth Alpha 0.2 isn't production ready yet.")
argparser.add_argument("--showResult", help="Displays the config when the command completes.", action="store_true")
argparser.add_argument("--profile", "-p", help="The name of the profile to operate on or use. Ignored by the profile actions. If omitted, will use config.current-profile if config.assume-current-profile is true.")
argparser.add_argument("--dry-run", help="[WIP] Performs a dry run and shows what the result would be without saving the config", action="store_true")
subparsers = argparser.add_subparsers()

# ==============================================================================
# PROFILE COMMANDS
# ==============================================================================
# Base class for profile-based actions. Work in progress; here to remind me
class ProfileActionBase(TableclothActionBase):
	def __init__(self, argv: argparse.Namespace, config: TableclothConfig) -> None:
		super().__init__(argv, config)
		self._profileName = self._argv.profileName

class CreateProfileAction(ProfileActionBase):
	def Perform(self) -> None:
		# Check for argument values in args
		# If they're not there, ask user for them
		minecraftVersion = self._argv.mcversion or input("Enter Minecraft version:")
		fabricLoaderVersion = self._argv.fabricloader or input("Fabric Loader version:")
		fabricInstallerVersion = self._argv.fabricinstaller or input("Fabric Installer version:")

		self._config.AddProfile(self._profileName, minecraftVersion, fabricLoaderVersion, fabricInstallerVersion)

class CopyProfileAction(ProfileActionBase):
	def Perform(self) -> None:
		self._config.CopyProfile(self._profileName, self._argv.newProfile)

class RenameProfileAction(ProfileActionBase):
	def Perform(self) -> None:
		self._config.RenameProfile(self._profileName, self._argv.newProfileName)

class RemoveProfileAction(ProfileActionBase):
	def Perform(self) -> None:
		self._config.DeleteProfile(self._profileName)

class ListProfilesAction(TableclothActionBase):
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
current_subparser.add_argument('--mcversion', metavar="Minecraft Version", help='The version of Minecraft this profile uses', type=str)
current_subparser.add_argument('--fabricloader', metavar="Fabric Loader", help="The version of the Fabric Loader this profile uses", type=str)
current_subparser.add_argument('--fabricinstaller', metavar="Fabric Installer", help="The version of the Fabric installer this profile uses", type=str)
current_subparser.set_defaults(func = CallbackFromClass(CreateProfileAction))

current_subparser = profile_parsers.add_parser("copy", help="Copies one profile to another")
current_subparser.add_argument('profileName', metavar="Profile Name", help="The name of the original profile", type=str)
current_subparser.add_argument('newProfile', metavar="New Profile Name", help="The name of the new profile", type=str)
current_subparser.set_defaults(func = CallbackFromClass(CopyProfileAction))

current_subparser = profile_parsers.add_parser("rename", help="Renames an existing profile")
current_subparser.add_argument('profileName', metavar="Profile Name", help="The name of the profile", type=str)
current_subparser.add_argument('newProfileName', metavar="Profile New Name", help="The new name of the profile", type=str)
current_subparser.set_defaults(func = CallbackFromClass(RenameProfileAction))

current_subparser = profile_parsers.add_parser("remove", help="Removes a profile")
current_subparser.add_argument('profileName', metavar="Profile Name", help="The name of the profile to remove", type=str)
current_subparser.set_defaults(func = CallbackFromClass(RemoveProfileAction))

current_subparser = profile_parsers.add_parser("list", help="Lists all profiles")
current_subparser.set_defaults(func = CallbackFromClass(ListProfilesAction))
# ==============================================================================
# END PROFILE ACTIONS
# ==============================================================================


# ==============================================================================
# MOD ACTIONS
# ==============================================================================
class ModActionBase(ProfileRequiredActionBase):
	def __init__(self, argv: argparse.Namespace, config: TableclothConfig) -> None:
		super().__init__(argv, config)

class AddModAction(ModActionBase):
	def Perform(self) -> None:
		self.GetProfile().AddMod(self._argv.modName, self._argv.modVersion)

class ListModsAction(ModActionBase):
	def Perform(self) -> None:
		for mod in self.GetProfile().ListMods():
			print(mod)

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
current_subparser.set_defaults(func = CallbackFromClass(AddModAction))

current_subparser = mod_parsers.add_parser("list", help="Lists all the mods in the profile.")
current_subparser.set_defaults(func = CallbackFromClass(ListModsAction))

current_subparser = mod_parsers.add_parser("remove", help="[WIP] Removes the mod from the profile.")
current_subparser.add_argument("modName", help="The name of the mod to remove.")

current_subparser = mod_parsers.add_parser("find", help="[WIP] Reports each profile that has the mod.")
current_subparser.add_argument("modName", help="The name of the mod to search for.")

current_subparser = mod_parsers.add_parser("setver", help="[WIP] Sets the version of the mod.")
current_subparser.add_argument("modVersion", help="The version of the mod.")

# ==============================================================================
# END MOD ACTIONS
# ==============================================================================

class LaunchAction(TableclothActionBase):
	def Perform(self) -> None:
		subprocess.call([
			"java",
		])

current_subparser = subparsers.add_parser("launch", help="Launches the Minecraft server")
current_subparser.set_defaults(func = CallbackFromClass(LaunchAction))

class ServeUpAction(ProfileRequiredActionBase):
	def Perform(self) -> None:
		profile = self._config.GetCurrentProfile()
		gameVersion = profile.GetMinecraftVersion()
		loaderVersion = profile.GetFabricLoaderVersion()
		installerVersion = profile.GetFabricInstallerVersion()

		fabricInstallerUrl = "https://meta.fabricmc.net/v2/versions/loader/{}/{}/{}/server/jar".format(gameVersion, loaderVersion, installerVersion)
		downloadName = "fabric-server-mc.{}-loader.{}-launcher.{}.jar".format(gameVersion, loaderVersion, installerVersion)

		serverJar = requests.get(fabricInstallerUrl).content
		open(downloadName, 'wb').write(serverJar)

		print("Server jar created. You may need to change its permissions.")
		if not os.path.exists("mods"):
			os.mkdir("mods")

		print("Installing mods...")
		modrinthService = ModrinthHostService()
		modrinthService.DownloadMods(profile)
		print("Done!")

current_subparser = subparsers.add_parser("serve-up", help="[WIP] Downloads the mods according to the desired profile")
current_subparser.set_defaults(func = CallbackFromClass(ServeUpAction))

def cfgSetModVersion(config: dict, modName: str, versionId: str, modVersionId: str, versionInfo: dict) -> bool:
	if not config[CONFIG_MODS][modName]:
		return False

	modConfig = config[CONFIG_MODS][modName]
	modConfig[CONFIG_MOD_VERSION] = versionId
	modrinthConfig = modConfig[CONFIG_MOD_MODRINTH]
	modrinthConfig[CONFIG_MOD_MODRINTH_VERSION_ID] = modVersionId
	modrinthConfig[CONFIG_MOD_MODRINTH_DOWNLOAD_URL] = versionInfo["url"]
	modrinthConfig[CONFIG_MOD_MODRINTH_FILENAME] = versionInfo["filename"]
	modrinthConfig[CONFIG_MOD_MODRINTH_HASHES][CONFIG_MOD_MODRINTH_HASHES_SHA512] = versionInfo["hashes"]["sha512"]
	modrinthConfig[CONFIG_MOD_MODRINTH_HASHES][CONFIG_MOD_MODRINTH_HASHES_SHA1] = versionInfo["hashes"]["sha1"]
	return True

# ===============================serve-up command===============================

#TODO: Add a --clean param that cleans the mods folder before doing the download
#TODO: Add a --dry-run param that will show the user what this command will do

def performUpdate(args) -> int:	
	config = getConfig()
	
	mcVer = config.get("minecraft-version")
	fabricConfig = config.get("fabric")
	loaderVer = fabricConfig.get("loader-version")
	installerVer = fabricConfig.get("installer-version")

	installerUrl = "https://meta.fabricmc.net/v2/versions/loader/{}/{}/{}/server/jar".format(mcVer, loaderVer, installerVer)
	
	if (config.get(CONFIG_SERVER_JAR_NAME)):
		serverJarName = config.get(CONFIG_SERVER_JAR_NAME)
	else:
		serverJarName = "fabric-server-mc.{}-loader.{}-launcher.{}.jar".format(mcVer, loaderVer, installerVer)

	print("Getting fabric server jar from " + installerUrl)
	print('Naming server jar "' + serverJarName + '"')

	# TODO: Verify that things went right
	serverJar = requests.get(installerUrl).content
	open(serverJarName, 'wb').write(serverJar)

	print("Server jar created. You will need to manually change its properties.")
	
	if not os.path.exists("mods"):
		os.mkdir("mods")

	print("Installing mods...")
	for mod in config.get(CONFIG_MODS).values():
		print("Downloading {} version {}".format(mod["name"], mod["version"]))
		serverJarResponse = requests.get(mod["modrinth"]["download-url"])
		if not serverJarResponse.status_code == 200:
			print("Could not download the mod (HTTP {})".format(serverJarResponse.status_code))
			continue
		path = "mods/" + mod["modrinth"]["filename"]
		open(path, 'wb').write(serverJarResponse.content)
		print("Mod saved to " + path)

	exit(0)


# ===========================config-versions command============================
def configVersions(args, config: TableclothConfig) -> int:
	if not len(sys.argv) > 2:
		#config_versions_subparser.parse_args(['-h'])
		#print("Must define a version for either --minecraft, --fabric-loader, or --fabric-installer")
		exit(1)

	config = getConfig()
	if (args.minecraft):
		config[CONFIG_MINECRAFT_VERSION] = args.minecraft
		print("Set Minecraft version to " + args.minecraft)
	if (args.fabric_loader):
		config[CONFIG_FABRIC][CONFIG_FABRIC_LOADER_VERSION] = args.fabric_loader
		print("Set Fabric loader version to" + args.fabric_loader)
	if (args.fabric_installer):
		config[CONFIG_FABRIC][CONFIG_FABRIC_INSTALLER_VERSION] = args.fabric_installer
		print("Set Fabric installer version to " + args.fabric_installer)

	config.Save()

	exit(0)


# ================================main function=================================
def main():
	if (len(sys.argv) == 1):
		argparser.parse_args(['-h'])
		return

	print("Tablecloth Alpha 0.2")

	#search = ModrinthHostService()
	#modId = search.FindMod("phosphor")["id"]
	#version = search.FindModVersion("1.19.4", modId, "mc1.19.x-0.8.1")

	config = TableclothConfig()
	args = argparser.parse_args()
	args.func(args, config)
	if args.showResult or args.dry_run:
		print(json.dumps(config.ToDict(), indent=2))
	if not args.dry_run:
		config.Save()

if __name__ == "__main__":
	main()
