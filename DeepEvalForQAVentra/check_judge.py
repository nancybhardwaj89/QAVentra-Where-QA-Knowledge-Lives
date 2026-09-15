"""Quick sanity check: is the judge model reachable and working?

Run this before any evaluation to catch a bad API key or a library
version mismatch in seconds rather than minutes into a full test run.
"""

from pydantic import BaseModel

from framework.judges import get_judge


class SimpleAnswer(BaseModel):
    answer: str


def main():
    judge = get_judge()
    print(f"Judge: {judge.get_model_name()}")
    print("Sending test prompt...\n")

    result = judge.generate("Say hello in exactly 3 words", SimpleAnswer)

    print(f"Response: {result.answer}")
    print("\nJudge is working correctly.")


if __name__ == "__main__":
    main()