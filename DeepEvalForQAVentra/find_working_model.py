"""Probes candidate judge models to find one this account can actually call.

NVIDIA's /models endpoint lists the full catalog, not what your specific
account is provisioned for — so a model can appear available and still
return 404. This sends a real (tiny) request to each candidate.
"""

from openai import OpenAI

from framework import config

CANDIDATES = [
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "nvidia/llama-3.1-nemotron-51b-instruct",
    "mistralai/mistral-large-2-instruct",
    "mistralai/mistral-large",
    "mistralai/mistral-nemotron",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-nano-3-30b-a3b",
    "nvidia/mistral-nemo-minitron-8b-8k-instruct",
    "nv-mistralai/mistral-nemo-12b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
    "nvidia/llama3-chatqa-1.5-70b",
    "meta/llama-3.2-90b-vision-instruct",
]

client = OpenAI(
    base_url=config.NVIDIA_BASE_URL,
    api_key=config.NVIDIA_API_KEY,
)

working = []

for model in CANDIDATES:
    try:
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
        )
        print(f"  WORKS    {model}")
        working.append(model)
    except Exception as e:
        reason = str(e)[:70].replace("\n", " ")
        print(f"  fails    {model}  ({reason})")

print("\n" + "=" * 55)
if working:
    print("Usable models:")
    for m in working:
        print(f"  {m}")
    print(f"\nPut this in your .env:\n  JUDGE_MODEL={working[0]}")
else:
    print("None worked. Check that your API key is valid and active.")