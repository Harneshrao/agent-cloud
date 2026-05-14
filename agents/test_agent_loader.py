import sys
import os

# ensure project root in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.loader import load_agents


def main():

    agents = load_agents()

    print("\nLoaded agents:\n")

    for name in agents:
        print(name)


if __name__ == "__main__":
    main()