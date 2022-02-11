# CapersBot.py
import logging
import random
import asyncio
from botocore.exceptions import ClientError
import discord
import boto3
from dotenv import load_dotenv
from discord.ext import commands
import os
import atexit
#Turn on logging
logging.basicConfig(level=logging.INFO)

#constants
AUTOSAVE_NAME = "activedecks.pickle"
AUTOSAVE_INTERVAL = 600
BUCKET = 'capersbot'
AWS_OBJECT = 'activedecks.pickle'
BOT_DEV = os.getenv('BOT_DEV')
TOKEN = os.getenv('DISCORD_TOKEN')


use_aws = False
s3 = ""
if TOKEN is None:
  #if no token, look for env file, assume dev machine, reset constants
  load_dotenv()
  #os.chdir(os.getenv('WORKING'))
  BOT_DEV= os.getenv('BOT_DEV')
  TOKEN = os.getenv('DISCORD_TOKEN')
else:
  #set aws, open client
  use_aws = True
  s3 = boto3.client('s3')

import enum
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
  def __init__(self, suit:enum, rank:enum, stack:str, up:bool = False):
    self.suit = suit
    self.rank = rank
    self.stack = stack
    self.up = up
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
    init_up = False
    for s in suits:
      for r in ranks:
        self.cards.append(Card(suit=s, rank=r, stack=init_stack, up=init_up))
    self.cards.append(Card(suit=Suit.JOKER,rank=Rank.GOOD,stack='Draw', up=False))
    self.cards.append(Card(suit=Suit.JOKER,rank=Rank.BAD,stack='Draw', up=False))
     
  def reshuffle(self):
    random.shuffle(self.cards)
    for c in self.cards:
      c.up = False
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
  #    print(c.long_name() + " in: " + c.stack + ". Is up card: " + str(c.up))

  def clear_last(self):
    for c in self.cards:
      c.up = False

  def flip(self):
    #pass over deck until a Draw card is found
    for i in range(len(self.cards)):
      c = self.cards[i]
      if c.stack == "Draw":
        self.clear_last()
        c.up = True
        c.stack = "Discard"
        return c
    return None

  def sleeve(self) ->tuple[str, Card]:
      sleeve = self.pile(attribute="Stack", member = "Sleeve", sort=False, reverse=False)
      if sleeve == []:
        for c in self.cards:
          if c.up == True:
            c.up = False
            c.stack = "Sleeve"
            return ("success", c)
        return ("fail", None)
      else:
        return ("full", sleeve)

  def unsleeve(self) ->Card:
      sleeve = self.pile(attribute="Stack", member = "Sleeve", sort=False, reverse=False)
      if sleeve is None:       
        return None
      else:
        for c in self.cards:
          if c.stack == "Sleeve":
            c.stack = "Discard"
            self.clear_last()
            c.up = True
        return sleeve

  def nuke(self) -> tuple:
    #returns a 2 member tuple with a bool and a Card object or None
    for c in self.cards:
        if c.up == True:
          c.up = False
          c.stack = "Destroyed"
          return (True, c)
    return (False, None)

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

#create card image embeds    
#todo:check if this can move to Card
def embed(name) ->tuple:
  file = discord.File(fp="./cardimages/"+name, spoiler=False, filename=name)
  embed = discord.Embed()
  embed.set_image(url="attachment://"+name)
  return (file, embed)

#Back up to pickle structure
import pickle
active_decks ={}
pickle_problem = False

def load_backup():
  global active_decks
  global pickle_problem
  #pull aws copy first
  if use_aws == True:
    try:
      print("pulling from aws")
      with open(AUTOSAVE_NAME, 'wb') as f:
        s3.download_fileobj(BUCKET, AWS_OBJECT, f)
    except ClientError as e:
      print (e)
      pickle_problem = True
      
  try:
    #read the local file into active_decks
    print("reading file")
    print(active_decks.values)
    with open(AUTOSAVE_NAME, "rb") as ad:
      active_decks = pickle.load(ad)
    print(active_decks.values)
  except (OSError, IOError) as e:
    #create a blank file if one is missing
    print("error, creating blank file")
    print(e)
    with open(AUTOSAVE_NAME, "wb") as ad:
      pickle.dump(active_decks, ad)
  except EOFError as e:
    #this is fine
    print("error, reverting to blank dictionary")
    print(e)
    active_decks = {}
  except Exception as e:
    #this is a problem
    print("big error, reverting to blank dictionary")
    active_decks = {}
    pickle_problem = True
    print (e)

#backup to pickle
async def backup(seconds=1):
    while True:
      print("Saving")      
      with open(AUTOSAVE_NAME, "wb") as f:
        pickle.dump(active_decks,f)
      if use_aws == True:
        print("uploading to aws")
        with open(AUTOSAVE_NAME, "rb") as f:
          s3.upload_fileobj(f, BUCKET, AWS_OBJECT)
      await asyncio.sleep(seconds)
def backup_now():
  print("Saving")
  with open(AUTOSAVE_NAME, "wb") as f:
    pickle.dump(active_decks,f)
  if use_aws == True:
    print("uploading to aws")
    with open(AUTOSAVE_NAME, "rb") as f:
      s3.upload_fileobj(f, BUCKET, AWS_OBJECT)

#load backup before opening bot connections, register backup on exit
load_backup()
atexit.register(backup_now)
print("all prebot is ready")

#check
def from_guild(ctx):
    return ctx.guild is not None

#bot setup
# Change the no_category default string
help_command = commands.DefaultHelpCommand(
    no_category = 'Commands')
# set intents
#intents = discord.Intents(messages=True, guilds=True, members=True)
#set bot
bot = commands.Bot(command_prefix="+")#, intents=intents)

@bot.event
async def on_ready():
  print("onready")
  dev = await bot.fetch_user(BOT_DEV)
  bot.loop.create_task(backup(AUTOSAVE_INTERVAL))
  #notify if there was a problem with the pickle
  if pickle_problem:
    await dev.send("there was a pickle problem")
  await dev.send("I have connected, working directory: "+str(os.getcwd()))
#@bot.command(name='soundcheck', help='responds I can still hear you')
#async def echo_back(ctx):
#  response = "I can still hear you, "+ctx.author.name
  
#  await ctx.send(response)
@bot.command(name='build', help='builds or rebuilds your a fresh deck BE CAREFUL')
@commands.guild_only()
async def new_deck(ctx):
  owner=ctx.author.id
  deck = Deck(owner = owner)
  active_decks.update({owner:deck})
  response = "built deck for " + ctx.author.display_name + " with ownerID: "+str(owner)  
  await ctx.send(response)

@bot.command(name='discards', brief='List all your discarded cards', help='Shows a list of your discards using your preferred output. To sort, add the Yes argument')
async def show_discards(ctx, sort="No"):
  owner = ctx.author.id
  deck = active_decks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    #validate sort
    err = ""
    if sort.capitalize() in ("Yes", "True", "Sort", "Sorted"):
      sort = True
    elif sort.capitalize() in ("No", "False", "Unsorted"):
      sort = False
    else:
      err = "You gave an invalid option for sorting. Use Yes or No, default to No. "
      sort 
    #get  discards
    discards = deck.pile(attribute="Stack", member="Discard", sort=sort, reverse=False)
    if len(discards) > 0:
      mode = deck.output_mode
      discards = var_name_cards(pile=discards, mode=mode)
      response = err + ctx.author.display_name+"\'s discards are: "+str(discards)
    else:
      response = err+ ctx.author.display_name + " has no discarded cards."
  await ctx.send(response)

@bot.command(name='flip', brief='Flip the top card of a deck', help='Flips a single card, by default targeting your own deck. You may target another player)
@commands.guild_only()
async def flip(ctx, target:discord.Member = "Me"):
  #check if caller has a deck this is used to set preferences
  err = ""
  p = (None, None)
  deck = active_decks.get(ctx.author.id)
  if deck is None:
    response = "You must build a deck to use this command."
  else:
    mode = deck.output_mode
    image_mode = deck.image_mode
  if target in ["me", "Me", None, ctx.author]: 
    target_user = ctx.author
    owner = ctx.author.id
    owner_display_name = ctx.author.display_name
    subject ="Your"
  else:
    target_user = target
    owner = target_user.id
    owner_display_name = target_user.display_name
    subject = "That"
  if target_user is not None:
    #change deck to targeted deck
    deck = active_decks.get(owner)
    if deck is None:
      response = "No such deck. Use the build command."  
    else:
      c = deck.flip()
      if c is None:
        response = subject + " deck is empty, reshuffle!"
      else:
        response = owner_display_name +"\'s card is: "+c.var_name(mode=mode)
        if image_mode:
          image_name = c.image_name()
          p = embed(image_name)           
        else:
          p = (None, None)        
  await ctx.send(response,file=p[0], embed=p[1])

@flip.error
async def flip_error(ctx, error):
  if isinstance(error, commands.MemberNotFound):
    await ctx.send('I could not find that member')
  
@bot.command(name='sleeve', help='Sleeve the last flipped card')
@commands.guild_only()
async def sleeve(ctx):
  owner = ctx.author.id
  deck = active_decks.get(owner)
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
@commands.guild_only()
async def unsleeve(ctx):
  owner = ctx.author.id
  deck = active_decks.get(owner)
  p = (None, None)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    c = deck.unsleeve()
    if c is None:
      response = "You don't have a sleeved card"
    else:
      mode = deck.output_mode
      response = ctx.author.display_name+" unsleeves their "+c.var_name(mode=mode)
      if image_mode:
        image_name = c.image_name()
        p = embed(image_name)              
  await ctx.send(response,file=p[0], embed=p[1])
@bot.command(name='shuffle', help='Shuffle your discards and draw together')
@commands.guild_only()
async def shuffleup(ctx):
  owner = ctx.author.id
  deck = active_decks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    c = deck.reshuffle()
    response = ctx.author.display_name+" reshuffles their deck"
  await ctx.send(response)

@bot.command(name='nuke', help='nuke your last flipped card')
@commands.guild_only()
async def nuke_card(ctx):
  owner = ctx.author.id
  deck = active_decks.get(owner)
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


@bot.command(name='glance', help='Stats at a glance. Command can be sent by DM')
async def glance(ctx):
  owner = ctx.author.id
  deck = active_decks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    #set output mode
    mode = deck.output_mode
    # count discards
    discardslen = str(len(deck.pile(attribute="Stack",member="Discard", sort=False, reverse=False)))
    # count cards
    drawlen = str(len(deck.pile(attribute="Stack",member="Draw", sort=False, reverse=False)))
    # check sleeves
    sleeves = deck.pile(attribute="Stack", member = "Sleeve", sort=False, reverse=False)
    if sleeves == []:
      sleeves = "nothing up their sleeve"
    else: sleeves = sleeves.var_name(mode=mode) + " up their sleeve"
    # check nuked
    destroyed = deck.pile(attribute="Stack", member="Destroyed", sort=False, reverse=False)
    if destroyed == []:
      destroyed = "no cards"
    else:
      destroyed = str(var_name_cards(pile=destroyed, mode=mode))
    # check for flipped card
    for c in deck.cards:
      if c.up == True:
        up = c.var_name(mode=mode) + " is the last flipped card."
        break
      up = "No card is the last flipped card."
    response = ctx.author.display_name + " has discarded " + discardslen + " cards, has " + drawlen + " cards left in their draw, has destroyed " + destroyed + " and has " + sleeves + ". " + up
  await ctx.send(response)

@bot.command(name='output', brief='change the format of your cards', help='output accepts one argument. Valid arguments are: emoji, long, short. Can be sent by DM' )
async def output_mode(ctx, arg = ""):
  owner = ctx.author.id
  deck = active_decks.get(owner)
  valid = ('Emoji', 'Long', 'Short')
  mode = arg.capitalize()  
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    if mode in valid:
      deck.output_mode = mode
      response = ctx.author.display_name + "'s output mode is now: "+mode
    else:
      response = arg +  " is not a valid option. Please use one of:" +str(valid)
  await ctx.send(response)  
@bot.command(name='images', brief='Show card images or not ', help='On or Off. Images display during flip and discards commands. Can be sent by DM')
async def image_mode(ctx, arg:str = "" ):
  owner = ctx.author.id
  deck = active_decks.get(owner)
  valid = ('On', 'Off')
  mode = arg.capitalize()  
  if deck is None:
    response = "No such deck. Use the build command."
  #elif 
  #  response =   
  else:
    if mode in valid:
      #convert on and off inputs into a boolean
      if mode == "On":
        deck.image_mode = True
      elif mode == "Off":
        deck.image_mode = False
      response = ctx.author.display_name + "'s image output mode is now: "+mode
    else:
      response = arg + " is not a valid option. Please use one of:" +str(valid)
  await ctx.send(response) 

@bot.command(name='peek', brief='Peek the top of a deck', help='without arguments, peek targets your own deck, but you must provide both arguments to target someone else\'s deck.')
@commands.check(from_guild)
async def peek(ctx, count:int = 1, target: discord.Member ="Me"):
  #check if caller has a deck this is used to set preferences
  deck = active_decks.get(ctx.author.id)
  if deck is None:
    response = "you must build a deck to use this command."
  else:
    output_mode = deck.output_mode  
    #target self by default, allow converter to handle the rest
    if target in ["me", "Me", None]: 
      target_user = ctx.author
      owner = ctx.author.id
      owner_display_name = ctx.author.display_name
      subject ="Your"
    else:
      target_user = target
      owner = target_user.id
      owner_display_name = target_user.display_name
      subject = "That"
    #get targeted deck    
    deck = active_decks.get(owner)
    if deck is None:
      response = "No such deck. Use the build command."  
    else:
      mode = deck.output_mode
      image_mode = deck.image_mode
      #get the draw deck
      pile = deck.pile(attribute="Stack", member = "Draw", sort=False, reverse=False)
      #check for empty
      if pile == []:
        response = subject + " deck is empty, reshuffle!"
      #check for too short
      elif len(pile) < count:
        response = subject + " deck doesn't have that many cards left"    
      else:
        #append elements off of the pile and into the deck
        peek_pile = []
        for i in range(count):
          peek_pile.append(pile[i])
        dm = owner_display_name +"\'s top cards are: " + str(var_name_cards(pile=peek_pile, mode=output_mode))
        await ctx.author.send(dm)
        if target_user == ctx.author:
          response = ctx.author.display_name + " peeks at the top " + str(count) + " cards of their own deck"
        else:
          response = ctx.author.display_name + " peeks at the top " + str(count) + " cards of " + owner_display_name + "\'s deck"
  await ctx.send(response)

@peek.error
async def peek_error(ctx, error):
  if isinstance(error, commands.MemberNotFound):
    await ctx.send('I could not find that member')

#@bot.command(name='here', brief='show who is here', help='dev command')
#@commands.guild_only()
#async def who_here(ctx):
#  el = []
#  for member in ctx.guild.members:
#    find_channel_user("tznkai", ctx)
#    el.append(member.display_name)
#  response = "channel: " + ctx.channel.name + "guild members: " + str(len(ctx.guild.members)) + str(el)

#  await ctx.send(response)  
#@output_mode.error
#async def output_mode_error(self, ctx: commands.Context, error: commands.CommandError):
#  if isinstance(error, commands.MissingRequiredArgument):
#    message = "Missing required argument, please supply a mode."
#  else:
#    message = "something went wrong!"
#  await ctx.send(message)

#make this development/standalone build only somehow
#@bot.command(name='save', brief='force the bot to save data', help='forces the bot to save data')
#async def man_save(ctx):
#  response = "done"
#  backup()
#  await ctx.send(response)

#@bot.command(name='show', help='outputs the contents of a deck to console for debugging purposes only')
#async def show_deck(ctx):
#  owner = ctx.author.id
#  deck = active_decks.get(owner)
#  if deck is None:
#    response = "No such deck. Use the build command."  
#  else:
#    response = "Outputting deck "+str(owner)+" to console"
#    deck.show()
#  await ctx.send(response)

bot.run(TOKEN)

