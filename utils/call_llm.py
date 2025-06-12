import os
from groq import Groq
import ollama


def call_llm(prompt , llm_server="ollama") -> str:
    """
    Calls the Groq LLM with a given prompt.
    """
    if llm_server == "groq":
        client = Groq(api_key="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")
        r = client.chat.completions.create(
            model="llama-3.1-8b-instant", # Or another suitable Groq model
            messages=[{"role": "user", "content": prompt}]
        )
        return r.choices[0].message.content
    elif llm_server == "ollama":
        response = ollama.chat(
            model="llama3.2:latest" ,
            messages=[{"role": "user", "content": prompt}],
        )
        return response['message']['content']
if __name__ == "__main__":
    # Example usage
    prompt = "What is the capital of France?"
    print(f"Prompt: {prompt}")
    response = call_llm(prompt)
    print(f"Response: {response}")
