import argparse
import os
import requests
import subprocess
import sys
import tempfile

from typing import List

apps_query = """
query {
  user {
    accounts {
      id
      apps {
        id
      }
    }
  }
}
"""


def get_app_ids(grid_url: str, auth_token: str) -> List[str]:
    response = requests.post(
        url=f"{grid_url}/console/v2/api/",
        headers={"Authorization": f"Token {auth_token}"},
        json={"query": apps_query, "variables": {}},
    )
    if response.status_code != 200:
        print("Could not get list of apps:")
        print(f"{response.status_code}:")
        print(response.text)
        exit(1)

    app_ids = []
    data = response.json()

    for account in data["data"]["user"]["accounts"]:
        for app in account["apps"]:
            app_ids.append(app["id"])
    return app_ids


def system(*args):
    subprocess.call(args, stdout=sys.stdout, stderr=sys.stderr)


def push_app(grid_url: str, base_path: str, app_id: str):
    print(
        f"==================== Pushing App: {app_id} ==========================="
    )
    system(
        "meya",
        "clone",
        "--grid-url",
        grid_url,
        "--app-id",
        app_id,
        "--directory",
        app_id,
    )
    app_path = os.path.join(base_path, app_id)
    print(f"Switching directories to {app_path}")
    os.chdir(app_path)
    git_context = ["--git-dir", ".meya/git", "--work-tree", "."]
    system(
        "git",
        *git_context,
        "remote",
        "add",
        "-f",
        "zen-common",
        "https://github.com/roeland-frans/zen-common.git",
    )
    system(
        "git",
        *git_context,
        "subtree",
        "add",
        "--prefix",
        "zen",
        "zen-common",
        "master",
        "--squash",
    )
    system("meya", "push", "--build-image")
    print(f"Switching back to {base_path}")
    os.chdir(base_path)


def push_apps(grid_url: str, app_ids: List[str]):
    with tempfile.TemporaryDirectory() as temp_path:
        print("Created temporary directory:", temp_path)
        os.chdir(temp_path)
        for app_id in app_ids:
            push_app(grid_url, temp_path, app_id)


def main():
    parser = argparse.ArgumentParser(
        description="Add/Update 'zen-common' code in all account apps."
    )
    parser.add_argument(
        "--grid-url",
        dest="grid_url",
        default="https://grid.meya.ai",
        help="The grid URL you want to connect to.",
    )
    parser.add_argument(
        "--auth-token",
        dest="auth_token",
        help="Your Meya auth token.",
        required=True,
    )
    parser.add_argument(
        "--app-ids",
        dest="filter_app_ids",
        nargs="+",
        help="The app IDs you would like to update.",
    )
    args = parser.parse_args()
    grid_url = os.getenv("MEYA_GRID_URL") or args.grid_url
    auth_token = os.getenv("MEYA_AUTH_TOKEN") or args.auth_token
    app_ids = get_app_ids(grid_url, auth_token)
    if args.filter_app_ids:
        app_ids = [
            app_id for app_id in app_ids if app_id in args.filter_app_ids
        ]
    push_apps(grid_url, app_ids)


if __name__ == "__main__":
    main()
