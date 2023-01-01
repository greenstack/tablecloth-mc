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
# that have been modded with Fabric from the CLI. To help with this, you can
# (and should!) register mods using this script.

# TODO: Have Tablecloth use the Modrinth API to download the mods.

# Subcommands:
#
# addmod [name] --url=[url] [--version=[version]]
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
CONFIG_MINECRAFT_VERSION = "minecraft-version"
CONFIG_FABRIC = "fabric"
CONFIG_FABRIC_LOADER_VERSION = "loader-version"
CONFIG_FABRIC_INSTALLER_VERSION = "installer-version"
CONFIG_SERVER_JAR_NAME = "jar-name"

def getDefaultConfig() -> dict:
	return {
		"mods": {},
		"minecraft-version": "1.19.3",
		"fabric": {
			"loader-version": "0.14.12",
			"installer-version": "0.11.1"
		},
		"jar-name": None
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

# ================================addmod command================================
def registerMod(argv) -> int:
	print("Registering mod...")
	
	exit(0)

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
	print("Creating original config")
	dumpConfig(getConfig())
	print("Created config file ({})".format(TABLECLOTH_CONFIG_PATH))
init_subparser.set_defaults(func=init)

# ==============================removemod command===============================
def unregisterMod(argv) -> int:
	print("Unregistering mod...")
	
	exit(0)

# ==============================setmodver command===============================
def setModVersion(argv) -> int:
	print("Setting mod version")
	
	exit(0)

# ===============================serve-up command===============================
serve_up_subparser = subparsers.add_parser(
	'serve-up',
	description="Download the server jar and mods"
)

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
	if not (args.minecraft or args.fabric_loader or args.fabric_installer):
		config_versions_subparser.parse_args(['-h'])
		#print("Must define a version for either --minecraft, --fabric-loader, or --fabric-installer")
		exit(1)

	config = getConfig()
	if (args.minecraft):
		config[CONFIG_MINECRAFT_VERSION] = args.minecraft
	if (args.fabric_loader):
		config[CONFIG_FABRIC][CONFIG_FABRIC_LOADER_VERSION] = args.fabric_loader
	if (args.fabric_installer):
		config[CONFIG_FABRIC][CONFIG_FABRIC_INSTALLER_VERSION] = args.fabric_installer

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
