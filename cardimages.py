#cardsplay
#module to constructs splays out of piles
import PIL
from PIL import Image
import io
import math

from capersdecks import Deck

#globals and constants
CARD_PATH = "./cardimages/"
FULL_WIDTH = 500
HEIGHT = 726
PARTIAL_WIDTH = 95
CARD_IMAGES = {}

def prep_dict(d):
  deck = Deck(0)
  for card in deck.cards:
    base_image_name = card.image_name()
    im = Image.open(CARD_PATH + base_image_name)
    key = card.short_name()
    d.update({key:im})

def splay(pile, bo = True, divisor=1,testno="") -> object:
  working_pile = pile.copy() #work on a copy of the pile to avoid disturbing the original if it is going to be reused.
  working_pile.reverse() #piles are splayed starting from the bottom and then a new card on top
  left_pointer = 0 #reset where to paste from
  top = len(working_pile)-1
  partials = (top) * PARTIAL_WIDTH #partials are calculated 
  im = Image.new("RGBA", (partials + FULL_WIDTH,HEIGHT ), color=(255, 255, 255, 0)) #initialize the new image
  for card in working_pile:
    region = CARD_IMAGES.get(card.short_name())
    box = (left_pointer, 0 )
    im.paste(region, box, region)
    left_pointer = left_pointer + PARTIAL_WIDTH
  im = im.resize((im.width//divisor,im.height//divisor)) #Shrink by divisor
    #if __name__ == "__main__":
    #  im.save("test"+str(testno)+".png")
    #  o = None
  if bo: #return as a bytes object
    o = io.BytesIO()
    im.save(o, format='png')
    im.close()
  else: #or an Image object
    o = im
  return o

def single(card, divisor=1) -> io.BytesIO:
  bo = io.BytesIO()
  im = CARD_IMAGES.get(card.short_name())
  im = im.resize((im.width//divisor,im.height//divisor))
  im.save(bo, format='png')
  return bo
  
def count_pack(pile, count=9):
  #fragments pile into multiple piles by count
  #sort into suits if necessary
  work_pile = pile.copy() #use a working copy to avoid messing with the main pile.
  sub_pile = [] # to pass to the next
  rows = [] # list of bo to be appended up and down
  card_count = 0 #start from zero
  #pack a list
  for card in work_pile:
    sub_pile.append(card)
    card_count = card_count + 1
    if card_count == count: # every count, form a row
      rows.append(splay(sub_pile, bo = False))
      card_count = 0 #reset to start new pack
      sub_pile = [] #reset to start new pack
  #at end of for, there might be remainder
  if card_count > 0:
    rows.append(splay(sub_pile, bo = False))
  return rows

def verticle_build(pile, sort=False, divisor=1, testno=""):
  #abandon this in favor of scaleling.
  if sort:
    #sort by suit method will go here.
    pass
  else:
    top_pointer = 0
    imgs = count_pack(pile, count=9)
    total_rows = len(imgs)
    width = imgs[0].width
    im = Image.new("RGBA", (width, HEIGHT*total_rows+total_rows-1), color=(255, 255, 255, 0))
    for region in imgs:
      box = (0,top_pointer)
      im.paste(region,box)
      top_pointer = top_pointer + HEIGHT + 1 # advance pointer
    im = im.resize((im.width//divisor,im.height//divisor)) #Shrink by divisor
    if __name__ == "__main__": # for testing
      im.save("test"+str(testno)+".png")
      im.close()
    else: #normal operation is to return a bytes stream
      o = io.BytesIO()
      im.save(o, format='png')
      im.close()
      return o
# build a reference deck and load into memory at runtime
prep_dict(CARD_IMAGES)


if __name__ == "__main__":
  test_deck = Deck(-1)
  test_pile = test_deck.pile("Stack", "Draw", False, False, 17)
  for card in test_pile:
    print(card.emoji())
  for testno in range(1,11):
    verticle_build(test_pile, sort=False, divisor = testno, testno=testno)