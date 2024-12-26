import discord
from discord.ext import commands
import os
import time
import win32com.client
import asyncio
import eyed3
from mutagen.id3 import ID3, APIC
import logging


logging.getLogger('discord.player').setLevel(logging.CRITICAL)
logging.getLogger('discord.voice_state').setLevel(logging.CRITICAL)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="$", intents=intents)

@bot.event
async def on_message(ctx):
    if ctx.author == bot.user:
        return
    
    if "music" in ctx.content.lower():
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            voice_client = await channel.connect()
        else:
            await ctx.channel.send("Not in vc")
            return
        
        # Connect to iTunes COM interface
        try:
            itunes = win32com.client.Dispatch("iTunes.Application")
        except:
            await ctx.channel.send("Music player not opened")
            return
        
        prev = ""
        paused = False
        warned = False
        first = True
        finished = False
        prev_position = 0
        just_opened = True
        
        while True:
            track = itunes.CurrentTrack

            player_state = itunes.PlayerState
            
            if player_state == 0 and not paused: #paused
                print("paused")
                voice_client.pause()
                # playback_state[ctx.guild.id]["paused"] = True
                paused = True
            
            if paused:
                if player_state == 1: #playing
                    voice_client.resume()
                    # playback_state[ctx.guild.id]["paused"] = False
                    paused = False
            
            #switch tracks and send embed
            if track and player_state == 1:
                file_path = track.Location
                if file_path != prev:
                    # dont know if this will work =============================
                    print(f"Current track: {file_path}")
                    prev = file_path
                    
                    #play song
                    voice_client.stop()
                    player_position = itunes.PlayerPosition
                    voice_client.play(discord.FFmpegPCMAudio(
                        source=file_path,
                        before_options=f"-ss {player_position}"
                    ))
                    
                    #get song metadata
                    audio_file = eyed3.load(file_path)
                    title = audio_file.tag.title or 'Unknown Title'
                    artist = audio_file.tag.artist or 'Unknown Artist'
                    
                    album_cover = None
                    if audio_file.tag.images:
                        # print("Found album cover")
                        album_cover = audio_file.tag.images[0].data
                        
                    audio = ID3(file_path)
                    for tag in audio.values():
                        if isinstance(tag, APIC):
                            album_cover = tag.data
                            with open(r"Discord\Bobbeth Beats\album.png", 'wb') as f:
                                f.write(album_cover)
                            # print(f"Album cover saved to {output_path}")
                            
                    #create embed
                    embed = discord.Embed(title="Now Playing:", color=discord.Color.blue())
                    embed.add_field(name=title, value=artist, inline=False)
                    
                    if album_cover is not None:
                        # Attach the local image file
                        file = discord.File(r"Discord\Bobbeth Beats\album.png", filename="album.png")
                        
                        # Set the image URL in the embed
                        embed.set_thumbnail(url="attachment://album.png")
                    else:
                        file = None
                    
                    # Send the embed
                    if first:
                        message = await ctx.channel.send(embed=embed, file=file)
                        stored_message_id = message.id
                        first = False
                    else:
                        #delete and send new message
                        message = await ctx.channel.fetch_message(stored_message_id)
                        await message.delete()
                        message = await ctx.channel.send(embed=embed, file=file)
                        stored_message_id = message.id
                    
                    warned = False
                    finished = False
                    prev_position = 0

            else:
                if not warned:
                    print("No track is currently selected or playing.")
                    warned = True
                    if just_opened and player_state == 0:
                        itunes.Play()
                        just_opened = False
            
            # update player position
            if player_state == 1:
                player_position = itunes.PlayerPosition
                if abs(player_position - prev_position) > 3:
                    print("updating position")
                    
                    voice_client.stop()
                    voice_client.play(discord.FFmpegPCMAudio(
                        source=file_path,
                        before_options=f"-ss {player_position}"
                    ))
                prev_position = player_position
            
            # pause song on player if song not done playing
            if not voice_client.is_playing() and player_state == 1 and not finished:
                print("done playing")
                finished = True
            
            #get remaining time
            if player_state == 1:
                duration = track.Duration
                player_position = itunes.PlayerPosition
                remaining_time = duration - player_position
                
                if remaining_time <= 0.5 and not finished:
                    # print("going back")
                    new_position = player_position - 0.5
                    itunes.PlayerPosition = new_position
            
            #add delay to not overwhelm
            await asyncio.sleep(0.1)
    
    if "leave" in ctx.content.lower():
        voice_client = message.guild.voice_client

        if voice_client:
            await voice_client.disconnect()
            itunes = None
        else:
            await ctx.channel.send("not in vc")
        

with open(r"Discord\Bobbeth Beats\token.txt") as file:
    token = file.read()

bot.run(token)
