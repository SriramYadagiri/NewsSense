from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
import os

# Use your existing OpenAI key
llm = OpenAIChat(id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"), temperature=0)

agent = Agent(
    model=llm,
    tools=[DuckDuckGoTools()],
    description="""
You are a fact-checking AI. Your job is to:
1. Extract factual claims from an article.
2. Use the `duckduck_search` tool to verify each claim. 
3. Prioritize trusted sources:
- Reuters, AP, BBC, Al Jazeera, NYTimes, CNN, DefenseNews, FlightAware
- If available, use fact-checking sites like Snopes or Politifact
- Format the search query to include:  `<claim text> site:reuters.com OR site:bbc.com OR site:cnn.com ...`
4. Return for each claim:
   - The claim text word for word preserving punctuation; do not modify the claim from the article at all
   - A verdict: 'Supported', 'Disputed', or 'Not Found'
   - A short justification
   - A source URL or snippet

Do not include markdown, prose, or code comments. Only return a JSON in the following format: 
[
  {
    "claim": "...",
    "verdict": "...",
    "justification": "...",
    "source": "..."
  }
] 
"""
)