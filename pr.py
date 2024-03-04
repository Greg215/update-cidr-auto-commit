import os
import subprocess
import requests
from ruamel.yaml import YAML

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    raise ValueError("Please set the GITHUB_TOKEN environment variable.")

GITHUB_REPO = 'Greg215/update-cidr-auto-commit' 
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/pulls"

def run_git_command(command, capture_output=False):
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=capture_output)
        return result.stdout if capture_output else None
    except subprocess.CalledProcessError as e:
        print(f"Error running Git command {' '.join(command)}:\n{e}")
        return None

def format_yaml_with_yq(file_path):
    try:
        formatted_output = subprocess.run(['yq', 'eval', '-P', file_path], check=True, text=True, capture_output=True).stdout
        with open(file_path, 'w') as f:
            f.write(formatted_output)
        print(f"Formatted and updated file with yq: {file_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error formatting file with yq on {file_path}:\n{e}")

def update_yaml_file(file_path, application_name):
    print(f"Found file: {file_path}")
    yaml = YAML()
    yaml.preserve_quotes = True
    data = None
    with open(file_path, 'r') as f:
        data = yaml.load(f)

    updated = False
    for spec in data.get('spec', []):
        if 'overrides' in spec:
            for override in spec['overrides']:
                env = override.get('env')
                if env in ['dev', 'prod']:
                    cidr = '10.219.0.0/18' if env == 'dev' else '10.120.0.0/18'
                    if 'extraIngressRules' not in override:
                        override['extraIngressRules'] = {'CIDRs': [cidr]}
                        updated = True
                    elif 'CIDRs' not in override['extraIngressRules']:
                        override['extraIngressRules']['CIDRs'] = [cidr]
                        updated = True
                    else:
                        if cidr not in override['extraIngressRules']['CIDRs']:
                            override['extraIngressRules']['CIDRs'].append(cidr)
                            updated = True

    if updated:
        with open(file_path, 'w') as f:
            yaml.dump(data, f)
        print(f"Updated file: {file_path}")
        format_yaml_with_yq(file_path)
        return True  # Indicates that the file was updated
    else:
        print(f"No changes needed for file: {file_path}")
        return False  # Indicates that no changes were made


def create_pull_request(branch_name, application_name):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": f"Update CIDRs for {application_name}",
        "head": branch_name,
        "base": "main",
        "body": f"Automated pull request to update CIDRs for {application_name}.",
        "draft": False
    }
    response = requests.post(GITHUB_API_URL, json=data, headers=headers)
    if response.status_code == 201:
        print(f"Pull request created successfully for {branch_name}.")
    else:
        print(f"Failed to create pull request for {branch_name}. Response: {response.text}")


def process_application_file(file_path, application_name):
    branch_name = f"feature/obs-227/obs-cidr-{application_name}"
    # Check if the branch already exists
    existing_branches = run_git_command(['git', 'branch', '--list', branch_name], capture_output=True)
    if branch_name not in existing_branches:
        # Create a new branch from main/master (adjust as needed)
        run_git_command(['git', 'checkout', 'main'])
        run_git_command(['git', 'pull'])
        run_git_command(['git', 'checkout', '-b', branch_name])
    else:
        # Switch to the existing branch
        run_git_command(['git', 'checkout', branch_name])

    if update_yaml_file(file_path, application_name):
        # Add, commit, and push changes
        run_git_command(['git', 'add', file_path])
        commit_message = f"Update CIDRs for {application_name}"
        run_git_command(['git', 'commit', '-m', commit_message])
        run_git_command(['git', 'push', '--set-upstream', 'origin', branch_name])

        create_pull_request(branch_name, application_name)
    else:
        # No changes made, return to the main branch
        run_git_command(['git', 'checkout', 'main'])

def check_and_update_files(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file in ['aurora.yaml', 'postgres.yaml']:
                file_path = os.path.join(root, file)
                # Assumes the directory structure is apps/<application name>/resources
                application_name_parts = root.split(os.sep)
                if 'apps' in application_name_parts:
                    application_name_index = application_name_parts.index('apps') + 1
                    if application_name_index < len(application_name_parts):
                        application_name = application_name_parts[application_name_index]
                        process_application_file(file_path, application_name)

repo_root_dir = '.'
check_and_update_files(repo_root_dir)