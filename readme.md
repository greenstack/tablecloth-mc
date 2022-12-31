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

# License
Tablecloth MC is published under the MIT License.
