import discord
import Augmentor
from discord.ext import commands
from discord.utils import get
from PIL import ImageFont, ImageDraw, Image

from modules.logger import *
from modules.pools import *
from modules.globals import *
#from modules.captcha import *
from modules.hashrate import *
from modules.difficulty import *

intents = discord.Intents.all()
client = commands.Bot(intents=intents, command_prefix=config["bot_prefix"])

client.add_command(pools)
client.add_command(hashrate)
client.add_command(difficulty)

@client.event
async def on_message(message):
	#if author is bot return
	if message.author.id == client.user.id:
		return
	await client.process_commands(message)

@client.event
async def on_ready():
	global channel, pools_msg
	Log("Client connected as " + client.user.name + ' (' + str(client.user.id) + ')')
	try:
		channel = client.get_channel(config["stats_channel"])
		Log("Stats channel hooked")
	except:
		Log("Stats channel doesn't exist", ERROR)
		return
	try:
		pools_msg = await channel.fetch_message(channel.last_message_id) #Dawaj kurwa ostatnia wiadomosc
		Log("Stats message fetched")
	except:
		try:
			pools_msg = await channel.send('Init message')
			Log("Channel initilized")
		except:
			Log("Everything fucked up, suicide yourself", ERROR)
			return
		pass
		
	while True:
		await UpdateData()
		await asyncio.sleep(config["update_interval"])
		
'''@client.event
async def on_member_join(member):
	await captcha(client, member)
'''
async def UpdateData():
	Log("Querying APIs")
	#Updating data from APIs
	try:
		networkQuery = requests.get("http://80.60.19.222:38302/get_info")
		if networkQuery.status_code == 200:
			Globals['networkInfo'] = networkQuery.json()
			Globals['networkInfo']['height'] -= 1
			Log("Network OK")
		else:
			Log("Network fucked up", ERROR)
			return
		networkQuery = requests.get("http://80.60.19.222:38302/get_transaction_pool_stats")
		if networkQuery.status_code == 200:
			Globals['txpool'] = networkQuery.json()
			Log("Transaction pool OK")
		else:
			Log("Transaction pool fucked up", ERROR)
			return
		networkQuery = requests.get("http://mrl.stx.nl:8081/api/emission")
		if networkQuery.status_code == 200:
			Globals['emission'] = networkQuery.json()
			Log("Emission OK")
		else:
			Log("Emission fucked up", ERROR)
			return
		networkQuery = requests.get("http://mrl.stx.nl:8081/api/rawblock/" + str(Globals['networkInfo']['height']))
		if networkQuery.status_code == 200:
			Globals['topblock'] = networkQuery.json()
			Log("Top block OK")

		else:
			Log("Top block fucked up", ERROR)
			return
	except:
		Log("Update data failed", ERROR)
		return
	try:
		priceQuery = requests.get("https://xeggex.com/api/v2/asset/getbyticker/MRL")
		if priceQuery.status_code == 200:
			Globals['moreloInfo'] = priceQuery.json()
		'''
		priceQuery = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=morelo&vs_currencies=btc")
		if priceQuery.status_code == 200:
			Globals['moreloInfo'][1] = priceQuery.json()
		priceQuery = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=morelo&vs_currencies=eth")
		if priceQuery.status_code == 200:
			Globals['moreloInfo'][2] = priceQuery.json()
		'''
		Log("Price OK")
	except:
		Log("Price fucked up", ERROR)
		return	
	try:
		#miningpoolstats.stream API hack
		poolsQuery = requests.get("http://miningpoolstats.stream/morelo")
		if poolsQuery.status_code == 200:
			token = re.search('var last_time = "([^"]+)"', poolsQuery.text).group(1)
			poolsQuery = requests.get("http://data.miningpoolstats.stream/data/morelo.js", params={'t': token}, headers={'User-Agent': 'MoreloBOT'})
			if poolsQuery.status_code == 200:
				poolsQuery = poolsQuery.json()
				Globals['poolsInfo'] = sorted(poolsQuery['data'], key = lambda i: i['hashrate'], reverse=True)#Jebana magia sortowania z rewersem
				Log("Pools OK")
	except:
		Log("Pools fucked up", ERROR)
		return
	#Update messages
	pools = ""
	Log("Embed magic...")
	if Globals['poolsInfo']: #Pojebany parser do pooli
		for pool in Globals['poolsInfo']:
			if pool['hashrate'] >= 0:
				pools = pools + pool['url'] + ' (Hashrate: ' + Suffix(pool['hashrate']) +')\n'
	network = "```Hashrate	 : " + Suffix(int(Globals['networkInfo']['difficulty']) / 120) + \
	"\nHeight	   : " + str(Globals['networkInfo']['height']) + \
	"\nEmission	 : %.2f MRL" % (Globals['emission']['data']['coinbase'] / 1000000000) + \
	"\nBlock Reward : %.4f MRL" % (Globals['topblock']['data']['miner_tx']['vout'][0]['amount'] / 1000000000) + \
	"\nDifficulty   : " + str(Globals['networkInfo']['difficulty']) + \
	"\nPending Tx's : " + str(Globals['txpool']['pool_stats']['txs_total']) + \
	"\nBlock Hash   : " + Globals['networkInfo']['top_block_hash'][:10] + "...```"
	prices = "```24H Volume : Unknown" + \
	"\n24H Change : Unknown" + \
	"\n\nUSD $		: " + Globals['moreloInfo']['usdValue'] + "```"
	embed=discord.Embed(color=0xf78803)
	embed.set_thumbnail(url="https://raw.githubusercontent.com/MoreloNetwork/Graphical-Assets/master/MRL-512.png")
	embed.add_field(name="Network statistics", value=network, inline=False)
	embed.add_field(name="Pools statistics", value=pools, inline=False)
	embed.add_field(name="Morelo prices", value=prices, inline=False)
	#TODO add timezone
	embed.set_footer(text="Last update - " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC+2"))
	try:
		await pools_msg.edit(content='', embed=embed)
		Log("Message sent")
	except:
		Log("Message fucked up", ERROR)
		return

client.run(config["access_token"])
