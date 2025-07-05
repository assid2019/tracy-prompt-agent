from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import sqlite3
import os
from openai import OpenAI
from openai import error as openai_error

app = FastAPI()

# Connect to OpenRouter-compatible OpenAI client
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Pydantic schema for requests
class AgentRequest(BaseModel):
    user: str
    task_type: str
    input_text: Optional[str] = None

# Retrieve prompt from SQLite
def retrieve_prompt(user, task_type):
    conn = sqlite3.connect("tracy_memory.db")
    c = conn.cursor()
    c.execute("""
        SELECT prompt FROM prompts
        WHERE user=? AND task_type=?
        ORDER BY version DESC
        LIMIT 1
    """, (user, task_type))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "You are a helpful Tracy agent."

# Log responses to SQLite
def log_response(user, task_type, response):
    conn = sqlite3.connect("tracy_memory.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO responses (user, task_type, response)
        VALUES (?, ?, ?)
    """, (user, task_type, response))
    conn.commit()
    conn.close()

@app.post("/prompt-agent")
async def prompt_agent(req: AgentRequest):
    prompt = retrieve_prompt(req.user, req.task_type)
    if req.input_text:
        prompt += f"\nUser input: {req.input_text}"

    try:
        completion = client.chat.completions.create(
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": req.input_text or ""}
            ],
            extra_headers={
                "HTTP-Referer": "https://your-site.com",  # optional
                "X-Title": "tracy-prompt-agent"           # optional
            }
        )
        result = completion.choices[0].message.content
        log_response(req.user, req.task_type, result)
        return {"result": result}
    except openai_error.OpenAIError as e:
        # catch OpenAI/OpenRouter errors
        return {"error": str(e)}

