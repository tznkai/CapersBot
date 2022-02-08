# CapersBot.py
import logging
import asyncio
#Turn on logging
import os
logging.basicConfig(level=logging.INFO)
#load env variables
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
WRONGPATH = os.getenv('WRONGPATH')
PATH = os.getenv('PATH')
# workaround for environment differences, set working directory
wdir = os.getcwd()
if wdir == WRONGPATH:
  os.chdir(PATH) 
wdir = os.getcwd()
import random
import discord
from discord.ext import commands

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
  def emoji(self):
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
  def short_name(self):
    return self.name[0]
  def long_name(self):
    return self.name.capitalize()


#working classes
class Card:
  def __init__(self, suit, rank, stack, up):
    self.suit = suit
    self.rank = rank
    self.stack = stack
    self.up = up
  def short_name(self): 
    return str( self.rank.short_name() )+ self.suit.short_name()
  def long_name(self):
    if self.suit == Suit.JOKER:
      n = self.rank.long_name()+" "+self.suit.long_name()
    else:
      n = self.rank.long_name() + " of " +self.suit.long_name()
    return n
  def emoji(self):
    return str( self.rank.emoji() ) + self.suit.emoji()
  def var_name(self, mode):
    if mode == "Emoji":
      return self.emoji()
    elif mode == "Short":
      return self.short_name()
    elif mode == "Long":
      return self.long_name()
    else:
      return self.long_name()
  def image_name(self):
    #naming, add .png
    #Jokers don't get of
    if self.suit == Suit.JOKER:
      n = self.rank.long_name()+"_"+self.suit.long_name()
    #ranks 2 - 10 use numbers
    elif self.rank.value >1 and self.rank.value <11:
      n = str(self.rank.short_name())+"_of_"+self.suit.long_name()
    #face cards get full rank name and use alt art
    else:
      n = self.rank.long_name() + "_of_" +self.suit.long_name()+"2"
    n = n.lower()
    filename = n + ".png"
    return filename


class Deck:
  def __init__(self,owner):
    print("initializing")
    self.cards = []
    self.owner = owner
    self.image_mode = True
    self.output_mode = "Long"
    self.build()
    self.reshuffle()    
  def build(self):
    print("building")          
    suits = [Suit.CLUBS,Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]
    ranks = [Rank.ACE,Rank.TWO,Rank.THREE,Rank.FOUR,Rank.FIVE,Rank.SIX,Rank.SEVEN,Rank.EIGHT,Rank.NINE,Rank.TEN, Rank.JACK,Rank.QUEEN,Rank.KING]
    init_stack = "Draw"
    init_up = False
    for s in suits:
      for r in ranks:
        self.cards.append(Card(suit=s, rank=r, stack=init_stack, up=init_up))
    self.cards.append(Card(suit=Suit.JOKER,rank=Rank.GOOD,stack='Draw', up=False))
    self.cards.append(Card(suit=Suit.JOKER,rank=Rank.BAD,stack='Draw', up=False))
      
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
          c.up = False

  def show(self):
    print("show method called")
    for c in self.cards:
      print(c.long_name() + " in: " + c.stack + ". Is up card: " + str(c.up))

  def stack_list(self, stack):
    L = []
    for c in self.cards:
      if c.stack == stack:
        L.append(c)
    return L

  def clear_last(self):
    for c in self.cards:
      c.up = False

  def flip(self):
    for count in range(len(self.cards)):
      c = self.cards.pop(0)
      if c.stack == "Draw":
        self.clear_last()
        c.up = True
        c.stack = "Discard"
        self.cards.append(c)
        return c
      else:
        self.cards.append(c)
    return None

  def sleeve_check(self):      
    for c in self.cards:
      if c.stack == "Sleeve":
        return c
    return None

  def sleeve(self):
      sleeve = self.sleeve_check()
      if sleeve is None:
        for c in self.cards:
          if c.up == True:
            c.up = False
            c.stack = "Sleeve"
            return ("success", c)
        return ("fail", None)
      else:
        return ("full", sleeve)
  def unsleeve(self):
      sleeve = self.sleeve_check()
      if sleeve is None:       
        return None
      else:
        for c in self.cards:
          if c.stack == "Sleeve":
            c.stack = "Discard"
            self.clear_last()
            c.up = True
        return sleeve
  def nuke(self):
      #returns a 2 member tuple with a bool and a Card object or None
      for c in self.cards:
          if c.up == True:
            c.up = False
            c.stack = "Destroyed"
            return (True, c)
      return (False, None)

#functions

def name_cards(stack):
  L = []
  for card in stack:
    L.append( card.long_name() )
  return L

def short_name_cards(stack):
  L = []
  for card in stack:
    L.append( card.short_name() )
  return L

def emojify_cards(stack):
  L = []
  for card in stack:
    L.append( card.emoji() )
  return L

def var_name_cards(stack, mode):
    if mode == "Emoji":
      return emojify_cards(stack)
    elif mode == "Short":
      return short_name_cards(stack)
    elif mode == "Long":
      return name_cards(stack)
    else: #default to long name
      return name_cards(stack)

def suit_sift(stack, suit, sort):
  #takes a list of cards, returns a list of cards with matching suits
  #returning a list should be made a method of Deck in future versions
  L = []
  for card in stack:
    if card.suit == suit:
      L.append(card)
  if sort and len(L)>0:
      L.sort(key=get_rank)
  return L

def get_rank(card):
  rank = card.rank.value
  return rank

#main path resumes

pickleProblem = False
#pickle check, define empty dict otherwise.
import pickle
try:
  ad = open("activedecks.pickle", "rb")
  activeDecks = pickle.load(ad)
  ad.close()
except (OSError, IOError) as e:
  activeDecks={}
  ad = open("activedecks.pickle", "wb")
  pickle.dump(activeDecks, ad)
  ad.close()
  print(e)
except EOFError as e:
  print (e)
  activeDecks = {}
except Exception as e:
  activeDecks = {}
  pickleProblem = True
  print (e)
  
#bot functions
async def autosave():
  while True:
    with open("activedecks.pickle", "wb") as f:
      pickle.dump(activeDecks,f)
    await asyncio.sleep(600)
    
def embed(name):
  file = discord.File(fp=name, spoiler=False, filename=name)
  embed = discord.Embed()
  embed.set_image(url="attachment://"+name)
  return (file, embed)

#bot commands
bot = commands.Bot(command_prefix="+")

@bot.event
async def on_ready():
  dev = await bot.fetch_user(277631444833009676)
  bot.loop.create_task(autosave())
  if pickleProblem:  
    await dev.send("there was a pickle problem")
  await dev.send("I have connected, working directory: "+str(wdir))
#@bot.command(name='soundcheck', help='responds I can still hear you')
#async def echo_back(ctx):
#  response = "I can still hear you, "+ctx.author.name
  
#  await ctx.send(response)
@bot.command(name='build', help='builds or rebuilds your a fresh deck BE CAREFUL')
async def new_deck(ctx):
  owner=ctx.author.id
  deck = Deck(owner = owner)
  activeDecks.update({owner:deck})
  response = "built deck for " + ctx.author.display_name + " with ownerID: "+str(owner)  
  await ctx.send(response)
#@bot.command(name='show', help='outputs the contents of a deck to console for debugging purposes only')
#async def show_deck(ctx):
#  owner = ctx.author.id
#  deck = activeDecks.get(owner)
#  if deck is None:
#    response = "No such deck. Use the build command."  
#  else:
#    response = "Outputting deck "+str(owner)+" to console"
#    deck.show()
#  await ctx.send(response)
@bot.command(name='discards', help='List all your discarded cards')
async def show_discards(ctx):
  owner = ctx.author.id
  deck = activeDecks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    #sort function
    discards = deck.stack_list(stack="Discard")
    if len(discards) > 0:
      mode = deck.output_mode
      spades = suit_sift(discards, Suit.SPADES, True)
      hearts = suit_sift(discards, Suit.HEARTS, True)
      diamonds = suit_sift(discards, Suit.DIAMONDS, True)
      clubs = suit_sift(discards, Suit.CLUBS, True)
      jokers = suit_sift(discards, Suit.JOKER, True)
      sortedDiscards = []
      sortedDiscards.extend(spades)
      sortedDiscards.extend(hearts)
      sortedDiscards.extend(diamonds)
      sortedDiscards.extend(clubs)
      sortedDiscards.extend(jokers)
      sortedDiscards = str(var_name_cards(stack=sortedDiscards, mode=mode))
      response = ctx.author.display_name+"\'s discards are: "+sortedDiscards
    else:
      response = ctx.author.display_name + " has no discarded cards."
  await ctx.send(response)
@bot.command(name='flip', help='Flip the top card off of your deck')
async def flip(ctx):
  owner = ctx.author.id
  deck = activeDecks.get(owner)
  if deck is None:
    p = (None, None)
    response = "No such deck. Use the build command."  
  else:
    mode = deck.output_mode
    image_mode = deck.image_mode
    c = deck.flip()
    if c is None:
      response = "Your deck is empty, reshuffle!"
    else:
      response = ctx.author.display_name+"\'s card is: "+c.var_name(mode=mode)
      if image_mode:
        image_name = c.image_name()
        p = embed(image_name)           
      else:
        p = (None, None)        
  await ctx.send(response,file=p[0], embed=p[1])
  
@bot.command(name='sleeve', help='Sleeve the last flipped card')
async def sleeve(ctx):
  owner = ctx.author.id
  deck = activeDecks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    mode = deck.output_mode
    s = deck.sleeve()
    if s[0] == "full":
      response = "You already have a sleeved card, it's a "+s[1].var_name(mode=mode)
    elif s[0] == "fail":
      response = "Nothing to sleeve, you can only sleeve the last flipped card"
    else:
      response = ctx.author.display_name+" sleeves their "+s[1].var_name(mode=mode)
  await ctx.send(response)
@bot.command(name='unsleeve', help='Unsleeve the last flipped card')
async def unsleeve(ctx):
  owner = ctx.author.id
  deck = activeDecks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    c = deck.unsleeve()
    if c is None:
      response = "You don't have a sleeved card"
    else:
      mode = deck.output_mode
      response = ctx.author.display_name+" unsleeves their "+c.var_name(mode=mode)
  await ctx.send(response)
@bot.command(name='shuffle', help='Shuffle your discards and draw together')
async def shuffleup(ctx):
  owner = ctx.author.id
  deck = activeDecks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    c = deck.reshuffle()
    response = ctx.author.display_name+" reshuffles their deck"
  await ctx.send(response)

@bot.command(name='nuke', help='nuke your last flipped card')
async def nuke_card(ctx):
  owner = ctx.author.id
  deck = activeDecks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    t = deck.nuke()
    if t[0] == True:
      mode = deck.output_mode
      response = ctx.author.display_name + " nukes their "+t[1].var_name(mode=mode)
    elif t[0] == False:
      response = "Nothing to nuke, you can only nuke the last flipped card"
  await ctx.send(response)


@bot.command(name='glance', help='Stats at a glance')
async def glance(ctx):
  owner = ctx.author.id
  deck = activeDecks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    #set output mode
    mode = deck.output_mode
    # count discards
    discardslen = str(len(deck.stack_list(stack="Discard")))
    # count cards
    drawlen = str(len(deck.stack_list(stack="Draw")))
    # check sleeves
    sleeves = deck.sleeve_check()
    if sleeves is None:
      sleeves = "nothing up their sleeve"
    else: sleeves = sleeves.var_name(mode=mode) + " up their sleeve"
    # check nuked
    destroyed = deck.stack_list(stack="Destroyed")
    if destroyed == []:
      destroyed = "no cards"
    else:
      destroyed = var_name_cards(stack=destroyed, mode=mode)
      destroyed = str(destroyed)
    # check for flipped card
    for c in deck.cards:
      if c.up == True:
        up = c.var_name(mode=mode) + " is the last flipped card."
        break
      up = "No card is the last flipped card."
    response = ctx.author.display_name + " has discarded " + discardslen + " cards, has " + drawlen + " cards left in their draw, has destroyed " + destroyed + " and has " + sleeves + ". " + up
  await ctx.send(response)

@bot.command(name='output', brief='change the format of your cards', help='output accepts one argument. Valid arguments are: emoji, long, short')
async def output_mode(ctx, arg):
  owner = ctx.author.id
  deck = activeDecks.get(owner)
  valid = ('Emoji', 'Long', 'Short')
  mode = arg.capitalize()  
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    if mode in valid:
      deck.output_mode = mode
      response = ctx.author.display_name + "'s output mode is now: "+mode
    else:
      response = arg + "is not a valid mode"
  await ctx.send(response)  
@bot.command(name='images', brief='On or Off', help='seting images on will ')
async def image_mode(ctx, arg):
  owner = ctx.author.id
  deck = activeDecks.get(owner)
  valid = ('On', 'Off')
  mode = arg.capitalize()  
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    if mode in valid:
      #convert on and off inputs into a boolean
      if mode == "On":
        deck.image_mode = True
      elif mode == "Off":
        deck.image_mode = False
      response = ctx.author.display_name + "'s output mode is now: "+mode
    else:
      response = arg + "is not a valid mode"
  await ctx.send(response)  

#@output_mode.error
#async def output_mode_error(self, ctx: commands.Context, error: commands.CommandError):
#  if isinstance(error, commands.MissingRequiredArgument):
#    message = "Missing required argument, please supply a mode."
#  else:
#    message = "something went wrong!"
#  await ctx.send(message)

@bot.command(name='save', brief='force the bot to save data', help='forces the bot to save data')
async def man_save(ctx):
  response = "done"
  with open("activedecks.pickle", "wb") as f:
    pickle.dump(activeDecks, f)
  await ctx.send(response)

bot.run(TOKEN)