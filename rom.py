import binascii
import sys
import struct
from pathlib import Path

# Offset to apply to addresses when looking at a USB dump. This is because
# the first 4096-byte page of the SPI flash is not normally dumped via USB.
# We start at the second page, so addresses will be off by 1 page.
USB_ADDR_OFFSET = 0x1000

# Base of the address table.
PTR_BASE=0x2f010
OFFSET_NAME = 0x0
OFFSET_MOTHER_NAME = 0x8
OFFSET_FATHER_NAME = 0x18
OFFSET_SIBLING_NAME = 0x30
OFFSET_MSG1 = 0x38
FAMILY_SLOT_OFFSETS = {
  'user': OFFSET_NAME,
  'mother': OFFSET_MOTHER_NAME,
  'father': OFFSET_FATHER_NAME,
  'sibling': OFFSET_SIBLING_NAME,
}
FAMILY_SLOT_ORDER = ('user', 'mother', 'father', 'sibling')

class Rom(object):
  def __init__(self, contents):
    self.rom = contents
  def _get_table_addr(self, addr):
    return int.from_bytes(self.rom[addr:addr+4], byteorder='little')-USB_ADDR_OFFSET
  def _get_lfstring(self, rom, addr):
    return self.rom[addr:self.rom.find(b'\x00', addr)]
  def _family_slot_starts(self):
    slots = []
    for label in FAMILY_SLOT_ORDER:
      start = self._get_table_addr(PTR_BASE + FAMILY_SLOT_OFFSETS[label])
      slots.append((label, start))
    return sorted(slots, key=lambda item: item[1])
  def _family_slot_layout(self):
    starts = self._family_slot_starts()
    sentinel_end = self._get_table_addr(PTR_BASE + OFFSET_MSG1)
    layout = {}
    for i, (label, start) in enumerate(starts):
      end = starts[i + 1][1] if i + 1 < len(starts) else sentinel_end
      name_end = self.rom.find(b'\x00', start)
      if name_end == -1:
        raise ValueError('Could not locate current name terminator.')
      area_end = name_end + 1
      while area_end < end and self.rom[area_end] == 0xFF:
        area_end += 1
      layout[label] = {
        'start': start,
        'end': end,
        'name_end': name_end,
        'area_end': area_end,
        'name': self.rom[start:name_end].decode('utf-8', errors='ignore'),
        'body': self.rom[area_end:end],
      }
    return layout
  def _get_name_block_end(self, nameaddr):
    marker = b'\x01\x00\xcf\x02'
    marker_pos = self.rom.find(marker, nameaddr)
    if marker_pos == -1:
      raise ValueError('Could not locate name block marker.')
    sound_end = self.rom.find(b'\x11', marker_pos + len(marker))
    if sound_end == -1:
      raise ValueError('Could not locate end of name sound block.')
    return sound_end + 1
  def _get_name_area_end(self, nameaddr):
    name_end = self.rom.find(b'\x00', nameaddr)
    if name_end == -1:
      raise ValueError('Could not locate current name terminator.')
    area_end = name_end + 1
    while area_end < len(self.rom) and self.rom[area_end] == 0xFF:
      area_end += 1
    return area_end
  def _set_name_only_at(self, nameaddr, namestr):
    area_end = self._get_name_area_end(nameaddr)
    payload = namestr + b'\x00'
    if len(payload) > (area_end - nameaddr):
      raise ValueError('New name is too long for the existing name area.')
    payload = payload + (b'\xFF' * ((area_end - nameaddr) - len(payload)))
    self.rom = self.rom[:nameaddr] + payload + self.rom[area_end:]
  def _set_family_slot_with_audio(self, slot_label, namestr):
    layout = self._family_slot_layout()
    if slot_label not in layout:
      raise ValueError('Unknown family slot: %s' % slot_label)
    target = layout[slot_label]
    pad = 0 if (len(namestr) + 1) % 4 == 0 else 4 - ((len(namestr) + 1) % 4)
    name_payload_len = len(namestr) + 1 + pad
    total_len = target['end'] - target['start']
    target_body_len = total_len - name_payload_len
    def collect_bodies(source_layout):
      bodies = {}
      for label in FAMILY_SLOT_ORDER:
        slot = source_layout[label]
        if slot['body'] and len(slot['body']) <= target_body_len:
          bodies[slot['name'].upper()] = slot['body']
      return bodies

    supported_bodies = collect_bodies(layout)
    if namestr.decode('utf-8').upper() not in supported_bodies:
      catalog_path = Path('original_backup.rom')
      if catalog_path.exists():
        catalog = Rom(catalog_path.read_bytes())
        supported_bodies.update(collect_bodies(catalog._family_slot_layout()))

    body = supported_bodies.get(namestr.decode('utf-8').upper())
    if body is None:
      body = b'\x00' * target_body_len
    elif len(body) != target_body_len:
      if len(body) > target_body_len:
        body = b'\x00' * target_body_len
      else:
        body = body + (b'\x00' * (target_body_len - len(body)))
    name_payload = namestr + b'\x00' + (b'\xFF' * pad)
    self.rom = self.rom[:target['start']] + name_payload + body + self.rom[target['start'] + total_len:]
  def _audio_catalog(self):
    catalogs = [('current', self._family_slot_layout())]
    catalog_path = Path('original_backup.rom')
    if catalog_path.exists():
      catalogs.append(('catalog', Rom(catalog_path.read_bytes())._family_slot_layout()))
    return catalogs
  def list_supported_audio_names(self):
    names = {}
    for source, layout in self._audio_catalog():
      for label in FAMILY_SLOT_ORDER:
        slot = layout[label]
        if not slot['body']:
          continue
        entry = names.get(slot['name'].upper())
        body_len = len(slot['body'])
        if entry is None or (entry['source'] != 'current' and source == 'current'):
          names[slot['name'].upper()] = {
            'name': slot['name'],
            'source': source,
            'slot': label,
            'body_len': body_len,
          }
    return sorted(names.values(), key=lambda item: item['name'].upper())
  def get_name_at(self, offset):
    return self._get_lfstring(self.rom, self._get_table_addr(PTR_BASE + offset)).decode("utf-8")
  def set_name_at(self, offset, namestr):
    self._set_name_only_at(self._get_table_addr(PTR_BASE + offset), namestr)
  def list_name_slots(self):
    layout = self._family_slot_layout()
    return [(label, layout[label]['name'], len(layout[label]['body'])) for label in FAMILY_SLOT_ORDER]
  def get_name_string(self):
    return self.get_name_at(OFFSET_NAME)
  def rename_family_slot(self, slot_label, namestr):
    self._set_family_slot_with_audio(slot_label, namestr)
  def set_name_details(self, namestr, namesound=None):
    nameaddr = self._get_table_addr(PTR_BASE+OFFSET_NAME)
    if namesound is None:
      self._set_name_only_at(nameaddr, namestr)
      return

    pad = 0 if (len(namestr) + 1) % 4 == 0 else 4 - ((len(namestr) + 1) % 4)
    old_name_end = self.rom.find(b'\x00', nameaddr)
    if old_name_end == -1:
      raise ValueError('Could not locate current name terminator.')
    block_end = self._get_name_block_end(nameaddr)
    block_len = block_end - nameaddr
    namesound = b'\x01\x00\xcf\x02' + namesound + b'\x11'
    payload = namestr + b'\x00' + (b'\xFF' * pad) + namesound
    if len(payload) > block_len:
      raise ValueError('New name block is larger than the original block.')
    payload = payload + (b'\xFF' * (block_len - len(payload)))
    self.rom = self.rom[:nameaddr] + payload + self.rom[block_end:]
  def get_message1_string(self):
    return self._get_lfstring(self.rom, self._get_table_addr(PTR_BASE+OFFSET_MSG1)).decode("utf-8")
