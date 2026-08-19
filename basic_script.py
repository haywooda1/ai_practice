import anthropic
from dotenv import load_dotenv
from pathlib import Path
# Load .env relative to this script's location, regardless of cwd
load_dotenv(Path(__file__).parent / ".env")
# Create a client — it auto-reads ANTHROPIC_API_KEY
client = anthropic.Anthropic()
# Send a message to Claude
message = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[
        # {"role": "user", "content": "Say hello and tell me one interesting fact about AI agents."}
        {"role": "user", "content": "What are the ,ps on-demand skills for AI Engineering Manager roles in 2026?"}

    ]
)
# Print Claude's response
print(message.content[0].text)
#
# What each part does:
# Lines 1-2
#  Import the Anthropic SDK and dotenv library
# Line 4
#  Reads your .env file and loads ANTHROPIC_API_KEY into the environment
# Line 6
#  Creates an Anthropic client — automatically picks up your API key
# Line 8-13
#  Sends a message to Claude — just like typing in the chat UI, but from code
# Line 9
#  claude-sonnet-4-5 is the model — the same one powering this conversation
# Line 10
#  max_tokens limits how long Claude's response can be (1024 is plenty to start)
# Line 18
#  Prints Claude's reply — .content[0].text is how you extract the text from the response object