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

	def SetFabricLoaderVersion(self, fabricLoaderVersion: str) -> None:
		self.__fabricLoaderVersion = fabricLoaderVersion

	def FromDict(data):
		#todo: data validation
		profile = TableclothProfile(
			data['minecraft']['version'],
			data["fabric"]["loader"],
			data["fabric"]["installer"]
		)

		for mod, settings in data["mods"].items():
			profile.AddMod(mod, settings["version"], settings["modrinth"])

		profile.SetJarName(data["overrides"]["jar-name"])
		profile.SetJavaPath(data["overrides"]["java-path"])
		profile.__javaArgs = data["overrides"]["java-args"]

		return profile

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

	def AddMod(self, modName, version, modrinthInfo) -> None:
		self.__mods[modName] = {
			"version": version,
			"modrinth": modrinthInfo,
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
			"profiles": {
				"default": TableclothProfile()
			},
			"settings": {
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

	def GetProfile(self, profileName: str) -> TableclothProfile:
		return self.__config[CONFIG_PROFILES][profileName]

	def ToDict(self) -> dict:
		config = copy.deepcopy(self.__config)
		
		# Convert the profiles to dictionaries for JSON serialization
		profiles = {}
		for profile, settings in config[CONFIG_PROFILES].items():
			profiles[profile] = settings.ToDict()

		config[CONFIG_PROFILES] = profiles
		return config

# Base class for all actions in tablecloth.
class TableclothActionBase:
	def __init__(self, argv: argparse.Namespace, config: TableclothConfig) -> None:
		self._config = config
		self._argv = argv

	def Perform(self) -> None:
		pass

# Base class for profile-based actions. Work in progress; here to remind me
class ProfileActionBase(TableclothActionBase):
	def __init__(self, argv: argparse.Namespace, config: TableclothConfig) -> None:
		super().__init__(argv, config)
		self._profileName = self._argv.profileName

class CreateProfileAction(ProfileActionBase):
	def __init__(self, argv: argparse.Namespace, config: TableclothConfig) -> None:
		super().__init__(argv, config)

	def Perform(self) -> None:
		# Check for argument values in args
		# If they're not there, ask user for them
		minecraftVersion = self._argv.mcversion or input("Enter Minecraft version:")
		fabricLoaderVersion = self._argv.fabricloader or input("Fabric Loader version:")
		fabricInstallerVersion = self._argv.fabricinstaller or input("Fabric Installer version:")

		self._config.AddProfile(self._profileName, minecraftVersion, fabricLoaderVersion, fabricInstallerVersion)

class CopyProfileAction(ProfileActionBase):
	def __init__(self, argv:argparse.Namespace, config: TableclothConfig) -> None:
		super().__init__(argv, config)

	def Perform(self) -> None:
		self._config.CopyProfile(self._profileName, self._argv.newProfile)

def CallbackFromClass(action: type):
	return lambda argv, config: action(argv, config).Perform()

# ============================argument parser setup=============================
argparser = argparse.ArgumentParser(prog="Tablecloth MC", description="A CLI-based Minecraft Server launcher and Fabric mod installer")
subparsers = argparser.add_subparsers()

current_subparser = subparsers.add_parser("profile", help="Manage profiles")
current_subparser.set_defaults(func = lambda args, config: argparser.parse_args(["profile", "-h"]))
profile_parsers = current_subparser.add_subparsers()

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

# ================================mod subcommand================================

def addCommonModParameters(parser, addDownload: bool) -> None:
	parser.add_argument("name", type=str, help="The name of the mod")
	parser.add_argument("version", type=str, help="The version of the mod")
	if addDownload:
		parser.add_argument('--download', help="Specify this flag if you want to immediately download the mod")

# ================================addmod command================================

def findMod(modName: str) -> dict:
	projectRequest = requests.get(MODRINTH_PROJECT_API.format(modName))
	if not projectRequest.status_code == 200:
		print("Could not retrieve project {}: HTTP {}".format(modName, projectRequest.status_code))
		exit(projectRequest.status_code)
	return projectRequest.json()

def findModVersion(modName: str, modVersion: str) -> dict:
	config = getConfig()

	versionResponse = requests.get(MODRINTH_VERSION_API.format(modName),
		params = {
			"loaders": ["fabric"],
			"game_versions": [config[CONFIG_MINECRAFT_VERSION]],
		}
	)
	if (not versionResponse.status_code == 200):
		print("Could not get version data for the mod! HTTP {}".format(versionResponse.status_code))
		exit(versionResponse.status_code)
	
	versionData = versionResponse.json()
	
	if len(versionData) == 1:
		version = versionData[0]
	else:
		for versionInfo in versionData:
			if versionInfo["version_number"] == modVersion:
				version = versionInfo
				break
	return version

def addModToConfig(config: dict, modName: str, modInfo: dict, overwrite: bool) -> bool:
	if modName in config[CONFIG_MODS].keys() and not overwrite:
		return False

	config[CONFIG_MODS][modName] = {
		CONFIG_MOD_NAME: modName,
		CONFIG_MOD_VERSION: "",
		CONFIG_MOD_MODRINTH: {
			CONFIG_MOD_MODRINTH_PROJECT_ID: modInfo["id"],
			CONFIG_MOD_MODRINTH_VERSION_ID: "",
			CONFIG_MOD_MODRINTH_DOWNLOAD_URL: "",
			CONFIG_MOD_MODRINTH_FILENAME: "",
			CONFIG_MOD_MODRINTH_HASHES: {
				CONFIG_MOD_MODRINTH_HASHES_SHA512: "",
				CONFIG_MOD_MODRINTH_HASHES_SHA1: "",
			}
		}
	}
	return True

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

def registerMod(argv) -> int:
	print("Searching for {} version {}".format(argv.name, argv.version))

	projectDataJson = findMod(argv.name)

	print("Found {} (project id {}) on Modrinth".format(argv.name, projectDataJson["id"]))
	
	# 1. GET /project/slug/version (be sure to put the minecraft-version in the 
	# 		query to get only versions that we can run and that loaders is set to fabric)
	# 2. Iterate over them. Check if version_number is the same
	# 3. Iterate over each version's game_versions to make sure it matches
	# 4. If it does, then go to that version's files key.
	# 5. In that version's files key, iterate over the array. Try to find the
	#			primary file (key: "primary"; it will be true) and get the url; if it's
	#			the only one, use that.
	
	config = getConfig()

	version = findModVersion(argv.name, argv.version)

	print("Found version {} for the mod!".format(argv.version))
	
	for file in version["files"]:
		if file["primary"]:
			versionFile = file
		else:
			versionFile = file

	success = addModToConfig(config, argv.name, projectDataJson, False)
	if not success:
		print("Did not register the mod.")
		exit(1)
	cfgSetModVersion(config, argv.name, argv.version, version["id"], versionFile)
	
	dumpConfig(config)
	print("Registered {}. Run `tablecloth serve-up` to download it.".format(argv.name))

	exit(0)

# ==============================setmodver command===============================

def setModVersion(argv):
	print("Setting mod version")
# =============================mod remove command===============================
# TODO: Add positional arugment --remove to uninstall the mod immediately

def unregisterMod(argv) -> int:
	config = getConfig()

	if not argv.name in config[CONFIG_MODS].keys():
		print("Mod {} isn't registered".format(argv.name))
		exit(1)

	config[CONFIG_MODS].pop(argv.name)

	dumpConfig(config)
	print("Removed {}".format(argv.name))

# ===============================cleanup command================================
def cleanup(argv) -> int:
	print("cleaning up...")
	
	exit(0)

# =================================init command=================================
def init(argv) -> int:
	if os.path.exists(TABLECLOTH_CONFIG_PATH):
		print(TABLECLOTH_CONFIG_PATH + " already exists.")
		exit(1)
	print("Creating original config")
	dumpConfig(getDefaultConfig())
	print("Created config file ({})".format(TABLECLOTH_CONFIG_PATH))

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

	config = TableclothConfig()
	args = argparser.parse_args()
	args.func(args, config)
	print(json.dumps(config.ToDict(), indent=2))

if __name__ == "__main__":
	main()
