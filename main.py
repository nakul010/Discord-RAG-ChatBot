import os, re, random, json, calendar, logging, asyncio
import discord
import pytz
import auth_admin
from pathlib import Path
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from keep_alive import keep_alive
from dotenv import load_dotenv
from discord.ext import tasks, commands
from discord.ext.commands.context import Context
from discord import app_commands
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from lucky_picker import pick_lucky_winner, get_random_seed
from ticket_helper import TicketHelper, start_ticket_embed
from tracking import process_embeds, generate_report

# Load environment variables for API keys
load_dotenv()

logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# Constants
EMBEDDINGS_CONFIG_FILE = "embeddings_config.json"
VECTORSTORE_DIR = "vectorstore"


singapore_tz = pytz.timezone("Asia/Singapore")
start_time = singapore_tz.localize(datetime(2024, 12, 17, 0, 0))
end_time = start_time + timedelta(days=1)

# Singapore public holidays (2024 and 2025) to consider
HOLIDAYS = [
    # 2024 holidays
    datetime(2024, 10, 31),  # Deepavali
    datetime(2024, 12, 25),  # Christmas Day
    # 2025 holidays
    datetime(2025, 1, 1),  # New Year's Day
    datetime(2025, 1, 29),  # Chinese New Year
    datetime(2025, 1, 30),  # Chinese New Year
    datetime(2025, 3, 31),  # Hari Raya Puasa
    datetime(2025, 4, 18),  # Good Friday
    datetime(2025, 5, 1),  # Labour Day
    datetime(2025, 5, 12),  # Vesak Day
    datetime(2025, 6, 7),  # Hari Raya Haji
    datetime(2025, 8, 9),  # National Day
    datetime(2025, 10, 20),  # Deepavali (tentative)
    datetime(2025, 12, 25),  # Christmas Day
]


def is_weekend(date: datetime):
    """Check if the date is on a weekend (Saturday or Sunday)."""
    return date.weekday() >= 5


def is_holiday(date: datetime):
    """Check if the date is a holiday."""
    return date in HOLIDAYS


def calculate_withdrawal_date(start_date: datetime, days_to_add: int):
    """Calculate the expected withdrawal date considering weekends and public holidays."""
    current_date = start_date
    days_added = 0

    while days_added < days_to_add:
        current_date += timedelta(days=1)
        if not is_weekend(current_date) and not is_holiday(current_date):
            days_added += 1

    return current_date


def load_documents(file_path):
    """Load documents from a text file."""
    try:
        loader = TextLoader(file_path)
        return loader.load()
    except Exception as e:
        print(f"Error loading documents: {e}")
        return []


def create_or_load_embeddings():
    """Create new embeddings or load existing configuration."""
    if os.path.exists(EMBEDDINGS_CONFIG_FILE):
        with open(EMBEDDINGS_CONFIG_FILE, "r") as f:
            config = json.load(f)
        return GoogleGenerativeAIEmbeddings(**config)
    else:
        config = {"model": "models/embedding-001"}
        embeddings = GoogleGenerativeAIEmbeddings(**config)
        with open(EMBEDDINGS_CONFIG_FILE, "w") as f:
            json.dump(config, f)
        return embeddings


def create_or_load_vectorstore(docs, embeddings):
    """Create new vector store or load existing one."""
    if os.path.exists(VECTORSTORE_DIR):
        return Chroma(persist_directory=VECTORSTORE_DIR, embedding_function=embeddings)
    else:
        vectorstore = Chroma.from_documents(
            documents=docs, embedding=embeddings, persist_directory=VECTORSTORE_DIR
        )
        return vectorstore


def setup_rag_chain():
    """Set up the RAG chain."""
    # Load the cleaned data
    data = load_documents("cleaned_data.txt")
    if not data:
        print("No documents loaded. Please check the file.")
        return None

    # Split the data into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
    docs = text_splitter.split_documents(data)

    # Set up embeddings and vector store
    embeddings = create_or_load_embeddings()
    vectorstore = create_or_load_vectorstore(docs, embeddings)

    retriever = vectorstore.as_retriever(
        search_type="similarity", search_kwargs={"k": 10}
    )

    # Set up the language model for responses
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", temperature=0.3, max_tokens=500
    )

    system_prompt = (
        "You are a helpdesk chatbot designed to provide support using relevant articles from the Stackup Help Center. Your role is to:\n"
        "1. Provide solutions by retrieving and referencing information from the knowledge base articles.\n"
        "2. Answer queries based on factual and relevant content from these articles.\n"
        "3. Guide users through step-by-step troubleshooting and reference related articles.\n"
        "4. Please ensure accuracy in your responses and avoid any assumptions. Only provide information that is explicitly mentioned in the articles provided.\n"
        "5. Structure responses clearly by summarizing key points from articles, providing article links for more details, and using a helpful, professional tone.\n"
        "6. If unsure, suggest the user seeks further help from the server's moderator if an article does not cover their issue.\n"
        "7. Please format all links as [text](URL) without any additional attributes, and create a descriptive text for each link.\n"
        "8. If a user asks to calculate an estimated date for withdrawal, kindly inform them to use the `</calculate_withdrawal:1305242443477815359>` command. For all other inquiries related to withdrawal, respond in accordance with your usual process.\n"
        "9. Be grammatically correct.\n\n"
        "10. The articles are structured as follows: \n"
        "  - Title: This is the title of the article.\n"
        "  - URL: This is the URL to access the article online.\n"
        "  - Body: This is the detailed content of the article, containing the full information, instructions, and related steps.\n"
        "{context}"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    # Create the retrieval chain
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain


def get_answer(question, rag_chain):
    """Retrieve an answer to the given question using RAG."""
    response = rag_chain.invoke({"input": question})
    return response.get("answer", "I don't know.")


# Set up Discord bot
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler()


@bot.event
async def on_ready():
    keep_alive()
    logging.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logging.info(e)
    logging.info("------")
    global rag_chain
    rag_chain = setup_rag_chain()
    scheduler.add_job(start_tracking, DateTrigger(run_date=start_time))
    scheduler.add_job(stop_tracking, DateTrigger(run_date=end_time))
    scheduler.start()


@bot.event
async def on_message(message: discord.Message):
    current_time = datetime.now(singapore_tz)
    if start_time < current_time < end_time:
        if (
            message.channel.id == 954580346945544302
            and message.author.id == 950425192017039401
        ):
            logging.info(f"Processing message from {message.author} (ID: {message.id})")
            await asyncio.sleep(2)
            if message.embeds:
                await process_embeds(message.embeds, message.id)
            elif message.flags.value == 128:
                logging.info("Message loading (flag 128). Attempting to fetch...")
                try:
                    full_message = await message.channel.fetch_message(message.id)
                    if full_message.embeds:
                        logging.info("Fetched embeds from suppressed message.")
                        await process_embeds(full_message.embeds, message.id)
                except discord.NotFound:
                    logging.info("Message not found.")
                except discord.Forbidden:
                    logging.info("Permission denied when fetching the message.")
                except Exception as e:
                    logging.info(f"Unexpected error: {e}")
            else:
                logging.info(
                    f"Embeds not found in {message.id} sent by {message.author}"
                )


async def start_tracking():
    """Start tracking user activity."""
    logging.info("DAY 2: DECEMBER GRIND tracking has started")
    users = [735548895878185001, 890986684580233216]
    for user in users:
        user = await bot.fetch_user()
        await user.send("DAY 2: DECEMBER GRIND tracking has started")


async def stop_tracking():
    """Stop tracking and generate a report."""
    logging.info("DAY 2: DECEMBER GRIND tracking has ended")

    users = [735548895878185001, 890986684580233216]

    for user in users:
        user = await bot.fetch_user(users)
        await user.send(
            "DAY 2: DECEMBER GRIND tracking has ended. Report will be generated in <#1092443920576807024>"
        )

    milestone_achieved_report, milestone_not_achieved_report = await generate_report()

    coin_transfer_channel_id = 1092443920576807024
    coin_transfer_channel = bot.get_channel(coin_transfer_channel_id)
    if coin_transfer_channel:
        await coin_transfer_channel.send(
            f"\n# DAY 2: DECEMBER GRIND REPORT\n\n### <:StackUp:935796086231171112> <:yaycoin:1076423261572837538> Stackies who completed Day 2 milestone and getting extra and bonus stackcoin <:yaycoin:1076423261572837538> <:StackUp:935796086231171112>\n```{milestone_achieved_report}```\n### <:StackUp:935796086231171112> <:yaycoin:1076423261572837538> Stackies getting extra stackcoins <:yaycoin:1076423261572837538> <:StackUp:935796086231171112>\n```{milestone_not_achieved_report}```"
        )
        logging.info("Report sent to coin transfer channel.")
    else:
        logging.error("Coin transfer channel not found. Check the channel ID.")


@bot.tree.command(name="help", description="List all available commands")
async def help_command(interaction: discord.Interaction):
    logging.info(f"Help command by {interaction.user.name} in #{interaction.channel}")

    file = discord.File("media/su-pfp.png", filename="su-pfp.png")
    embeded = discord.Embed(
        color=0xFF5D64,
        title="Stackup Help Centre",
        url="https://stackuphelpcentre.zendesk.com/hc/en-us",
    )
    embeded.add_field(
        name="</ask:1314299955997052950>",
        value="Get answers to your StackUp related questions.",
        inline=False,
    )
    embeded.add_field(
        name="</calculate_withdrawal:1314299955997052951>",
        value="Calculate the estimated date to receive your withdrawal",
        inline=False,
    )
    if auth_admin.check_has_permissions(interaction):
        embeded.add_field(
            name="</lucky_winner:1314299955997052952>",
            value="Pick lucky winners randomly",
            inline=False,
        )
    embeded.add_field(
        name="</help:1314299955997052949>", value="Help Command", inline=False
    )
    embeded.set_thumbnail(url="attachment://su-pfp.png")

    await interaction.response.send_message(file=file, embed=embeded, delete_after=30)


@bot.tree.command(
    name="ask", description="Get answers to your StackUp related questions"
)
@app_commands.describe(
    question="Bot is currently in development, response accuracy may vary as enhancements are being made"
)
async def ask(interaction: discord.Interaction, question: str):
    logging.info(
        f"Question asked: {question} by {interaction.user.name} in #{interaction.channel}"
    )
    try:
        await interaction.response.defer(thinking=True)

        if rag_chain:
            answer = get_answer(question, rag_chain)
            await interaction.followup.send(
                answer
            )  # + "\n\n**Stackup Helper Bot is under development and might have discrepancies in responses**")
        else:
            await interaction.followup.send(
                "Sorry, I'm not ready to answer questions yet. Please try again later."
            )

    except Exception as e:
        logging.error("Error in 'ask' command: %s", e)
        await interaction.followup.send(
            "An error occurred while processing your request. Please try again later.",
            ephemeral=True,
        )


@bot.command(name="ask", help="Get answers to your StackUp related questions")
async def mark_ask(ctx: Context, *, question: str = None):
    logging.info(f"Mark Question asked: {question}")
    if question:
        answer = get_answer(question, rag_chain)
        await ctx.reply(
            answer
        )  # + "\n\n**Stackup Helper Bot is under development and might have discrepancies in responses**")
    else:
        await ctx.reply(
            "Please ask a question after the command, e.g., `!ask <your question>`."
        )


# Add the new command for calculating the withdrawal date
@bot.tree.command(
    name="calculate_withdrawal", description="Calculate the estimated withdrawal date"
)
@app_commands.describe(
    withdrawal_date="Date of withdrawal. Please use DD-MM-YYYY format.",
)
async def calculate_withdrawal(interaction: discord.Interaction, withdrawal_date: str):
    logging.info(
        f"Withdrawal date calculation request by {interaction.user.name} in #{interaction.channel}, Start Date: {withdrawal_date}"
    )
    processing_days = 7

    try:
        withdrawal_date_obj = datetime.strptime(withdrawal_date, "%d-%m-%Y")

        estimated_date = calculate_withdrawal_date(withdrawal_date_obj, processing_days)

        await interaction.response.send_message(
            f"The estimated withdrawal date is: {estimated_date.strftime('%d-%m-%Y')} \n-# Disclaimer: The estimated withdrawal time is based on a processing period of 7 business days, excluding weekends and public holidays."
        )  # <t:{calendar.timegm(estimated_date.timetuple())}:D>"

    except ValueError:
        await interaction.response.send_message(
            "Invalid date format. Please use DD-MM-YYYY format for the start date.",
            ephemeral=True,
        )
    except Exception as e:
        logging.error(f"Error in 'calculate_withdrawal' command: {e}")
        await interaction.response.send_message(
            "An error occurred while calculating the withdrawal date. Please try again later.",
            ephemeral=True,
        )


@bot.tree.command(name="ticket", description="Open a new ticket")
async def ticket(interaction: discord.Interaction):
    await interaction.response.send_message(
        view=TicketHelper(), embed=start_ticket_embed, ephemeral=True
    )


@bot.tree.command(name="lucky_winner", description="Randomly pick lucky winner(s)")
@app_commands.describe(
    range="Range of numbers to choose from. Provided as `1-10`. Both numbers are included as possible winners.",
    count="Number of lucky winners. Defaults to 1 if not provided.",
    seed="Seed for the randomizer. If not provided, a random will be generated.",
    exclude="Number(s) to exclude from the pick. Provided as a list: `1,2,3`.",
)
async def lucky_winner(
    interaction: discord.Interaction,
    range: str,
    count: int = 1,
    seed: int = None,
    exclude: str = "",
):
    if auth_admin.check_has_permissions(interaction):
        if seed is None:
            seed = get_random_seed()

        error, winners, seed_used = pick_lucky_winner(range, count, seed, exclude)

        if error:
            logging.info(
                f"Lucky winner request by {interaction.user.name} in #{interaction.channel}, "
                f"for range {range} excluding {exclude if len(exclude) > 1 else None} using seed {seed} for {count} winner(s) "
                f"gives error: {error}"
            )
            await interaction.response.send_message(f"{error}")
        else:
            logging.info(
                f"Lucky winner request by {interaction.user.name} in #{interaction.channel}, "
                f"for range {range} excluding {exclude if len(exclude) > 1 else None} using seed {seed} "
                f"yields {count} winner(s): {winners}"
            )
            await interaction.response.send_message(
                f"The lucky {'winner is' if len(winners) == 1 else 'winners are'} {', '.join(winners)}."
            )
    else:
        logging.info(
            f"Unauthorized request of Lucky winner command by {interaction.user.name} in #{interaction.channel}"
        )
        await interaction.response.send_message(
            "You don't have access to this command!", ephemeral=True
        )


# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
