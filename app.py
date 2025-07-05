from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
import os
from openai import OpenAI
from openai import (
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    NotFoundError,
    UnprocessableEntityError,
    RateLimitError,
    APIConnectionError,
    Timeout,
    APIStatusError,
)

app = FastAPI()

# ✅ Connect to OpenRouter (OpenAI-compatible)
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

class AgentRequest(BaseModel):
    user: str
    task_type: str
    input_text: Optional[str] = None

def retrieve_prompt(user: str, task_type: str) -> str:
    conn = sqlite3.connect("tracy_memory.db")
    c = conn.cursor()
    c.execute(
        """
        SELECT prompt FROM prompts
        WHERE user = ? AND task_type = ?
        ORDER BY version DESC
        LIMIT 1
        """,
        (user, task_type)
    )
    row = c.fetchone()
    conn.close()
    return row[0] if row else "You are a helpful Tracy agent."

def log_response(user: str, task_type: str, response: str):
    conn = sqlite3.connect("tracy_memory.db")
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO responses (user, task_type, response)
        VALUES (?, ?, ?)
        """,
        (user, task_type, response)
    )
    conn.commit()
    conn.close()

@app.post("/prompt-agent")
async def prompt_agent(req: AgentRequest):
    prompt = retrieve_prompt(req.user, req.task_type)
    if req.input_text:
        prompt += f"\nUser input: {req.input_text}"

    try:
        completion = client.chat.completions.create(
            model="deepseek/deepseek-chat-v3",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": req.input_text or ""}
            ],
        )
        result = completion.choices[0].message.content
        log_response(req.user, req.task_type, result)
        return {"result": result}

    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail="Authentication failed. Check your API key.")
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail="Permission denied. Check your model or account limits.")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail="Model or resource not found.")
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=f"Bad request: {str(e)}")
    except UnprocessableEntityError as e:
        raise HTTPException(status_code=422, detail="The request could not be processed by the model.")
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Slow down.")
    except APIConnectionError as e:
        raise HTTPException(status_code=503, detail="Connection to API failed.")
    except Timeout as e:
        raise HTTPException(status_code=504, detail="The API request timed out.")
    except APIStatusError as e:
        raise HTTPException(status_code=502, detail="API server returned an error response.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
