import requests
import re
import toml
import json
from tqdm import tqdm

GITHUB_REPOS_FILE = "top_repositories_1000.json"
OUTPUT_FILE = "git_package_list.json"
TOKEN = "git_token"


def fetch_default_branch(repo_url):
    repo_api_url = repo_url.replace("https://github.com/", "https://api.github.com/repos/")
    headers = {"Authorization": f"token {TOKEN}"}
    response = requests.get(repo_api_url, headers=headers)
    if response.status_code == 200:
        repo_data = response.json()
        return repo_data.get("default_branch", "main")
    else:
        return "main"


def fetch_file_from_github(repo_url, file_path, branch):
    raw_url = repo_url.replace("github.com", "raw.githubusercontent.com") + f"/{branch}/{file_path}"
    response = requests.get(raw_url)
    if response.status_code == 200:
        return response.text
    else:
        return None


def extract_dependencies(requirements_content):
    dependencies = []
    lines = requirements_content.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith(("#", "-", ".")):
            continue
        if "@" in line:
            continue
        package_name = re.split(r'[<>=;@~!#$%^&*()+{}:?]', line)[0].strip()
        if "[" in package_name:
            package_name = package_name.split("[")[0].strip()
        if package_name and re.match(r'^[a-zA-Z0-9\-_]+$', package_name):
            dependencies.append(package_name)
    return dependencies


def extract_requirements_from_txt(requirements_txt_content):
    return extract_dependencies(requirements_txt_content)


def extract_requirements_from_setup_py(setup_py_content):
    install_requires = []
    match = re.search(r"install_requires\s*=\s*\[(.*?)\]", setup_py_content, re.DOTALL)
    if match:
        requirements_str = match.group(1)
        requirements_pkg = re.findall(r"['\"]([^'\"]+?)['\"](?:\s*,\s*#.*?$|\s*,|$)", requirements_str, re.MULTILINE)
        install_requires = extract_dependencies("\n".join(requirements_pkg))
    return install_requires


def extract_requirements_from_pyproject(pyproject_content):
    try:
        pyproject_data = toml.loads(pyproject_content)
    except Exception as e:
        print(f"Failed to parse pyproject.toml: {e}")
        return []

    dependencies = []
    if 'project' in pyproject_data and 'dependencies' in pyproject_data['project']:
        dependencies.extend(extract_dependencies("\n".join(pyproject_data['project']['dependencies'])))
    if 'project' in pyproject_data and 'optional-dependencies' in pyproject_data['project']:
        for opt_deps in pyproject_data['project']['optional-dependencies'].values():
            dependencies.extend(extract_dependencies("\n".join(opt_deps)))
    if 'build-system' in pyproject_data and 'requires' in pyproject_data['build-system']:
        dependencies.extend(extract_dependencies("\n".join(pyproject_data['build-system']['requires'])))
    if 'tool' in pyproject_data and 'poetry' in pyproject_data['tool'] and 'dependencies' in pyproject_data['tool']['poetry']:
        dependencies.extend(extract_dependencies("\n".join(pyproject_data['tool']['poetry']['dependencies'].keys())))
    if 'tool' in pyproject_data and 'poetry' in pyproject_data['tool'] and 'group' in pyproject_data['tool']['poetry']:
        for group in pyproject_data['tool']['poetry']['group'].values():
            if 'dependencies' in group:
                dependencies.extend(extract_dependencies("\n".join(group['dependencies'].keys())))
    for section in pyproject_data.get('tool', {}).values():
        if isinstance(section, dict) and 'dependencies' in section:
            dependencies.extend(extract_dependencies("\n".join(section['dependencies'].keys())))

    return dependencies


def normalize_package_name(package_name):
    return re.sub(r'[^a-z0-9]+', '-', package_name.lower())


def get_requirements(repo_url):
    default_branch = fetch_default_branch(repo_url)
    all_requirements = set()

    requirements_txt_content = fetch_file_from_github(repo_url, "requirements.txt", default_branch)
    if requirements_txt_content:
        txt_requirements = extract_requirements_from_txt(requirements_txt_content)
        all_requirements.update(txt_requirements)

    setup_py_content = fetch_file_from_github(repo_url, "setup.py", default_branch)
    if setup_py_content:
        setup_requirements = extract_requirements_from_setup_py(setup_py_content)
        all_requirements.update(setup_requirements)

    pyproject_content = fetch_file_from_github(repo_url, "pyproject.toml", default_branch)
    if pyproject_content:
        pyproject_requirements = extract_requirements_from_pyproject(pyproject_content)
        all_requirements.update(pyproject_requirements)

    normalized_requirements = set(normalize_package_name(pkg) for pkg in all_requirements)
    return list(normalized_requirements)


def save_requirements_to_json(repo_url, requirements, output_file):
    try:
        with open(output_file, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    data[repo_url] = requirements
    with open(output_file, 'w') as file:
        json.dump(data, file, indent=4)


if __name__ == "__main__":
    with open(GITHUB_REPOS_FILE, 'r') as file:
        repo_urls = json.load(file)

    for repo_url in tqdm(repo_urls, desc="Processing Repositories"):
        requirements = get_requirements(repo_url)
        save_requirements_to_json(repo_url, requirements, OUTPUT_FILE)
