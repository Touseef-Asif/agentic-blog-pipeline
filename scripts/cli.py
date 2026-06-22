import json
import sys

import requests


def main():
    """CLI script that interacts with the Blog Pipeline streaming API."""
    print("Starting MVP Blog Writing Pipeline via CLI...")
    url = "http://localhost:8000/chat/stream"

    try:
        print("Connecting to API at", url)
        # Use stream=True to handle Server-Sent Events (SSE)
        response = requests.post(url, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[len("data: ") :]
                    data = json.loads(data_str)

                    if "message" in data:
                        print(f"[{data.get('node')}] {data['message']}")
                    elif "node" in data:
                        print(f"Executed node: {data['node']}")
                    elif "done" in data and data["done"]:
                        final_state = data.get("final_state", {})

                        print("\n" + "=" * 60)
                        print("Pipeline complete!")
                        print(f"Topic   : {final_state.get('selected_topic', 'N/A')}")
                        print(f"Score   : {final_state.get('best_score', 0)}/100")
                        print(f"Attempts: {final_state.get('attempts', 0)}")
                        print("=" * 60)
                        print("\nBEST BLOG DRAFT:\n")
                        print(final_state.get("best_draft", "No draft generated."))
                        print("\n" + "=" * 60)
    except requests.exceptions.ConnectionError:
        print(
            "Error: Could not connect to API. Is the server running? (python main.py)"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
