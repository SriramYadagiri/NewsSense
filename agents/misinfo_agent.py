import os
import json
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agents.google_search_tool import GoogleSearchToolkit
import re
from dotenv import load_dotenv

load_dotenv(override=True)

llm = OpenAIChat(id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"), temperature=0)
google_search_tool = GoogleSearchToolkit()

agent = Agent(
    model=llm,
    tools=[google_search_tool],
    description="""
You are a fact-checking AI. Your job is to:
1. Extract any factual claims from the article that might be misinformation or exaggerated.
2. Always use `google_search_tool` to look up each claim in the context of the article. It's important that you make sure to include context given in the article in the claim text you query
3. Always Call `google_search_tool` individually for each claim
4. For each claim use the resulting articles given by the `google_search_tool` to:
   - Return one of the following verdicts: 'Supported', 'Disputed', or 'Unverified'
     - Use 'Unverified' if no article directly supports or contradicts the claim.
   - Provide a short justification for your verdict.
   - Include a source URL if found, or say "No relevant source found".
   - In the json you return the value for the claim-query key should be the claim you queried 
   - The original-passage key should be the original passage you used to come up with the query. The original-passage must be a direct quote from the user given text.
   - Do not change or simplify punctuation in any passage. Retain double quotes ("), single quotes ('), apostrophes, and other punctuation **exactly** as they appear in the article. This is critical for text matching.
5. You must evaluate whether any of the top 5 results actually address the claim directly. 
  If the result does not directly confirm or dispute the claim, mark the verdict as 'Unverified'.

  If even one article directly confirms or denies the claim, return:
  - 'Supported' or 'Disputed'
  - A short justification (e.g. "CNN confirmed the quote in a report on July 10.")
  - The article URL or headline

Respond only with a JSON array, no extra text, markdown, or explanations. All string values must be valid JSON. Escape inner double quotes with a backslash (\") as required by JSON standards.:
[
  {
    "claim-query": "Federal authorities conducted raids on Glass House Farms in Camarillo and Carpinteria using tear gas.",
    "original-passage": "Federal authorities conducted raids on Glass House Farms families in Camarillo and Carpinteria. Authorities used tear gas,",
    "verdict": "Supported",
    "justification": "Sources confirm that federal authorities used tear gas during raids on Glass House Farms.",
    "source": "https://www.reuters.com/world/us/immigration-raids-california-cannabis-nurseries-spark-protests-2025-07-11/"
  },
  ...
]
""",
    instructions=[
        "Extract all factual claims from the article that could be misinformation, misrepresentation, or exaggeration.",
        "Always use `google_search_tool` for each claim.",
        "Do not attempt to verify claims without calling the tool.",
        "Parse the search results and check if any snippet directly supports or disputes the claim.",
        "Mark as Unverified only if none of the results are conclusive.",
        "Return results as a JSON array with `claim-query`, `original-passage`, verdict`, `justification`, and `source`."
    ],
    show_tool_calls=True,  # for development, show when the agent calls a tool (useful for debugging)
    markdown=True
)

def clean_json_response(raw_response):
    # Strip markdown backticks and non-JSON content
    cleaned = re.sub(r"```json|```", "", raw_response)
    cleaned = cleaned.strip()
    return cleaned

def verify_claims_with_agent(text):
    try:
        response = agent.run(f"Verify factual claims in this article:\n\n{text}")

        # Raw response (should be JSON)
        result = clean_json_response(response.content.strip())

        # Parse the JSON response
        data = json.loads(result)

        # Ensure fallback structure is maintained
        if not isinstance(data, list):
            raise ValueError("Agent output is not a list")

        # Ensure required fields are present
        formatted_data = []
        print(data)
        for entry in data:
            print(entry)
            if not all(k in entry for k in ("claim-query", "original-passage", "verdict", "justification", "source")):
                continue
            formatted_data.append({
                "claim-query": entry["claim-query"].strip(),
                "original-passage": entry["original-passage"].strip(),
                "verdict": entry["verdict"].strip(),
                "justification": entry["justification"].strip(),
                "source": entry["source"].strip()
            })

        print(formatted_data)

        return formatted_data

    except Exception as e:
        print("Agent verification error:", e)
        return []