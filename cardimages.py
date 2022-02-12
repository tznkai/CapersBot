#cardsplay
#module to constructs splays out of piles
import PIL
from PIL import Image
import io
import os


from capersdecks import Deck
CARD_PATH = "./cardimages/"

#globals and constants
FULL_WIDTH = 500
HEIGHT = 726
PARTIAL_PIXEL = 95
left_images = {}
  
def draw_in(im):
  map = im.load()
  #draw black line, draw gray line if transparent
  for col in range(im.size[0]):
    map[col,0] = (0, 0, 0, 255)
    map[col,HEIGHT -1] = (0, 0, 0, 255)
    if map[col,1] == (255,255,255,0):
      map[col,1] = (127, 127, 127, 255)
    elif map[col,HEIGHT -2] == (255,255,255,0):
      map[col,HEIGHT -2] = (127, 127, 127, 255)
    for row in range(2,HEIGHT -2):
      if map[col,row] == (255,255,255,0):
        map[col,row] = (255,255,255,255)
  return im

def prep_dict():
  deck = Deck(0)
  for card in deck.cards:
    base_image_name = card.image_name()
    im = Image.open(CARD_PATH + base_image_name)
    box = (0, 0, PARTIAL_PIXEL, HEIGHT )
    crop = im.crop(box)
    key = card.short_name()
    left_images.update({key:crop})
    im.close()

def splay(pile) ->io.BytesIO:
  #Bail out if too short
  if len(pile) < 2:
    return None
  #work on a copy of the pile
  working_pile = pile.copy()
  #build piles from the bottom, set pointer at left edge, calculate number of partials, prep new iamge
  working_pile.reverse()
  left_pointer = 0
  top = len(working_pile)-1
  partials = (top) *PARTIAL_PIXEL
  #make new image with transparency background
  im = Image.new("RGBA", (partials + FULL_WIDTH,HEIGHT ), color=(255, 255, 255, 0))
  #first card goes down
  region = left_images.get(working_pile[0].short_name())
  box = (left_pointer, 0, left_pointer+PARTIAL_PIXEL,HEIGHT)
  im.paste(region,box)
  left_pointer = left_pointer + PARTIAL_PIXEL
  #everything other than the first card and the last card have partials with white transformed
  for i in range(1, top):
    region = left_images.get(working_pile[i].short_name())
    region = draw_in(region)
    box = (left_pointer, 0, left_pointer+PARTIAL_PIXEL,HEIGHT )
    im.paste(region,box)
    left_pointer = left_pointer + PARTIAL_PIXEL
  #last card is full size
  base_image_name = working_pile[top].image_name()
  region = Image.open(CARD_PATH + base_image_name)
  box = (left_pointer, 0, left_pointer+FULL_WIDTH,HEIGHT)
  im.paste(region,box)
  region.close()
  #then paste a partial on top
  region = left_images.get(working_pile[top].short_name())
  region = draw_in(region)
  box = (left_pointer, 0, left_pointer+PARTIAL_PIXEL,HEIGHT )
  im.paste(region,box)
  #need to do this as an object
  bo = io.BytesIO()
  im.save(bo, format='png')
  im.close()
  return bo
  
def build():
  #needs to fragment cards
  pass



# build a reference deck and load into memory at runtime
prep_dict()
