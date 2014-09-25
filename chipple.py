import random
import time
import sys
import pygame

''' 
    Pygame shit
'''
pygame.init()
size = width, height = 640, 320

speed = [2, 2]
black = 255, 170, 0

screen = pygame.display.set_mode(size)
pixel = pygame.image.load("pixel.png")

key_map = { 120 : 0x0,
            49  : 0x1,
            50  : 0x2,
            51  : 0x3,
            113 : 0x4,
            119 : 0x5,
            101 : 0x6,
            97  : 0x7,
            115 : 0x8,
            100 : 0x9,
            120 : 0xA,
            99  : 0xB,
            52  : 0xC,
            114 : 0xD,
            102 : 0xE,
            118 : 0xF
            }

LOGGING = False
DEBUG = False

def log(msg):
  if LOGGING:
    print msg

class cpu:
  inputs = [0] * 16
  display = [0] * 32 * 64
  memory = [0] * 4096
  v = [0] * 16 # 16 8-bit general purpose registers, VF used for special flags
  stack = [] # stack of 16 16-bit values (memory locations)
  opcode = 0
  index = 0 # 16-bit register
  pc = 0 # 16-bit program counter

  timer = 0

  should_draw = False
  key_weight = False

  funcmap = None
  vx = 0
  vy = 0

  fonts = [0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
           0x20, 0x60, 0x20, 0x20, 0x70, # 1
           0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
           0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
           0x90, 0x90, 0xF0, 0x10, 0x10, # 4
           0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
           0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
           0xF0, 0x10, 0x20, 0x40, 0x40, # 7
           0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
           0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
           0xF0, 0x90, 0xF0, 0x90, 0x90, # A
           0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
           0xF0, 0x80, 0x80, 0x80, 0xF0, # C
           0xE0, 0x90, 0x90, 0x90, 0xE0, # D
           0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
           0xF0, 0x80, 0xF0, 0x80, 0x80  # F
           ]

  def _0NNN(self):
    #log("0NNN")
    extracted_op = self.opcode & 0xf0ff
    try:
      self.funcmap[extracted_op]()
    except:
     print "Unknown instruction %X" % self.opcode

  def _00E0(self):
    log("00E0 %X - clear screen" % self.opcode)
    self.display = [0] * 64 * 32
    self.should_draw = True

  def _00EE(self):
    log("00EE %X - Returns from a subroutine." % self.opcode)
    self.pc = self.stack.pop()

  def _1NNN(self):
    log("1NNN %X - Jumps to address NNN" % self.opcode)
    self.pc = self.opcode & 0x0fff

  def _2NNN(self):
    log("2NNN %X - Calls subroutine at NNN" % self.opcode)
    self.stack.append(self.pc)
    self.pc = self.opcode & 0x0fff

  def _3XNN(self):
    log("3XNN %X - Skips next instruction if VX equals NN" % self.opcode)
    if self.v[self.vx] == (self.opcode & 0x00ff):
      self.pc += 2

  def _4XNN(self):
    log("4XNN %X - Skips the next instruction if VX doesn't equal NN." % self.opcode)
    if self.v[self.vx] != (self.opcode & 0xff):
      self.pc += 2

  def _5XY0(self):
    log("5XY0 %X - Skips the next instruction if VX = VY" % self.opcode)
    if self.v[self.vx] == self.v[self.vy]:
      self.pc += 2

  def _6XNN(self):
    log("6XNN %X - Sets VX to NN." % self.opcode)
    self.v[self.vx] = self.opcode & 0x00ff

  def _7XNN(self):
    log("7XNN %X - Adds NN to VX" % self.opcode)
    self.v[self.vx] += (self.opcode & 0x00ff)
    self.v[self.vx] &= 0xff

  def _8NNN(self):
    extracted_op = self.opcode & 0xf00f
    extracted_op += 0x0ff0
    try:
      self.funcmap[extracted_op]()
    except:
      print "Unknown instruction 8NNN %X" % self.opcode

  def _8XY0(self):
    log("8XY0 %X - Sets VX to the value of VY" % self.opcode)
    self.v[self.vx] = self.v[self.vy]

  def _8XY1(self):
    log("8XY1 %X - Sets VX to the value of VX or VY" % self.opcode)
    self.v[self.vx] |= self.v[self.vy]

  def _8XY2(self):
    log("8XY2 %X - Sets VX to the value of VX and VY" % self.opcode)
    self.v[self.vx] &= self.v[self.vy]

  def _8XY3(self):
    log("8XY3 %X - Sets VX to the value of VX xor VY" % self.opcode)
    self.v[self.vx] ^= self.v[self.vy]

  def _8XY4(self):
    log("8XY4 %X - Adds VY to VX." % self.opcode)
    if self.v[self.vx] + self.v[self.vy] > 0xff:
      self.v[0xf] = 1
    else: 
      self.v[0xf] = 0
    self.v[self.vx] += self.v[self.vy]
    self.v[self.vx] &= 0xff # ensure VX is 8-bit value (<= 0xff)

  def _8XY5(self):
    log("8XY5 %X - Subtracts VY from VX" % self.opcode)
    if self.v[self.vy] > self.v[self.vx]:
      self.v[0xf] = 0
    else:
      self.v[0xf] = 1
    self.v[self.vx] -= self.v[self.vy]
    self.v[self.vx] &= 0xff

  def _8XY6(self):
    log("8XY6 %X - Shift VX right by 1" % self.opcode)
    self.v[0xf] = self.v[self.vx] & 0x0001
    self.v[self.vx] = self.v[self.vx] >> 1

  def _8XY7(self):
    log("8XY7 %X - sets VX to VY - VX" % self.opcode)
    if self.v[self.vx] > self.v[self.vy]:
      self.v[0xf] = 0
    else:
      self.v[0xf] = 1
    self.v[self.vx] = self.v[self.vy] - self.v[self.vx]
    self.v[self.vx] &= 0xff

  def _8XYE(self):
    log("8XYE %X - Shifts VX left by one" % self.opcode)
    self.v[0xf] = (self.v[self.vx] & 0x00f0) >> 7 # how's this work?
    self.v[self.vx] = self.v[self.vx] << 1
    self.v[self.vx] &= 0xff

  def _9XY0(self):
    log("9XY0 %X - Skips the next instruction if VX doesn't equal VY" % self.opcode)
    if self.v[self.vx] != self.v[self.vy]:
      self.pc += 2

  def _ANNN(self):
    log("ANNN %X - Sets I to address NNN" % self.opcode)
    self.index = self.opcode & 0x0fff

  def _BNNN(self):
    log("BNNN %X - Jumps to the address NNN plus V0" % self.opcode)
    self.pc = (self.opcode & 0x0fff) + self.v[0]

  def _CXNN(self):
    log("CXNN %X - Sets VX to a random number and NN" % self.opcode)
    self.v[self.vx] = int(random.random() * 0xff) & (self.opcode & 0x00ff)
    self.v[self.vx] &= 0xff

  def _DXYN(self):
    log("DXYN %X - Does sprite shit" % self.opcode)
    self.v[0xf] = 0
    x = self.v[self.vx] & 0xff
    y = self.v[self.vy] & 0xff
    height = self.opcode & 0x000f
    row = 0
    while row < height:
      curr_row = self.memory[row + self.index]
      pixel_offset = 0
      while pixel_offset < 8:
        loc = x + pixel_offset + ((y + row) * 64)
        pixel_offset += 1
        if (y + row) >= 32 or (x + pixel_offset - 1) >= 64: 
          # ignore pixels outside screen
          continue
        mask = 1 << 8 - pixel_offset
        curr_pixel = (curr_row & mask) >> (8 - pixel_offset)
        self.display[loc] ^= curr_pixel
        if self.display[loc] == 0:
          self.v[0xf] = 1
        else:
          self.v[0xf] = 0
      row += 1
    self.should_draw = True

  def _ENNN(self):
    extracted_op = self.opcode & 0xf00f
    try:
      self.funcmap[extracted_op]()
    except:
      print "%X E SHIT BROKE" % self.opcode

  def _EX9E(self):
    log("EX9E %X - Skips next instruction if the key in VX is pressed" % self.opcode)
    key = self.v[self.vx] & 0xf
    if self.inputs[key] == 1:
      log("KEY PRESSED")
      self.pc += 2

  def _EXA1(self):
    log("EXA1 %X - Skips next instruction if the key in VX isn't pressed" % self.opcode)
    key = self.v[self.vx] & 0xF
    if self.inputs[key] == 0:
      self.pc += 2

  def _FNNN(self):
    #log("FNNN %X - some F---" % self.opcode)
    extracted_op = self.opcode & 0xf0ff
    try:
      self.funcmap[extracted_op]()
    except:
      log("Unknown opcode - FNNN %X" % self.opcode)

  def _FX07(self):
    log("FX07 %X - Sets VX to value of delay timer" % self.opcode)
    self.v[self.vx] = self.dt

  def _FX0A(self):
    log("FX0A %X - Await keypress, store in VX - " % self.opcode)
    key = self.get_key()
    if key >= 0:
      self.v[self.vx] = key
    else:
      self.pc -= 2

  def _FX15(self):
    log("FX15 %X - Set delay timer to VX" % self.opcode)
    self.dt = self.v[self.vx]

  def _FX18(self):
    log("FX18 %X - Set sound timer to VX" % self.opcode)
    self.st = self.v[self.vx]

  def _FX1E(self):
    log("FX1E %X - adds VX to I" % self.opcode)
    self.index += self.v[self.vx]
    if self.index > 0xfff:
      self.v[0xf] = 1
      self.index &= 0xfff
    else:
      self.v[0xf] = 0

  def _FX29(self):
    log("FX29 %X - Sets I to location of sprite for character in VX" % self.opcode)
    self.index = (5*(self.v[self.vx])) & 0xfff

  def _FX33(self):
    log("FX33 %X - Stores the BCD representation of VX something something something" % self.opcode)
    self.memory[self.index] = self.v[self.vx] / 100
    self.memory[self.index+1] = (self.v[self.vx] % 100) / 10
    self.memory[self.index+2] = self.v[self.vx] % 10

  def _FX55(self):
    log("FX55 %X - Stores V0 to VX in memory starting at address I." % self.opcode)
    for i in range(self.vx):
      self.memory[self.index+i] = self.v[i]
    self.index += (self.vx) + 1

  def _FX65(self):
    log("FX65 %X - Fills V0 to VX with values from memory starting at address I." % self.opcode)
    for i in range(self.vx):
      self.v[i] = self.memory[self.index+i]
    self.index += (self.vx) + 1


  def load_rom(self, rom_path):
    binary = open(rom_path, "rb").read()
    for i in range(len(binary)):
      self.memory[i+0x200] = ord(binary[i])

  def __init__(self, *args, **kwargs):
    self.funcmap = {
      0x0000: self._0NNN,
      0x00E0: self._00E0,
      0x00EE: self._00EE,
      0x1000: self._1NNN,
      0x2000: self._2NNN,
      0x3000: self._3XNN,
      0x4000: self._4XNN,
      0x5000: self._5XY0,
      0x6000: self._6XNN,
      0x7000: self._7XNN,
      0x8000: self._8NNN,
      0x8ff0: self._8XY0,
      0x8ff1: self._8XY1,
      0x8ff2: self._8XY2,
      0x8ff3: self._8XY3,
      0x8ff4: self._8XY4,
      0x8ff5: self._8XY5,
      0x8ff6: self._8XY6,
      0x8ff7: self._8XY7,
      0x8ffe: self._8XYE,
      0x9000: self._9XY0,
      0xA000: self._ANNN,
      0xB000: self._BNNN,
      0xC000: self._CXNN,
      0xD000: self._DXYN,
      0xE000: self._ENNN,
      0xE00E: self._EX9E,
      0xE001: self._EXA1,
      0xF000: self._FNNN,
      0xF007: self._FX07,
      0xF00A: self._FX0A,
      0xF015: self._FX15,
      0xF018: self._FX18,
      0xF01E: self._FX1E,
      0xF029: self._FX29,
      0xF033: self._FX33,
      0xF055: self._FX55,
      0xF065: self._FX65
    }

  def stepper(self):
    for event in pygame.event.get():
      if event.type == pygame.KEYDOWN:
        key = event.key
        if key == 13:
          i = int(raw_input("What register should we change? > "))
          self.v[i] = int(raw_input("What should we change register %d to? > " % i))
          print "step %X" % self.opcode
          print "register", self.v
          print "pc 0x%X" % self.pc
          print "index %X" % self.index
          print "---"
          return True
        if key == 32:
          self.debug = False
        if key == 275:
          print "step %X" % self.opcode
          print "register", self.v
          print "pc 0x%X" % self.pc
          print "index %X" % self.index
          print "---"
          return True

  def tick(self):
    self.opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]

    while self.debug:
      if self.stepper():
        break
    """ Main loop of emulation """

    self.vx = (self.opcode & 0x0f00) >> 8
    self.vy = (self.opcode & 0x00f0) >> 4

    extracted_op = self.opcode & 0xf000

    self.pc += 2

    if self.dt > 0:
      self.dt -= 1
    if self.st > 0:
      self.st -= 1

    #time.sleep(0.01)

    #self.inputs = [0] * 16
    events = pygame.event.get()
    for event in events:
      if event.type == pygame.KEYDOWN:
        key = event.key
        if key in key_map:
          self.inputs[key_map[key]] = 1
        if key == 32:
          self.debug = True 
      if event.type == pygame.KEYUP:
        key = event.key
        if key in key_map:
          self.inputs[key_map[key]] = 0

    try:
      self.funcmap[extracted_op]()
    except:
      print "Unknown instructon: %X - %X" % (self.opcode, extracted_op)


  def clear(self):
    screen.fill(black)
    self.should_draw = True

  def initialize(self):
    #self.clear()
    self.memory = [0] * 4096
    self.v = [0] * 16
    self.display = [0] * 64 * 32
    self.stack = []
    self.inputs = [0] * 16
    self.opcode = 0
    self.index = 0

    self.dt = 0
    self.st = 0
    self.should_draw = False

    self.pc = 0x200

    #self.debug = False

    for i in range(80):
      self.memory[i] = self.fonts[i]

  def draw(self):
    if self.should_draw:
      screen.fill(black)
      #self.clear()
      line_counter = 0
      for i in range(len(self.display)):
        if self.display[i] == 1:
          x = (i % 64) * 10
          y = (i / 64) * 10
          screen.blit(pixel, (x, y))
      pygame.display.flip()
      self.should_draw = False

  def get_key(self):
    for i in range(len(self.inputs)):
      if self.inputs[i] == 1:
        return i

  def main(self, debug):
    self.debug = debug
    self.initialize()
    self.load_rom(sys.argv[1])
    while True:
      self.tick()
      self.draw()

if len(sys.argv) < 2:
  print "Usage: python chipple.py <path to game>"
  exit()

if len(sys.argv) > 2:
  if sys.argv[2] == "debug":
    DEBUG = True
    print "debug"
  if sys.argv[2] == "log":
    LOGGING = True

emu = cpu()

emu.main(DEBUG)
