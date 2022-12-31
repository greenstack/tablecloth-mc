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
# help
#  Lets you know more about the program.
#
# addmod [name] --url=[url] [--version=[version]]
#		Registers a mod for use. It doesn't perform the download, however. Run the
#		tablecloth serve-up command.
#
# cleanup
#		Checks for mods that have been removed and deletes them.
#
# fabric [--loader=[version]] [--installer=[version]]
#		Sets the version for the fabric loader and installer. At least one of these
#		arguments is required.
#
# removemod [name]
#		Unregisters a mod for use. It doesn't perform the removal, however. Run
#		tablecloth cleanup to do that.
#
# serve-up
#		Downloads registered mods and updates Minecraft and Fabric.
#
# setmodver [name] --url=[url] [--version=[version]]
#
# update-mc --version=[versionId]
#		Updates the url from which the Minecraft server jar will be obtained.

import getopt
import json
import requests
import sys

def describeMeIfNoArgs(argv, aboutMe):
	if (len(argv) == 0):
		aboutMe()
		return True
	return False

def getConfig() -> dict:
	with open('tablecloth.json', 'r') as openFile:
		json_object = json.load(openFile)
		return json_object

# ================================about command=================================
def about() -> int:
	print("About Tablecloth")
	registerMod([])
	cleanup([])
	unregisterMod([])
	performUpdate([])
	updateMinecraft([])
	exit(0)

# ================================addmod command================================
def registerMod(argv) -> int:
	def aboutMe():
		print("removemod")
	if (describeMeIfNoArgs(argv, aboutMe)): return 0
	
	print("Registering mod...")
	
	exit(0)

# ===============================cleanup command================================
def cleanup(argv) -> int:
	def aboutMe():
		print("cleanup")
	if (describeMeIfNoArgs(argv, aboutMe)): return 0
	
	print("cleaning up...")
	
	exit(0)

# ==============================removemod command===============================
def unregisterMod(argv) -> int:
	def aboutMe():
		print("removemod")
	if (describeMeIfNoArgs(argv, aboutMe)): return 0

	print("Unregistering mod...")
	
	exit(0)

# ==============================setmodver command===============================
def setModVersion(argv) -> int:
	def aboutMe():
		print("setmodver")
	if (describeMeIfNoArgs(argv, aboutMe)): return 0

	print("Setting mod version")
	
	exit(0)

# ===============================serve-up command===============================
def performUpdate(argv) -> int:

	def aboutMe():
		print("serve-up: downloads registers mods and updates minecraft and fabric (if needed)")

	if (describeMeIfNoArgs(argv, aboutMe)): return 0
	
	print("Updating server")
	
	exit(0)

# ==============================update-mc command===============================
def updateMinecraft(argv) -> int:
	def aboutMe():
		print("update-mc")

	config = getConfig()
	
	mcVer = config.get("minecraft-version")
	fabricConfig = config.get("fabric")
	loaderVer = fabricConfig.get("loader-version")
	installerVer = fabricConfig.get("installer-version")

	installerUrl = "https://meta.fabricmc.net/v2/versions/loader/{}/{}/{}/server/jar".format(mcVer, loaderVer, installerVer)
	
	if (config.get("jarName")):
		serverJarName = config.get("jarName")
	else:
		serverJarName = "fabric-server-mc.{}-loader.{}-launcher.{}.jar".format(mcVer, loaderVer, installerVer)

	print("Getting fabric server jar from " + installerUrl)
	print('Naming server jar "' + serverJarName + '"')

	# TODO: Verify that things went right
	serverJar = requests.get(installerUrl).content
	open(serverJarName, 'wb').write(serverJar)

	print("Server jar created. You will need to manually change its permissions, owner, group, etc. manually.")

	exit(0)

# ================================main function=================================
def main():
	if (len(sys.argv) == 1):
		return about()

	mainArg = sys.argv[1]
	argv = sys.argv[2:]
	switcher = {
		"addmod": registerMod,
		"cleanup": cleanup,
		"removemod": unregisterMod,
		"setmodver": setModVersion,
		"serve-up": performUpdate,
		"update-mc": updateMinecraft,
		"help": about,
	}

	command = switcher.get(mainArg, about)
	command(argv)

	#opts, args = getopt.getopt(argv, "addMod:y:")
	

if __name__ == "__main__":
	main()
