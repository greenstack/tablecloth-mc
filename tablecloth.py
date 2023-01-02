#!/usr/bin/python3

# Tablecloth version 0.1-alpha

# ===================================LICENSE====================================
# Copyright © 2022 GreenstackJ

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

# Tablecloth is a software designed to automatically upgrade Minecraft servers
# that have been modded with Fabric from the CLI.

# Subcommands:
#
# addmod [name] [version]
#		Registers a mod for use. It doesn't perform the download, however. Run the
#		tablecloth serve-up command.
#
# cleanup
#		Checks for mods that have been removed and deletes them.
#
# config-versions [--minecraft=[versionId]] [--fabric-loader=[versionId]]
#									[--fabric-launcher=[versionId]]
#		Sets the version of the component that Tablecloth should search for.
#
# removemod [name]
#		Unregisters a mod for use. It doesn't perform the removal, however. Run
#		tablecloth cleanup to do that.
#
# serve-up
#		Downloads registered mods and updates Minecraft and Fabric.
#
# setmodver [name] --url=[url] [--version=[version]]
#		Sets the version of the mod to look for.


import argparse
import json
import os
import requests
import sys

TABLECLOTH_CONFIG_PATH = 'tablecloth.json'
CONFIG_MODS = "mods"
CONFIG_MINECRAFT_VERSION = "minecraft-version"
CONFIG_FABRIC = "fabric"
CONFIG_FABRIC_LOADER_VERSION = "loader-version"
CONFIG_FABRIC_INSTALLER_VERSION = "installer-version"
CONFIG_SERVER_JAR_NAME = "jar-name"
MODRINTH_API_BASE = "https://api.modrinth.com/v2/"
MODRINTH_PROJECT_API = MODRINTH_API_BASE + "project/{}"
MODRINTH_VERSION_API = MODRINTH_API_BASE + "project/{}/version"

def getDefaultConfig() -> dict:
	return {
		CONFIG_SERVER_JAR_NAME: None,
		CONFIG_MINECRAFT_VERSION: "1.19.3",
		CONFIG_FABRIC: {
			CONFIG_FABRIC_LOADER_VERSION: "0.14.12",
			CONFIG_FABRIC_INSTALLER_VERSION: "0.11.1",
		},
		CONFIG_MODS: {},
	}

def dumpConfig(config: dict) -> None:
	with open(TABLECLOTH_CONFIG_PATH, 'w') as configFile:
		json.dump(config, configFile)

def getConfig() -> dict:
	if (not os.path.exists(TABLECLOTH_CONFIG_PATH)):
		config = getDefaultConfig()
		# Write the default tablecloth.json file
		dumpConfig(config)
		return config

	with open(TABLECLOTH_CONFIG_PATH, 'r') as openFile:
		config = json.load(openFile)
		return config

# ============================argument parser setup=============================
argparser = argparse.ArgumentParser(description="Manage your Fabric-modded Minecraft server installation")
subparsers = argparser.add_subparsers()

# ==============================setmodver command===============================
def setModVersion(argv) -> int:
	print("Setting mod version")

# ================================mod subcommand================================
mod_subparser = subparsers.add_parser(
	'mod',
	description="Perform various operations on mod config."
)
mod_subparsers = mod_subparser.add_subparsers()

mod_add_subparser = mod_subparsers.add_parser(
	'add',
	description="Register a mod to be downloaded."
)
mod_add_subparser.add_argument("name", type=str, help="The name of the mod")
mod_add_subparser.add_argument("version", type=str, help="The version of the mod to register")

mod_add_subparser.add_argument('--download', help="Specify this flag if you want to immediately download the mod")

# ================================addmod command================================
register_mod_parser = subparsers.add_parser(
	"add-mod",
	description="Register a mod to be downloaded [DEPRECATED. Use tablecloth mod add instead.]",
	aliases=['am']
)
register_mod_parser.add_argument("name", type=str, help="The name of the mod")
register_mod_parser.add_argument("version", type=str, help="The version of the mod to download")

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

def registerMod(argv) -> int:
	if not len(sys.argv) > 2:
		register_mod_parser.parse_args(['-h'])
		return
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

	mod = {
		"name": argv.name,
		"version": argv.version,
		"modrinth":
		{
			"project-id": projectDataJson["id"],
			"version-id": version["id"], # Helps us keep it in place
			"download-url": versionFile["url"], # Gives us a link to the place
			"filename": versionFile["filename"],
			"hashes": { # Will let us know during serve-up if we need to download or not
				"sha512": versionFile["hashes"]["sha512"],
				"sha1": versionFile["hashes"]["sha1"],
			}
		}
	}

	# TODO: Make sure mod isn't already here
	# TODO: Make the mod name the key so we don't have to worry about redundant
	# additions. Should make mods easier to unregister as well.
	config[CONFIG_MODS][argv.name] = mod
	dumpConfig(config)
	print("Registered {}. Run `tablecloth serve-up` to download it.".format(argv.name))

	exit(0)

mod_add_subparser.set_defaults(func=registerMod)

def registerMod_DEPRECATED(argv):
	print("WARNING: The add-mod command is deprecated. Use mod add instead.")
	registerMod(argv)

register_mod_parser.set_defaults(func=registerMod_DEPRECATED)

# =============================mod remove command===============================
def unregisterMod(argv) -> int:
	print("Unregistering mod...")

# ===============================cleanup command================================
def cleanup(argv) -> int:
	print("cleaning up...")
	
	exit(0)

# =================================init command=================================
init_subparser = subparsers.add_parser(
	'init',
	description="Initialize Tablecloth with the default settings"
)
def init(argv) -> int:
	if os.path.exists(TABLECLOTH_CONFIG_PATH):
		print(TABLECLOTH_CONFIG_PATH + " already exists.")
		exit(1)
	print("Creating original config")
	dumpConfig(getDefaultConfig())
	print("Created config file ({})".format(TABLECLOTH_CONFIG_PATH))
init_subparser.set_defaults(func=init)

# ===============================serve-up command===============================
serve_up_subparser = subparsers.add_parser(
	'serve-up',
	description="Download the server jar and mods"
)
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

serve_up_subparser.set_defaults(func=performUpdate)

# ===========================config-versions command============================
config_versions_subparser = subparsers.add_parser(
		"config-version",
		aliases=['cv'],
		description="Configure the versions of Minecraft and the Fabric components"
)
config_versions_subparser.add_argument('--minecraft', metavar="[Minecraft Version]", type=str, help="The desired Minecraft version")
config_versions_subparser.add_argument('--fabric-loader', metavar="[Loader Version]", type=str, help="The version of the Fabric loader to use")
config_versions_subparser.add_argument('--fabric-installer', metavar="[Installer Version]", type=str, help="The version of the Fabric installer to use")

def configVersions(args) -> int:
	if not len(sys.argv) > 2:
		config_versions_subparser.parse_args(['-h'])
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

	dumpConfig(config)

	exit(0)

config_versions_subparser.set_defaults(func=configVersions)

# ================================main function=================================
def main():
	if (len(sys.argv) == 1):
		argparser.parse_args(['-h'])
		return

	args = argparser.parse_args()
	args.func(args)

if __name__ == "__main__":
	main()
