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
edit it yourself or you can use Tablecloth to manage it as well.

# Settings
At present, these settings can only be modified manually (except current-profile). Items with \* haven't been implemented yet.

 - **Assume Current Profile**: Sets whether Tablecloth should assume that the currently set profile is the profile to execute on. If false, then each command must identify which profile it's using.
 - **Current Profile**: The name of the current profile.
 - **Launch**\*: Parameters for launching the server using Tablecloth. This feature is a wishlist item that I'm just listing here before I can put it in as an issue on GitHub.
   - **Jar Name**: The name of the Jar to launch. If null, uses the default jar.
	 - **Java Path**\*: The path to the Java executable. If null, uses the system value for Java.
	 - **Java Args**: An array of args to pass to Java.
 - **Validation**\*: Settings to validate the integrity of downloaded files.
   - **Hashes**\*: Ensures that the hashes match those reported by Modrinth.
	 - **Size**\*: Ensures that the file size matches that reported by Modrinth.

# Actions
Notes:
 - All parameters without `--` are required for the action.
 - Any action marked with `*` is a planned feature.
 - If `--profile` isn't provided and `assume-current-profile` is `true`, then the operations will be performed on the `current-profile`. The exception to this is the `profile` actions. If `assume-current-profile` is false, the user must use either `--current-profile` or pass in a specific profile name.

## `cleanup`
Checks for mods that have been removed and deletes them (eventually). For now,
this will only work with the `--spotless` flag.

**Parameters**
 - Optional:
   - `--spotless`: Deletes the mods and the server jar, not just removed mods. Passing `--yes` or `-y` will skip the prompt.

**Parameters**  
None for now.

## `init`
Creates `tablecloth.json` with default configuration. If configuration doesn't exist, then the other commands may create it and run just fine. This command won't do anything if `tablecloth.json` doesn't exist.

## `launch`
Starts the Minecraft Server. This will always use the default profile.

## `mod`
Provides actions for working with mods in a profile.

If the mod name is provided as the only argument, this action will give all relevant data.

### `mod add`
Adds the mod to the profile (but doesn't add the jar file yet).

**Parameters**
 - Required:
   - Mod Name: The name of the mod to look for.
   - Mod Version: The version of the mod to use.

### `mod list`
Prints all mods that are a part of the profile.

**Parameters**  
None.

### `mod remove`
Removes the specified mod from the profile (but doesn't remove the mod jar itself).

**Parameters**
 - Required:
   - Mod Name: The name of the mod to remove.

### `mod search`
Reports all profiles that have the mod.

**Parameters**
 - Required:
   - Mod Name: The name of the mod to look for.

### `mod set-version`
Sets the mod's version.

**Parameters**
 - Required:
   - Mod Name: The name of the mod to set the version for.
   - Mod Version: The version of the mod to use.

## `profile`
Manages profiles stored by tablecloth. None of these commands will assume a default profile, regardless of settings.

### `profile add`
Adds a new profile, taking the user through a wizard to put in the required parameters.

### `profile copy`
Creates a new profile based on an existing profile.

**Parameters**  
 - Positional:
    - `source-profile`: The name of the profile to copy.
		- `destination-profile`: The name of the new profile.

### `profile list`
Lists all profiles.

### `profile override`
Allows you to set a launch override for the profile.

**Parameters**
 - Optional:
   - `--jar`: Sets the name of the server .jar that launch will run.
   - `--java-path`: Sets the path to the Java Runtime Executable (JRE).
   - `--java-args`: A list of args to pass to the JRE (comma seperated).

### `profile remove`
Removes a profile.

**Parameters**  
 - Positional:
   - `profile-name`: The name of the profile to delete.

### `profile rename`
Renames a profile. If the profile is the `current-profile`, that setting will be updated.

**Parameters**  
 - Positional:
   - `old-profile-name`: The name of the profile to rename.
   - `new-profile-name`: The new name of the profile.

## `serve-up`
Downloads the registered mods and updates Minecraft and Fabric. Note that at present, this will configure everything to match only the current-profile. If the current profile is changed, `serve-up` must be run again.

## `set-version`
Allows you to set the versions for Minecraft, Fabric Loader, and Fabric Installer.

**Parameters**
 - Positional:
   - `--minecraft`, `-m`: The game version to use.
   - `--fabric-loader`, `-l`: The Fabric Loader version to use.
   - `--fabric-installer`, `-i`: The Fabric Installer version to use.

## `config`\*
Manages various config options. With no arguments, `config` will report the default settings.

# Roadmap
## Basic Functionality
These features are needed to say that Tablecloth is in the beta stage.
 - Profiles (done)
 - Download mod dependencies
 - `tablecloth.lock.json`: A file that changes are committed to so users have a fallback if server configuration goes haywire.
 - Launch the server jar through Tablecloth. (done)

## Future Features
 - Figure out how to get most current version of Minecraft for default config
 - Figure out how to get most current version of Fabric jars for default config
 - Figure out how to automatically get mod version that matches current profile's Minecraft version
 - Report when a newer version of Minecraft is available that matches the minor version of the profile
	 - i.e. if 1.19.3 is installed, would report that 1.19.4 is available
	 - Should check if mods for profile are reported as compatible with current version
 - Report when a newer version of a mod is available that's compatible with the profile's set Minecraft version
   - `tablecloth update-check` would perform this check.

# License
Tablecloth MC is published under the MIT License.
