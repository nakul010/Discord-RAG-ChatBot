# Discord RAG ChatBot [![Discord Bot Status](https://badgen.infra.medigy.com/uptime-robot/status/ur2416038-6d3bb4f6ab214cff300f00ac)](https://stats.uptimerobot.com/mHvREacZr4)

A Discord bot that uses RAG (Retrieval Augmented Generation) to provide automated support by answering questions using content from the Help Desk's articles.

## Add to Your Server

To add this bot to your Discord server, click [here](https://discord.com/oauth2/authorize?client_id=1289849397978333227&permissions=277293845568&integration_type=0&scope=bot+applications.commands)

## Features

- Fetches and processes articles from the Help Desk
- Uses RAG with Google's Generative AI to provide accurate, context-aware responses
- Supports both slash commands and traditional prefix commands
- Maintains a persistent vector store for efficient information retrieval
- Provides helpful, professional responses with references to relevant articles

## Setting up

1. Clone the repository:

```bash
git clone https://github.com/nakul010/Discord-RAG-ChatBot.git
cd Discord-RAG-ChatBot
```

2. Install required packages:

```bash
pip install -r requirements.txt
```

3. Set up the environment variables by creating a `.env` file in the root directory with the following variables:

```
DISCORD_TOKEN = your_discord_token
HUGGING_FACE = your_hugging_face_token
GOOGLE_API_KEY = your_google_api_key
USERNAME = username  ### for viewing the logs
PASSWORD = password  ### for viewing the logs
```

> [!IMPORTANT]
> Ensure your `DISCORD_TOKEN` has _Privileged Gateway Intents_

## Usage

1. First, run the article fetching script to create the knowledge base:

```bash
python eda-data.py
```

2. Then start the Discord bot:

```bash
python main.py
```

### Available Commands

- `/ask <question>` - Get answers to your StackUp related questions.
- `/calculate_withdrawal <withdrawal_date>` - Calculate the estimated date to receive your withdrawal.
- `/help` - Help command.

## How It Works

1. **Data Preparation**:
   - Fetches articles from the Help Desk
   - Cleans HTML content and formats links to markdown
   - Saves processed articles to a text file

2. **RAG Setup**:
   - Loads processed documents
   - Splits text into chunks
   - Creates embeddings using Google's Generative AI
   - Stores vectors in a Chroma vector store

3. **Query Processing**:
   - Retrieves relevant documents based on user questions
   - Uses a custom prompt template to generate accurate responses
   - Provides answers with context from the knowledge base

## Future Plans

- **Image Merging Feature:** Implement a feature that allows users to request image merging directly within Discord.
- **Admin Logging System:** Implement logging system that allows admins to view all user interactions and queries.
