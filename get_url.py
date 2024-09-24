import requests
import json
import time

GITHUB_API_URL = "https://api.github.com/search/repositories"
TOKEN = "git_token"
OUTPUT_FILE = "top_repositories_1000.json"
RESULTS_PER_PAGE = 100
MAX_RESULTS = 1000


def fetch_python_repositories(page, results_per_page=100):
    headers = {
        "Authorization": f"token {TOKEN}",
    }

    params = {
        "q": "language:python",
        "sort": "stars",
        "order": "desc",
        "per_page": results_per_page,
        "page": page,
    }

    response = requests.get(GITHUB_API_URL, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_top_python_repositories():
    all_repos = []
    current_page = 1

    while len(all_repos) < MAX_RESULTS:
        data = fetch_python_repositories(page=current_page, results_per_page=RESULTS_PER_PAGE)

        if data and 'items' in data:
            all_repos.extend(data['items'])
        else:
            print("No more data or error encountered.")
            break

        print(f"Fetched page {current_page}, total repos fetched: {len(all_repos)}")

        time.sleep(2)

        current_page += 1

        if len(all_repos) >= MAX_RESULTS:
            all_repos = all_repos[:MAX_RESULTS]

    return all_repos


def save_repositories_to_json(repositories, output_file):
    repo_urls = [repo['html_url'] for repo in repositories]

    with open(output_file, 'w') as file:
        json.dump(repo_urls, file, indent=4)

    print(f"Saved top {len(repo_urls)} repository URLs to {output_file}")


if __name__ == "__main__":
    top_repos = get_top_python_repositories()

    save_repositories_to_json(top_repos, OUTPUT_FILE)
