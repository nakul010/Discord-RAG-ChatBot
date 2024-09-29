import os
from pathlib import Path
import json
import discord
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables for API keys
load_dotenv()

# Constants
EMBEDDINGS_CONFIG_FILE = "embeddings_config.json"
VECTORSTORE_DIR = "vectorstore"


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
        model="gemini-1.5-pro", temperature=0.3, max_tokens=500
    )

    # Create a prompt template
    system_prompt = (
        "You are a helpdesk chatbot designed to provide support using relevant articles from the Stackup Help Center. Your role is to:\n"
        "1. Provide solutions by retrieving and referencing information from the knowledge base articles."
        "2. Answer queries based on factual and relevant content from these articles."
        "3. Guide users through step-by-step troubleshooting and reference related articles."
        "4. Maintain accuracy and avoid hallucinations—only respond with information found in the articles provided."
        "5. Structure responses clearly by summarizing key points from articles, providing article links for more details, and using a helpful, professional tone."
        "6. If unsure, escalate the query by suggesting the user seeks further help from servers's moderator if an article does not cover their issue."
        "7. And for ticket creating link use 'Create Ticket here' markdown"
        "8. Be Grammatically correct"
        "\n\n"
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


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    print("------")
    global rag_chain
    rag_chain = setup_rag_chain()


@bot.tree.command(name="ask", description="Ask a question from Stackup Helpdesk")
@app_commands.describe(question="Question for the chatbot")
async def ask(interaction: discord.Interaction, question: str):
    # Acknowledge the interaction immediately
    await interaction.response.defer(thinking=True)

    if rag_chain:
        answer = get_answer(question, rag_chain)
        await interaction.followup.send(answer)
    else:
        await interaction.followup.send(
            "Sorry, I'm not ready to answer questions yet. Please try again later."
        )


@bot.command(name="ask", help="Mark your question for the helpdesk")
async def mark_ask(ctx, *, question: str = None):
    if question:
        answer = get_answer(question, rag_chain)
        await ctx.reply(answer)
    else:
        await ctx.reply(
            "Please ask a question after the command, e.g., `!ask <your question>`."
        )


# Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))
