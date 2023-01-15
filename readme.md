# Tablecloth MC
Tablecloth MC (or more simply, just "Tablecloth") is a single Python file
designed to help you manage your [Fabric](https://fabricmc.net)-modded
[Minecraft](https://www.minecraft.net/) server from the CLI.

Tablecloth is still in **very early alpha**.

# Installation
I recommend that you download the raw `tablecloth.py` file and place it in the
directory you'll be running your Minecraft server in. Alternatively, you could
create a symlink in that directory that points to where you've cloned this repo. 
Either way, the repository comes with a `.gitignore` that will ignore all your 
Minecraft-specific folders, so it is - in theory - safe to store this repo and
your Minecraft instance in the same folder. I still strongly discourage this,
however.

After you run Tablecloth for the first time, it will create a file called
`tablecloth.json`. This is the configuration file that Tablecloth uses. You can
edit it yourself or you can use Tablecloth to manage it as well. _**NOTE** that
this functionality is still forthcoming._

# Subcommands
## config-version
Configure the versions of Minecraft and the Fabric components

## mod
Perform various operations on registered mods.

### add
Add the given mod. If the mod is already registered, this command will fail.

### set-ver
Set the version for the mod. If the mod can't be found on Modrinth, the command
will fail. It will also fail if the mod hasn't already been downloaded.

### remove
Unregisters the given mod.

## serve-up
Download the server jar and mods

# Roadmap
 - Add automated testing
 - Add a `tablecloth.lock.json` file to help make downloading more efficient.
 - Threading to download multiple mods at once?

# License
Tablecloth MC is published under the MIT License.
