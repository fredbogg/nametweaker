# nametweaker

Tools for tweaking LeapFrog My Own Leaptop ROM data.

## What it does

- Dump the ROM from a connected device.
- Rename the user, mother, father, or sibling slots.
- Reuse built-in audio when a supported name exists.
- Fall back to silence when a supported audio clip is not available.

## Quick Start

1. Plug in the My Own Leaptop and turn it on.
2. Open a terminal in this folder.
3. Start the interactive prompt:

   ```powershell
   python nametweaker.py
   ```

4. At the `(Cmd)` prompt, use `dump` first if you want to read the ROM from the device.
5. Use `names` to see the current family slots.
6. Use `audionames` to see which names currently have audio-backed entries.
7. Rename a slot with `renamefamily <slot> <name>`.
8. Write the changes back with `writedevice`.

## Common Commands

```text
dump
names
audionames
rominfo
renamefamily sibling JANE
renamesibling JANE
renamefamily mother MARY
renamefamily father JOE
rename BOB
changename BOB
changename BOB,C:\path\to\soundfile.adp
writedevice
writefile C:\path\to\backup.rom
exit
```

## One-shot Rename

If you only want to rename the device without using the prompt:

```powershell
python changename.py NEWNAME
```

To change the name and replace the audio too:

```powershell
python changename.py NEWNAME C:\path\to\soundfile.wav
```

## Notes

- Supported audio names can be listed with `audionames`.
- If a requested name has no matching audio, the tool writes a silent payload.
- The scripts are intended for ROMs dumped from the device, not as a full replacement for the original LeapFrog software.
