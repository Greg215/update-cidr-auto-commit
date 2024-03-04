import os
import subprocess
from ruamel.yaml import YAML

def format_yaml_with_yq(file_path):
    try:
        # Format YAML file with yq and overwrite the original file
        formatted_output = subprocess.run(['yq', 'eval', '-P', file_path], check=True, text=True, capture_output=True).stdout
        with open(file_path, 'w') as f:
            f.write(formatted_output)
        print(f"Formatted and updated file with yq: {file_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error formatting file with yq on {file_path}:\n{e}")

def update_yaml_file(file_path):
    print(f"Found file: {file_path}")
    yaml = YAML()
    yaml.preserve_quotes = True
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
        # Format and update the content of the file with yq
        format_yaml_with_yq(file_path)
    else:
        print(f"No changes needed for file: {file_path}")

def check_and_update_files(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file in ['aurora.yaml', 'postgres.yaml']:
                file_path = os.path.join(root, file)
                update_yaml_file(file_path)

repo_root_dir = '.'
check_and_update_files(repo_root_dir)
