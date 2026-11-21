import os

from openai import AuthenticationError, OpenAI, RateLimitError



def check_openai_key(api_key: str | None = None) -> None:
  api_key = api_key or os.getenv("OPENAI_API_KEY")
  if not api_key:
    print("Set OPENAI_API_KEY to validate an OpenAI credential.")
    return
  client = OpenAI(api_key=api_key)
  try:
    # Listing models verifies the key without spending tokens
    client.models.list()
    print("✅ Success: Your OpenAI API key is valid and working.")
  except AuthenticationError:
    print("❌ Invalid API Key: Check that your key is correct and active.")
  except RateLimitError:
    print("⚠️ Valid Key, No Quota: The key works, but you exceeded your quota or need to add billing credits.")
  except Exception:
    print("Could not validate the key because of an unexpected error.")


if __name__ == "__main__":
  check_openai_key()
