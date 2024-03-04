import os
import yaml
from git import Repo

def update_yaml_with_cidrs(file_path, env):
    """
    Update the YAML file with the appropriate CIDRs based on the environment.
    """
    with open(file_path) as f:
        data = yaml.safe_load(f)

    # Determine the CIDR to add based on the environment
    cidr_to_add = "10.219.0.0/18" if env == "dev" else "10.120.0.0/18"

    # Ensure extraIngressRules exists and has the correct CIDRs
    data.setdefault('extraIngressRules', {}).setdefault('CIDRs', [])
    if cidr_to_add not in data['extraIngressRules']['CIDRs']:
        data['extraIngressRules']['CIDRs'].append(cidr_to_add)

    with open(file_path, 'w') as f:
        yaml.safe_dump(data, f, sort_keys=False)

def find_and_update_files(start_path):
    """
    Recursively find and update aurora.yaml or postgres.yaml files.
    """
    for root, dirs, files in os.walk(start_path):
        for file in files:
            if file in ['aurora.yaml', 'postgres.yaml']:
                file_path = os.path.join(root, file)
                with open(file_path) as f:
                    data = yaml.safe_load(f)
                if 'overrides' in data and 'env' in data['overrides']:
                    env = data['overrides']['env']
                    update_yaml_with_cidrs(file_path, env)

def main():
    repo = Repo('.')
    assert not repo.bare

    applications_path = 'apps'
    for app_name in os.listdir(applications_path):
        app_resources_path = os.path.join(applications_path, app_name, 'resources')
        if os.path.isdir(app_resources_path):
            find_and_update_files(app_resources_path)
            new_branch_name = f"feature/obs-227/obs-cidr-{app_name}"
            repo.git.checkout('HEAD', b=new_branch_name)
            repo.git.add(A=True)
            repo.git.commit('-m', f'Update CIDRs for {app_name}')
            repo.git.checkout('main')  # Switch back to main branch

if __name__ == "__main__":
    main()
