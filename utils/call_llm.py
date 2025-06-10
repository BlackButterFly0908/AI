import os
from groq import Groq

# Learn more about calling the LLM: https://the-pocket.github.io/PocketFlow/utility_function/llm.html
def call_llm(prompt):
    """
    Calls the Groq LLM with a given prompt.
    """
    client = Groq(api_key="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")
    r = client.chat.completions.create(
        model="llama-3.1-8b-instant", # Or another suitable Groq model
        messages=[{"role": "user", "content": prompt}]
    )
    return r.choices[0].message.content

if __name__ == "__main__":
    # Example usage
    prompt = "What is the capital of France?"
    print(f"Prompt: {prompt}")
    response = call_llm(prompt)
    print(f"Response: {response}")
