# CapersBot.py
import logging
import pickle
import asyncio
from typing import Type
#from botocore.exceptions import ClientError
import discord
from discord import app_commands
from discord.ext import commands
import boto3
from dotenv import load_dotenv
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
  TEST_GUILD = discord.Object(id=os.getenv('TEST_GUILD'))

else:
  #set aws, open client
  use_aws = True
  s3 = boto3.client('s3')
  TEST_GUILD = None

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
class AClient(discord.Client):
  def __init__(self, *, intents: discord.Intents):
    super().__init__(intents=intents)
    self.tree = app_commands.CommandTree(self)
  async def setup_hook(self):
      # This copies the global commands over to your guild
      if TEST_GUILD is not None:
        self.tree.copy_global_to(guild=TEST_GUILD)
      await self.tree.sync(guild=TEST_GUILD)
      print("sync command sent.")  
intents = discord.Intents.default()
client = AClient(intents=intents)


@client.event
async def on_ready():
  print(f"We have logged in as {client.user}.")  
  dev = await client.fetch_user(BOT_DEV)
  client.loop.create_task(backup(AUTOSAVE_INTERVAL))
  #notify if there was a problem with the pickle
  if pickle_problem:
    await dev.send("there was a pickle problem")
  await dev.send("I have connected, working directory is "+str(os.getcwd()) + " I'm in " + str(len(client.guilds)) + " servers!")
  
#  await interaction.response.send_message(response)
@client.tree.command(name='build', description='builds or rebuilds you a fresh deck. This eliminates all of your preferences.')
@app_commands.guild_only()
async def new_deck(interaction: discord.Interaction):
  owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
  deck = Deck(owner = owner)
  active_decks.update({owner:deck})
  response = "built deck for " + interaction.user.display_name + " with ownerID: "+owner
  await interaction.response.send_message(response)

@client.tree.command(name='discards', description='Shows a list of your discards using your image setting. Set Sort to Yes to sort.')
@app_commands.describe(sort='Yes or No, defaults to No.')
@app_commands.guild_only()
async def show_discards(interaction: discord.Interaction, sort: str ='No'):
  p = (None,None)
  owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
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
        response = "Your image mode is set incorrectly. Use /image"
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
        response = err + interaction.user.display_name+"\'s discards are: "+str(discards)      
    else:
      response = err+ interaction.user.display_name + " has no discarded cards."
    if p[0] is None:
      await interaction.response.send_message(response, ephemeral = True)
    else:
      await interaction.response.send_message(response,file=p[0], embed=p[1], ephemeral=True)
  
    

@client.tree.command(name='flip', description='Flips a single card, by default targeting your own deck. You may target another player')
@app_commands.rename(target='player')
@app_commands.describe(target="A player\'s nick. You may leave blank to target your own deck")
@app_commands.guild_only()
async def flip(interaction: discord.Interaction, target:discord.Member = None ):
  #check if caller has a deck this is used to set preferences
  err = ""
  p = (None, None)
  deck = active_decks.get(str(interaction.channel_id) + "_" + str(interaction.user.id))
  if deck is None:
    response = "You must build a deck to use this command."
  else:
    mode = deck.output_mode
    image_mode = deck.image_mode
    print(image_mode)
  if target is None: 
    target_user = interaction.user
    owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
    owner_display_name = interaction.user.display_name
    subject ="Your"
  else:
    target_user = target
    owner = str(interaction.channel_id) + "_" + str(target.id)
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
  if p[0] is None:
    await interaction.response.send_message(response)
  else:
    await interaction.response.send_message(response,file=p[0], embed=p[1])

@flip.error
async def flip_error(interaction, error):
  if isinstance(error, commands.MemberNotFound):
    await interaction.response.send_message('I could not find that member')
  
@client.tree.command(name='sleeve', description= 'Put the top of the discards in your sleeve, use the unsleeve command later.')
@app_commands.guild_only()
async def sleeve(interaction: discord.Interaction):
  owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
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
      response = interaction.user.display_name+" sleeves their "+s[1].var_name(mode=mode)
  await interaction.response.send_message(response)

@client.tree.command(name='unsleeve', description= 'Unsleeve the top of your discard. This becomes the top of the discard if you made a mistake.')
@app_commands.guild_only()
async def unsleeve(interaction: discord.Interaction):
  owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
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
      response = interaction.user.display_name+" unsleeves their "+c.var_name(mode=mode)
      if image_mode in ('On', 'Large'):
        bo = cardimages.single(c)
        p = embed_bytes(bo)     
      elif image_mode == 'Small':
        bo = cardimages.single(c,divisor=CARD_DIVISOR)
        p = embed_bytes(bo)
      else:
        p = (None, None)                  
  if p[0] is None:
    await interaction.response.send_message(response)
  else:
    await interaction.response.send_message(response, file=p[0], embed=p[1])

@client.tree.command(name='shuffle', description='Shuffles the draw and discards, leaving sleeve cards and destroyed cards in sleeve and destroyed.')
@app_commands.guild_only()
async def shuffleup(interaction: discord.Interaction):
  owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
  deck = active_decks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    c = deck.reshuffle()
    response = interaction.user.display_name+" reshuffles their deck"
  await interaction.response.send_message(response)

@client.tree.command(name='nuke', description='Destroys the top card of your discard. For use with the call the gloam power. Reset with /build')
@app_commands.guild_only()
async def nukecard(interaction: discord.Interaction):
  owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
  deck = active_decks.get(owner)
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    c = deck.nuke()
    if c is None:
      response = "Nothing to nuke, you can only nuke the top of the discards"      
    else:
      mode = deck.output_mode
      response = interaction.user.display_name+" nukes their "+c.var_name(mode=mode)
  await interaction.response.send_message(response)


@client.tree.command(name='glance', description='Stats at a glance.')
@app_commands.guild_only()
async def glance(interaction: discord.Interaction):
  owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
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
    response = interaction.user.display_name + " has discarded " + discardslen + " cards, has " + drawlen + " cards left in their draw, has destroyed " + destroyed + " and has " + sleeves + ". " + up
  await interaction.response.send_message(response, ephemeral=True)

@client.tree.command(name='output', description='Change how cards are displayed in text')
@app_commands.describe(arg = "emoji, long, short.")
@app_commands.rename(arg = "style")
@app_commands.guild_only()
async def output_mode(interaction: discord.Interaction, arg: str):
  owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
  deck = active_decks.get(owner)
  valid = ('Emoji', 'Long', 'Short')
  mode = arg.capitalize()  
  if deck is None:
    response = "No such deck. Use the build command."  
  else:
    if mode in valid:
      deck.output_mode = mode
      response = interaction.user.display_name + "'s output mode is now: "+mode
    else:
      response = arg +  " is not a valid option. Please use one of:" +str(valid)
  await interaction.response.send_message(response)  

@client.tree.command(name='images', description='Controls whether card images are shown when using the flip and discards command.')
@app_commands.describe(arg = "Large, Small, or Off")
@app_commands.rename(arg = "image_mode")
@app_commands.guild_only()
async def image_mode(interaction: discord.Interaction, arg: str):
  owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
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
      response = interaction.user.display_name +  "'s image output mode is now: "+mode
    else:
      response = arg + " is not a valid option. Please use one of:" +str(valid)
  await interaction.response.send_message(response, ephemeral=True) 

@client.tree.command(name='peek', description='glances at the top COUNT cards off the top of a draw deck')
@app_commands.guild_only()
@app_commands.describe(count = "number of cards you want to view", target = "which player\'s deck you want to target")
@app_commands.rename(target = "player")
async def peek(interaction: discord.Interaction, count:int = 1, target: discord.Member =None):
  #check if caller has a deck this is used to set preferences
  deck = active_decks.get(str(interaction.channel_id) + "_" + str(interaction.user.id))
  response = None
  if deck is None:
    private_response = "you must build a deck to use this command."
  else:
    output_mode = deck.output_mode
    #target self by default, allow converter to handle the rest
    if target is None: 
      target_user = interaction.user
      owner = str(interaction.channel_id) + "_" + str(interaction.user.id)
      owner_display_name = interaction.user.display_name
      subject ="Your"
    else:
      target_user = target
      owner = str(interaction.channel_id) + "_" + str(target.id)
      owner_display_name = target_user.display_name
      subject = "That"
    #get targeted deck    
    deck = active_decks.get(owner)
    if deck is None:
      private_response = "No such deck. Use the build command."  
    else:
      #get the draw deck
      pile = deck.pile(attribute="Stack", member = "Draw", sort=False, reverse=False)
      #check for empty
      if pile == []:
        private_response = subject + " deck is empty, reshuffle!"
      #check for too short
      elif len(pile) < count:
        private_response = subject + " deck doesn't have that many cards left"    
      else:
        #append elements off of the pile and into the deck
        peek_pile = []
        for i in range(count):
          peek_pile.append(pile[i])
        private_response = owner_display_name +"\'s top cards are: " + str(capersdecks.var_name_cards(pile=peek_pile, mode=output_mode))
        if target_user == interaction.user:
          response = interaction.user.display_name + " peeks at the top " + str(count) + " cards of their own deck"
        else:
          response = interaction.user.display_name + " peeks at the top " + str(count) + " cards of " + owner_display_name + "\'s deck"
  await interaction.response.send_message(private_response, ephemeral=True)
  if response is not None:
    await client.get_channel(interaction.channel_id).send(response)

@peek.error
async def peek_error(interaction: discord.Interaction, error):
  if isinstance(error, commands.MemberNotFound):
    await interaction.response.send_message('I could not find that member')

#@client.tree.command(name='here', brief='show who is here', description='dev command')
#@app_commands.guild_only()
#async def who_here(ctx):
#  el = []
#  for member in ctx.guild.members:
#    find_channel_user("tznkai", ctx)
#    el.append(member.display_name)
#  response = "channel: " + ctx.channel.name + "guild members: " + str(len(ctx.guild.members)) + str(el)

#  await interaction.response.send_message(response)  
#@output_mode.error
#async def output_mode_error(self, ctx: commands.Context, error: commands.CommandError):
#  if isinstance(error, commands.MissingRequiredArgument):
#    message = "Missing required argument, please supply a mode."
#  else:
#    message = "something went wrong!"
#  await interaction.response.send_message(message)

#make this development/standalone build only somehow
#@bot.command(name='save', brief='force the bot to save data', description='forces the bot to save data')
#async def man_save(ctx):
#  response = "done"
#  backup()
#  await interaction.response.send_message(response)

#@bot.command(name='show', description='outputs the contents of a deck to console for debugging purposes only')
#async def show_deck(ctx):
#  owner = ctx.author.id
#  deck = active_decks.get(owner)
#  if deck is None:
#    response = "No such deck. Use the build command."  
#  else:
#    response = "Outputting deck "+str(owner)+" to console"
#    deck.show()
#  await interaction.response.send_message(response)

client.run(TOKEN)

