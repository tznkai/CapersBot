# CapersBot.py
import logging
import pickle
import asyncio
from typing import Type
#from botocore.exceptions import ClientError
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
AUTOSAVE_INTERVAL = 43200
BUCKET = 'capersbot'
AWS_OBJECT = 'activedecks.pickle'
BOT_DEV = os.getenv('BOT_DEV')
TOKEN = os.getenv('DISCORD_TOKEN')
CARD_PATH = "./cardimages/"
CARD_DIVISOR = 10


#Use AWS if on Heroku, else do not disturb the pickle file to allow testing
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

#get modules
import capersdecks
from capersdecks import Rank
from capersdecks import Suit
from capersdecks import Card
from capersdecks import Deck
import cardimages


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

#image maker - at runtime, takes open source cards and makes image lefts.
#ingests a list of cards and constructs an image

#Discord related functions:
#checks
def from_guild(ctx):
    return ctx.guild is not None

#embed bytes objects
def embed_bytes(bo):
  bo.seek(0)
  f = discord.File(bo, spoiler=False, filename='embed.png')
  embed = discord.Embed()
  embed.set_image(url="attachment://"+'embed.png')
  print(f)
  print(f.filename)
  return (f, embed)

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
  await dev.send("I have connected, working directory is "+str(os.getcwd()) + " I'm in " + str(len(bot.guilds)) + " servers!")
#@bot.command(name='soundcheck', help='responds I can still hear you')
#async def echo_back(ctx):
#  response = "I can still hear you, "+ctx.author.name
  
#  await ctx.send(response)
@bot.command(name='build', brief='Do this once', help='builds or rebuilds you a fresh deck. This eliminates all of your preferences.')
@commands.guild_only()
async def new_deck(ctx):
  owner=ctx.author.id
  deck = Deck(owner = owner)
  active_decks.update({owner:deck})
  response = "built deck for " + ctx.author.display_name + " with ownerID: "+str(owner)  
  await ctx.send(response)

@bot.command(name='discards', brief='List all your discarded cards', help='Shows a list of your discards using your preferred output. To sort, add the Yes argument')
async def show_discards(ctx, sort="No"):
  p = (None,None)
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
      image_mode = deck.image_mode
      valid = image_mode in ('On', 'Large', 'Small')
      if not valid:
        response = "Your image mode is set incorrectly. Use +help images to find the right setting"
      else:
        if image_mode in ('On', 'Large'):
          divisor = 1
        elif image_mode == 'Small':
          divisor = CARD_DIVISOR
        else:
          err = "something has gone extremely wrong with the image builder"
        bo = cardimages.splay(discards, bo=True, divisor=divisor)
        p = embed_bytes(bo)
        discards = capersdecks.var_name_cards(pile=discards, mode=mode)
        response = err + ctx.author.display_name+"\'s discards are: "+str(discards)      
    else:
      response = err+ ctx.author.display_name + " has no discarded cards."
  await ctx.send(response,file=p[0], embed=p[1])

@bot.command(name='flip', brief='Flip the top card of a deck', help='Flips a single card, by default targeting your own deck. You may target another player')
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
    print(image_mode)
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
        if image_mode in ('On', 'Large'):
          bo = cardimages.single(c, divisor = 1)
          p = embed_bytes(bo)     
        elif image_mode == 'Small':
          bo = cardimages.single(c,divisor=CARD_DIVISOR)
          p = embed_bytes(bo)    
        else:
          p = (None, None)        
  await ctx.send(response,file=p[0], embed=p[1])

@flip.error
async def flip_error(ctx, error):
  if isinstance(error, commands.MemberNotFound):
    await ctx.send('I could not find that member')
  
@bot.command(name='sleeve', brief='Sleeve the top of the discards', help = 'Put the top of the discards in your sleeve, use the unsleeve command later. Maximum one in a sleeve, does not dynamically track the top of your discard.')
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
      response = "Nothing to sleeve, you can only sleeve the top of the discards"
    else:
      response = ctx.author.display_name+" sleeves their "+s[1].var_name(mode=mode)
  await ctx.send(response)

@bot.command(name='unsleeve', brief='Unsleeve the top of the discards', help = 'Unsleeve the top of the discards. This becomes the top of the discard if you made a mistake.')
@commands.guild_only()
async def unsleeve(ctx):
  owner = ctx.author.id
  deck = active_decks.get(owner)
  p = (None, None)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    image_mode = deck.image_mode
    c = deck.unsleeve()
    if c is None:
      response = "You don't have a sleeved card"
    else:
      mode = deck.output_mode
      response = ctx.author.display_name+" unsleeves their "+c.var_name(mode=mode)
      if image_mode in ('On', 'Large'):
        bo = cardimages.single(c)
        p = embed_bytes(bo)     
      elif image_mode == 'Small':
        bo = cardimages.single(c,divisor=CARD_DIVISOR)
        p = embed_bytes(bo)
      else:
        p = (None, None)                  
  await ctx.send(response,file=p[0], embed=p[1])
@bot.command(name='shuffle', brief='Shuffle your discards and draw together', help='Shuffles the draw and discards, leaving sleeve cards and destroyed cards in sleeve and destroyed. You will notice the order of the destroyed cards changes, this is normal.')
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

@bot.command(name='nuke', brief= "destroy the top card of your discard", help='Destroys the top card of your discard. For use with the call the gloam power. Use glance to see what cards you have destroyed. Can only be reset by rebuilding your deck.')
@commands.guild_only()
async def nuke_card(ctx):
  owner = ctx.author.id
  deck = active_decks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    c = deck.nuke()
    if c is None:
      response = "Nothing to nuke, you can only nuke the top of the discards"      
    else:
      mode = deck.output_mode
      response = ctx.author.display_name + " nukes their "+c.var_name(mode=mode)
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
    discards = deck.pile(attribute="Stack",member="Discard", sort=False, reverse=False)
    if len(discards) == 0:
      discardslen = "no"
      up = ""
    else:
      discardslen = str(len(discards))
      up = "The top card of the discard is a " + str(discards[0].var_name(mode=mode))
    # count deck cards
    drawlen = str(len(deck.pile(attribute="Stack",member="Draw", sort=False, reverse=False)))
    # check sleeve
    sleeves = deck.pile(attribute="Stack", member = "Sleeve", sort=False, reverse=False)
    if sleeves == []:
      sleeves = "nothing up their sleeve"
    else: sleeves = sleeves[0].var_name(mode=mode) + " up their sleeve"
    # check nuked
    destroyed = deck.pile(attribute="Stack", member="Destroyed", sort=False, reverse=False)
    if destroyed == []:
      destroyed = "no cards"
    else:
      destroyed = str(capersdecks.var_name_cards(pile=destroyed, mode=mode))
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
@bot.command(name='images', brief='Show card images or not ', help='Large, Small, or Off. Images display during flip and discards commands. Can be sent by DM')
async def image_mode(ctx, arg:str = "" ):
  owner = ctx.author.id
  deck = active_decks.get(owner)
  valid = ('Large', 'Small', 'Off')
  mode = arg.capitalize()  
  if deck is None:
    response = "No such deck. Use the build command."
  #elif 
  #  response =   
  else:
    if mode in valid:
      deck.image_mode = mode
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
        dm = owner_display_name +"\'s top cards are: " + str(capersdecks.var_name_cards(pile=peek_pile, mode=output_mode))
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

