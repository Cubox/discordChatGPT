from dotenv import load_dotenv
import os
from revChatGPT.V1 import AsyncChatbot

import discord
from discord import app_commands

load_dotenv()


botInstances = dict()


class CustomClient(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.activity = discord.Activity(type=discord.ActivityType.watching, name="you")


client = CustomClient()


@client.event
async def on_ready():
    await client.tree.sync()
    print(f"We have logged in as {client.user}")


@client.tree.command(name="rollback", description="Rollback the conversation")
async def rollback(interaction: discord.Interaction, *, amount: int):
    if interaction.user.id in botInstances:
        botInstances[interaction.user.id].rollback(amount)
    await interaction.response.defer(ephemeral=False)
    await interaction.followup.send(
        discord.Embed(
            description="The conversation has been rolled back {} times".format(amount),
            title="Rollback",
        )
    )


@client.tree.command(name="reset", description="Reset the conversation")
async def reset(interaction: discord.Interaction):
    if interaction.user.id in botInstances:
        botInstances[interaction.user.id].reset_chat()
    await interaction.response.defer(ephemeral=False)
    await interaction.followup.send(
        embed=discord.Embed(
            description="Conversation has been reset",
            title="Reset",
        )
    )


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.author.bot:
        return

    if not isinstance(message.channel, discord.TextChannel):
        return

    if client.user in message.mentions:
        async with message.channel.typing():
            dogjam = [
                emoji for emoji in message.guild.emojis if emoji.name == "dogjam"
            ][0]
            await message.add_reaction(dogjam)

            question = message.content.replace(f"<@{client.user.id}>", "").strip()

            author = message.author.id
            if author not in botInstances:
                botInstances[author] = AsyncChatbot(
                    config={
                        "email": os.getenv("OPENAI_EMAIL"),
                        "password": os.getenv("OPENAI_PASSWORD"),
                    }
                )
            bot = botInstances[author]

            responseMessage = ""
            try:
                async for response in bot.ask(question):
                    responseMessage = response["message"]
            except Exception as e:
                print(e)
                await message.reply("Something happened")
                await message.clear_reaction(dogjam)
                await message.add_reaction("👎")
                return

            if len(responseMessage) > 1900:
                # Split the response into smaller chunks of no more than 1900 characters each(Discord limit is 2000 per chunk)
                if "```" in responseMessage:
                    # Split the response if the code block exists
                    parts = responseMessage.split("```")
                    # Send the first message
                    await message.reply(parts[0])

                    # Send the code block in a seperate message
                    code_block = parts[1].split("\n")
                    formatted_code_block = ""
                    for line in code_block:
                        while len(line) > 1900:
                            # Split the line at the 50th character
                            formatted_code_block += line[:1900] + "\n"
                            line = line[1900:]
                        formatted_code_block += (
                            line + "\n"
                        )  # Add the line and seperate with new line

                    # Send the code block in a separate message
                    if len(formatted_code_block) > 2000:
                        code_block_chunks = [
                            formatted_code_block[i : i + 1900]
                            for i in range(0, len(formatted_code_block), 1900)
                        ]
                        for chunk in code_block_chunks:
                            await message.reply("```" + chunk + "```")

                    else:
                        await message.reply("```" + formatted_code_block + "```")

                    # Send the remaining of the response in another message

                    if len(parts) >= 3:
                        await message.reply(parts[2])

                else:
                    response_chunks = [
                        responseMessage[i : i + 1900]
                        for i in range(0, len(responseMessage), 1900)
                    ]
                    for chunk in response_chunks:
                        await message.reply(chunk)
            else:
                await message.reply(responseMessage)

            await message.clear_reaction(dogjam)
            await message.add_reaction("👍")


if __name__ == "__main__":
    client.run(os.getenv("DISCORD_BOT_TOKEN"))
