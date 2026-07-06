from cmd import Cmd
import rom
import usb
import pdb

class NameTweakerPrompt(Cmd):
  def __init__(self):
    super(NameTweakerPrompt, self).__init__()
    self.rom = None
    self.usbclient = usb.client()
    self.slot_offsets = {
      'user': rom.OFFSET_NAME,
      'mother': rom.OFFSET_MOTHER_NAME,
      'father': rom.OFFSET_FATHER_NAME,
      'sibling': rom.OFFSET_SIBLING_NAME,
    }

  def do_help(self, inp):
    print("Available commands:")
    print("  dump")
    print("  rominfo")
    print("  names")
    print("  audionames")
    print("  readfile <romfile>")
    print("  writefile <romfile>")
    print("  rename <name>")
    print("  renamesibling <name>")
    print("  renamefamily <slot> <name>")
    print("  changename <name>[,<soundfile>]")
    print("  writedevice")
    print("  exit")

  def do_exit(self, inp):
    print("See ya!")
    return True

  def do_dump(self, inp):
    print("Dumping rom from Leaptop...")
    self.rom = rom.Rom(self.usbclient.dump())
    print("Success! To write rom to file use 'writefile'.")
  
  def do_writedevice(self, inp):
    print("Writing rom to Leaptop...")
    self.usbclient.upload(self.rom.rom)
    print("Success!")

  def do_writefile(self, inp):
    if not inp:
      print("Please specify a ROM filename to write!")
    with open(inp, 'wb') as f:
      f.write(self.rom.rom)
    print("Wrote current ROM to file {}".format(inp))

  def do_changename(self, inp):
    if not self.rom:
      print("No ROM loaded! You must either get ROM from the device or load it from a file.")
      return
    parts = inp.split(',', 1)
    name = parts[0].strip()
    sound = parts[1].strip() if len(parts) > 1 else None
    if len(name) > 8:
      print("Sorry, names >8 characters are not supported yet!")
      return
    print("Changing name to {}".format(name))
    if sound:
      with open(sound, 'rb') as f:
        soundcontents = f.read()
        self.rom.set_name_details(bytes(name.upper().encode('UTF-8')), soundcontents)
    else:
      self.rom.set_name_details(bytes(name.upper().encode('UTF-8')))

  def do_rename(self, inp):
    if not self.rom:
      print("No ROM loaded! You must either get ROM from the device or load it from a file.")
      return
    if not inp.strip():
      print("Please specify a new name.")
      return
    self.do_changename(inp)

  def do_readfile(self, inp):
    if not inp:
      print("Please specify a ROM filename!")
      return
    with open(inp, 'rb') as f:
      self.rom = rom.Rom(f.read())
    print("Read rom from {}".format(inp))

  def do_rominfo(self, inp):
    print("Flash info:")
    print("Name: {}".format(self.rom.get_name_string()))

  def do_names(self, inp):
    if not self.rom:
      print("No ROM loaded! You must either get ROM from the device or load it from a file.")
      return
    for label, value, body_len in self.rom.list_name_slots():
      audio_state = "audio={}".format(body_len)
      print("{}: {} ({})".format(label, value, audio_state))

  def do_audionames(self, inp):
    if not self.rom:
      print("No ROM loaded! You must either get ROM from the device or load it from a file.")
      return
    print("Supported audio names:")
    for item in self.rom.list_supported_audio_names():
      print("{} [{}:{} bytes]".format(item['name'], item['source'], item['body_len']))

  def do_renamesibling(self, inp):
    if not self.rom:
      print("No ROM loaded! You must either get ROM from the device or load it from a file.")
      return
    if not inp.strip():
      print("Please specify a new sibling name.")
      return
    name = inp.strip()
    if len(name) > 8:
      print("Sorry, names >8 characters are not supported yet!")
      return
    print("Changing sibling name to {}".format(name))
    self.rom.rename_family_slot('sibling', bytes(name.upper().encode('UTF-8')))

  def do_renamefamily(self, inp):
    if not self.rom:
      print("No ROM loaded! You must either get ROM from the device or load it from a file.")
      return
    parts = inp.split(None, 1)
    if len(parts) != 2:
      print("Please specify a slot and a new name.")
      return
    slot = parts[0].strip().lower()
    name = parts[1].strip()
    if slot not in self.slot_offsets:
      print("Unknown slot '{}'. Try user, mother, father, or sibling.".format(slot))
      return
    if not name:
      print("Please specify a new name.")
      return
    if len(name) > 8:
      print("Sorry, names >8 characters are not supported yet!")
      return
    print("Changing {} name to {}".format(slot, name))
    self.rom.rename_family_slot(slot, bytes(name.upper().encode('UTF-8')))


NameTweakerPrompt().cmdloop()
