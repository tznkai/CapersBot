#capersdecks.py
import enum
from pickle import FALSE
import random
#Enumerations
from enum import Enum
class Rank(Enum):
  BAD = 1
  TWO = 2
  THREE = 3
  FOUR = 4
  FIVE = 5
  SIX = 6
  SEVEN = 7
  EIGHT = 8
  NINE = 9
  TEN = 10
  JACK = 11
  QUEEN = 12
  KING = 13
  ACE = 14
  GOOD = 15
  def emoji(self):
    return self.short_name()
  def long_name(self):
    return self.name.capitalize()
  def short_name(self):
    if self.value <11 and self.value >1:
     return self.value
    else:
      return self.name[0]
    
class Suit(Enum):
  JOKER = 5
  SPADES = 4
  HEARTS = 3
  DIAMONDS = 2
  CLUBS = 1
  def emoji(self) -> str:
    if self.name == "CLUBS":
      return "\U00002667"
    elif self.name == "DIAMONDS":
      return "\U00002666"
    elif self.name == "HEARTS":
      return "\U00002665"
    elif self.name == "SPADES":
      return "\U00002664"
    elif self.name == "JOKER":
      return "\U0001F0CF"
  def short_name(self) -> str:
    return self.name[0]
  def long_name(self) -> str:
    return self.name.capitalize()


#working classes
class Card:
  def __init__(self, suit:enum, rank:enum, stack:str):
    self.suit = suit
    self.rank = rank
    self.stack = stack
  def short_name(self) -> str: 
    return str( self.rank.short_name() )+ self.suit.short_name()
  def long_name(self) -> str:
    if self.suit == Suit.JOKER:
      n = self.rank.long_name()+" "+self.suit.long_name()
    else:
      n = self.rank.long_name() + " of " +self.suit.long_name()
    return n
  def emoji(self) -> str:
    return str( self.rank.emoji() ) + self.suit.emoji()
  def var_name(self, mode:str):
    if mode == "Emoji":
      return self.emoji()
    elif mode == "Short":
      return self.short_name()
    elif mode == "Long":
      return self.long_name()
    else:
      return self.long_name()
  def image_name(self) ->str:
    #naming, add .png
    #Jokers don't get of
    if self.suit == Suit.JOKER:
      n = self.rank.long_name()+"_"+self.suit.long_name()
    #ranks 2 - 10 use numbers
    elif self.rank.value >1 and self.rank.value <11:
      n = str(self.rank.short_name())+"_of_"+self.suit.long_name()
    #face cards get full rank name and use alt art
    else:
      n = self.rank.long_name() + "_of_" +self.suit.long_name()
      #if it's a jack queen or king, use alt art
      if self.rank.value < 14 and self.rank.value >11:
        n = n + "2"
    n = n.lower()
    filename = n + ".png"
    return filename
  def sort_value(self) -> int:
    s = self.suit.value * 100
    r = self.rank.value
    return s + r
#Card ends


class Deck:
  def __init__(self,owner:int):
    self.cards = []
    self.owner = owner
    self.image_mode = True
    self.output_mode = "Long"
    self.build()
    self.reshuffle()    

  def build(self):
    suits = [Suit.CLUBS,Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]
    ranks = [Rank.ACE,Rank.TWO,Rank.THREE,Rank.FOUR,Rank.FIVE,Rank.SIX,Rank.SEVEN,Rank.EIGHT,Rank.NINE,Rank.TEN, Rank.JACK,Rank.QUEEN,Rank.KING]
    init_stack = "Draw"
    for s in suits:
      for r in ranks:
        self.cards.append(Card(suit=s, rank=r, stack=init_stack))
    self.cards.append(Card(suit=Suit.JOKER,rank=Rank.GOOD,stack='Draw'))
    self.cards.append(Card(suit=Suit.JOKER,rank=Rank.BAD,stack='Draw'))
     
  def reshuffle(self):
    random.shuffle(self.cards)
    for c in self.cards:
      if c.stack == "Destroyed":
        pass
      elif c.stack == "Sleeve":
        pass
      elif c.stack == "GMSleeve":
        pass
      else:
          c.stack = "Draw"

  #def show(self):
  #  print("show method called")
  #  for c in self.cards:
  #    print(c.long_name() + " in: " + c.stack)

  def flip(self):
    #pass over deck until a Draw card is found
    for i in range(len(self.cards)):
      c = self.cards[i]
      if c.stack == "Draw":
        self.topdeck(i,"Discard")
        return c
    return None

  def sleeve(self) ->tuple[str, Card]:
      sleeve = self.pile(attribute="Stack", member = "Sleeve", sort=False, reverse=False)
      if sleeve == []:
        # if the sleeve is empty find the top of the discards,
        i = self.find_top("Discard")
        if i is None:
          # return discard empty
          return ("fail", None)
        else:
          # put it on top of the sleeve
          self.topdeck(i, "Sleeve")
          #send back success message, object
          return ("success", self.cards[0])        
      else:
        return ("full", sleeve[0])

  def unsleeve(self) ->Card:
      #find the top (only) card in sleeve
      i = self.find_top("Sleeve")
      if i is None:
        return None
      else:
        self.topdeck(i,"Discard")
        return self.cards[0]

  def nuke(self) -> tuple:
    #returns a 2 member tuple with a bool and a Card object or None
    i = self.find_top("Discard")    
    if i is None:
      return None
    else: 
      self.topdeck(i,"Destroyed")
      return self.cards[i]

  def pile(self, attribute:str, member:str, sort:bool, reverse:bool) -> list:
    #produces a list of Cards based on the pivoted attribute
    p = []
    #suits
    if attribute == "Suit":
      for card in self.cards:
        if card.suit.name.capitalize() == member:
          p.append(card)
        if sort and len(p)>0:
          p.sort(key=get_sort_value, reverse=reverse)
      return p
    elif attribute == "Stack":
      for card in self.cards:
        if card.stack == member:
          p.append(card)
        if sort and len(p)>0:
          p.sort(key=get_sort_value, reverse=reverse)
      return p
    else:
      # if asking for an invalid attribute, return None, fix the code
      p = None
      return p

  def find_top(self, stack) -> int:
    # find the top of a stack
    for i in range (len(self.cards)):
      if self.cards[i].stack == stack:
        return i
    else:
      return None

  def topdeck(self, index, destination_stack:str):
    #takes the top card of start stack and places it on top of the other stack.
    #this function has no error checking and will accept an destination stack!
    c = self.cards.pop(index)
    #set to destination stack
    c.stack = destination_stack
    #insert at the top of the card list, this preserves the ordering
    self.cards.insert(0, c)
#Deck ends


#functions to extract name from pile of cards
def name_cards(pile) ->str:
  p = []
  for card in pile:
    p.append( card.long_name() )
  return p
def short_name_cards(pile)->str:
  p = []
  for card in pile:
    p.append( card.short_name() )
  return p
def emojify_cards(pile)->str:
  p = []
  for card in pile:
    p.append( card.emoji() )
  return p
def var_name_cards(pile:list, mode:str):
    if mode == "Emoji":
      return emojify_cards(pile)
    elif mode == "Short":
      return short_name_cards(pile)
    elif mode == "Long":
      return name_cards(pile)
    else: #default to long name
      return name_cards(pile)

#functions to use for sorting Card objects
def get_rank(card)->int:
  return card.rank.value
def get_stack(card)->str:
  return card.stack
def get_sort_value(card):
  return card.sort_value()