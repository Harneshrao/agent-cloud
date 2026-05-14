import sys
import os

# ---------------------------------------------------
# Ensure project root is in Python path
# ---------------------------------------------------

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ---------------------------------------------------
# Import Example Agent from SDK
# ---------------------------------------------------

from sdk.agent import ExampleAgent


def main():

    print("\nRunning SDK Test...\n")

    state = {
        "task": "AI startup market"
    }

    agent = ExampleAgent()

    result = agent.run(state)

    print("\nSDK ExampleAgent result:\n")
    print(result)


if __name__ == "__main__":
    main()

