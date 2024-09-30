import json
import re
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

current_script_path = os.path.abspath(__file__)
BASE_DIR = os.path.dirname(os.path.dirname(current_script_path))
output_file = os.path.join(BASE_DIR, 'results.json')


def exact_package_match(typo_name, string):
    pattern = rf"^{re.escape(typo_name)}(?:-\d|\.|$)"
    return re.search(pattern, string) is not None


def calculate_score(typo_name, typo_score, dog_result, yara_scan_result, comparison_result, sbom_result, uploader_info, github_info, package_name, package_github_url):
    score = typo_score
    score_breakdown = [f"typos: [{typo_score:.2f}]"]
    dog_detected = any(typo_name == issue['package']
                       for package in dog_result.get('packages', [])
                       for issue in package.get('issues', []))
    yara_detected = any(exact_package_match(typo_name, item['file_path'].split('/')[0])
                        for item in yara_scan_result['malicious'])
    compare_detected = any(typo_name == version_info.get('malicious_package', '')
                           for package_info in comparison_result.values()
                           for version_list in package_info.get('versions', {}).values()
                           for version_info in version_list)
    sbom_detected = any(exact_package_match(typo_name, item['파일명'])
                        and '악성 이유' in item
                        for item in sbom_result['성공한 파일들'])

    if 3.5 <= score < 4.0:
        score += 0.3
        score_breakdown.append("typos bonus(>3.5): [+0.3]")
    elif score >= 4.0:
        score += 1.0
        score_breakdown.append("typos bonus(>4.0): [+1]")
    if dog_detected:
        score += 3
        score_breakdown.append("dog: [+3]")
    if yara_detected:
        score += 1
        score_breakdown.append("yara: [+1]")
    if compare_detected:
        score += 2
        score_breakdown.append("compare: [+2]")
    if sbom_detected:
        score += 2
        score_breakdown.append("sbom: [+2]")
    if yara_detected and dog_detected:
        score += 1
        score_breakdown.append("yara+dog bonus: [+1]")

    if github_info:
        github_url, github_name = github_info
        if github_url:
            github_name_normalized = github_name.lower().replace('_', '-').replace('.', '-') if github_name else ""
            typo_name_normalized = typo_name.lower().replace('_', '-')
            package_github_url_normalized = package_github_url.lower() if package_github_url else None

            if github_url.lower() == package_github_url_normalized:
                score += 2
                score_breakdown.append("git_url steal: [+2]")
            elif github_name_normalized == typo_name_normalized:
                score -= 1
                score_breakdown.append("git_url match: [-1]")
            else:
                score += 0.5
                score_breakdown.append("git_url mismatch: [+0.5]")
        else:
            score += 0.5
            score_breakdown.append("no git_url: [+0.5]")

    if uploader_info:
        uploader_count, package_count, join_within_3_months, join_date = uploader_info
        if uploader_count > 1:
            score -= 1
            score_breakdown.append("uploaders>1: [-1]")
        elif uploader_count == 1:
            if package_count > 0:
                score += 1 / package_count
                score_breakdown.append(f"pkg_count({package_count}): [+{1 / package_count:.2f}]")
            if join_within_3_months:
                score += 1
                score_breakdown.append("join date: [+1]")
        if uploader_count == 1 and package_count >= 2:
            if not join_within_3_months and join_date:
                if (datetime.now() - join_date).days > 365:
                    score -= 2
                    score_breakdown.append("old uploaders : [-2]")

    final_score = min(score, 10)
    if final_score < score:
        score_breakdown.append(f"(capped at 10)")

    return final_score, " + ".join(score_breakdown)


def get_danger_level(score):
    if score >= 8.0:
        return "ALERT"
    elif score >= 6.0:
        return "CRIT"
    elif score >= 5.0:
        return "WARNING"
    elif score >= 4.0:
        return "NOTICE"
    else:
        return "INFO"


def get_sbom_malicious_ids(typo_name, sbom_result, max_ids=10):
    ids = set()
    for item in sbom_result['성공한 파일들']:
        if exact_package_match(typo_name, item['파일명']) and '악성 이유' in item:
            for reason in item['악성 이유']:
                if 'id' in reason:
                    cve_match = re.search(r'CVE-\d{4}-\d+', reason['id'])
                    if cve_match:
                        ids.add(cve_match.group())
                    else:
                        ids.add(reason['id'])

    return list(ids)[:max_ids]


def get_dog_results(typo_name, dog_result, max_issues=3):
    issues = []
    for package in dog_result['packages']:
        if exact_package_match(typo_name, package['package']):
            for issue in package.get('issues', []):
                issues.append({
                    "location": issue['location'],
                    "code": issue['code'],
                    "message": issue['message']
                })

    unique_issues = []
    seen = set()
    for issue in issues:
        key = (issue['location'], issue['message'])
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)

    return unique_issues[:max_issues]


def is_in_comparison_results(typo_name, comparison_result):
    for package_info in comparison_result.values():
        for version_list in package_info.get('versions', {}).values():
            for version_info in version_list:
                if typo_name == version_info.get('malicious_package', ''):
                    return True
    return False


def get_result_description(typo_name, dog_result, sbom_result, comparison_result):
    result = {"dog_results": [], "sbom_ids": [], "comparison_result": None}

    dog_issues = get_dog_results(typo_name, dog_result)
    if dog_issues:
        result["dog_results"] = dog_issues
        if len(dog_issues) == 3:
            result["dog_results"].append({"message": "..."})

    sbom_ids = get_sbom_malicious_ids(typo_name, sbom_result)
    if sbom_ids:
        result["sbom_ids"] = sbom_ids
        if len(sbom_ids) == 10:
            result["sbom_ids"].append("...")

    if is_in_comparison_results(typo_name, comparison_result):
        result["comparison_result"] = "정상 패키지와 동일한 기능 제공"

    return result


def fetch_pypi_url(package_name):
    json_url = f"https://pypi.org/pypi/{package_name}/json"
    json_response = requests.get(json_url)

    if json_response.status_code == 200:
        return f"https://pypi.org/project/{package_name}/"
    else:
        return "no pypi url"


def fetch_package_github_url(package_name):
    json_url = f"https://pypi.org/pypi/{package_name}/json"
    json_response = requests.get(json_url)

    if json_response.status_code == 200:
        data = json_response.json()
        project_urls = data['info'].get('project_urls')

        if project_urls:
            if 'Source' in project_urls:
                source_url = project_urls['Source']
                match = re.match(r'https?://github\.com/([^/]+)/([^/]+)', source_url)
                if match:
                    return source_url

            if 'Homepage' in project_urls:
                homepage_url = project_urls['Homepage']
                match = re.match(r'https?://github\.com/([^/]+)/([^/]+)', homepage_url)
                if match:
                    return homepage_url

            for url in project_urls.values():
                match = re.match(r'https?://github\.com/([^/]+)/([^/]+)', url)
                if match:
                    return url

    return None


def fetch_uploader_info(package_name):
    url = f"https://pypi.org/project/{package_name}/"
    json_url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(url)
    json_response = requests.get(json_url)

    uploader_count = 0
    join_date = None
    github_url = None
    github_name = None
    project_count = None
    join_within_3_months = None

    if json_response.status_code == 200:
        data = json_response.json()
        project_urls = data['info'].get('project_urls', {})

        if project_urls:
            if 'Source' in project_urls:
                github_url = project_urls['Source']
                match = re.match(r'https?://github\.com/([^/]+)/([^/]+)', github_url)
                if match:
                    github_name = match.group(2)

            if not github_url and 'Homepage' in project_urls:
                homepage_url = project_urls['Homepage']
                match = re.match(r'https?://github\.com/([^/]+)/([^/]+)', homepage_url)
                if match:
                    github_url = homepage_url
                    github_name = match.group(2)

            if not github_url:
                for url in project_urls.values():
                    match = re.match(r'https?://github\.com/([^/]+)/([^/]+)', url)
                    if match:
                        github_url = url
                        github_name = match.group(2)
                        break

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        uploader_tags = soup.select('a[href^="/user/"]')
        uploaders = {tag.text.strip() for tag in uploader_tags}
        uploader_count = len(uploaders)

        if uploader_count == 1:
            uploader_name = list(uploaders)[0]
            uploader_profile_url = f"https://pypi.org/user/{uploader_name}/"
            profile_response = requests.get(uploader_profile_url)
            if profile_response.status_code == 200:
                profile_soup = BeautifulSoup(profile_response.text, 'html.parser')
                profile_info = profile_soup.find('div', class_='author-profile__info')
                if profile_info:
                    time_tag = profile_info.find('time')
                    if time_tag:
                        join_date_str = time_tag.text.strip()
                        join_date = datetime.strptime(join_date_str, "%b %d, %Y")
                        current_date = datetime.now()
                        join_within_3_months = (current_date - join_date).days <= 90
                        project_tags = profile_soup.find_all('a', {"href": lambda href: href and href.startswith("/project/")})
                        project_count = len(project_tags)
                    else:
                        join_within_3_months = False
                        project_count = 0
    return (uploader_count, project_count, join_within_3_months, join_date), (github_url, github_name)


def run_output():
    with open(os.path.join(BASE_DIR, 'final_typos.json'), 'r') as f:
        final_typos = json.load(f)
    with open(os.path.join(BASE_DIR, 'dog_result.json'), 'r') as f:
        dog_result = json.load(f)
    with open(os.path.join(BASE_DIR, 'yara_scan_results.json'), 'r') as f:
        yara_scan_result = json.load(f)
    with open(os.path.join(BASE_DIR, 'comparison_results.json'), 'r') as f:
        comparison_result = json.load(f)
    with open(os.path.join(BASE_DIR, 'sbom_results.json'), 'r', encoding='utf-8') as file:
        sbom_result = json.load(file)

    typo_result = []
    for package_name, typos in final_typos.items():
        for typo in typos:
            typo_name, typo_score = typo
            if typo_score >= 3.0:
                package_github_url = fetch_package_github_url(package_name)
                uploader_info, github_info = fetch_uploader_info(typo_name)
                score, score_breakdown = calculate_score(typo_name, typo_score, dog_result, yara_scan_result, comparison_result, sbom_result, uploader_info, github_info, package_name, package_github_url)
                danger = get_danger_level(score)
                result = get_result_description(typo_name, dog_result, sbom_result, comparison_result)
                pypi_url = fetch_pypi_url(typo_name)
                result_message = f"{package_name}의 타이포스쿼팅 패키지 의심."
                typo_result.append({
                    "name": typo_name,
                    "pypi_url": pypi_url,
                    "score": score,
                    "score_breakdown": score_breakdown,
                    "danger": danger,
                    "result": {
                        "message": result_message,
                        "dog_results": result.get("dog_results", []),
                        "sbom_ids": result.get("sbom_ids", []),
                    }
                })
    typo_result.sort(key=lambda x: x['score'], reverse=True)

    final_result = {
        "typoResult": typo_result,
    }

    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump(final_result, json_file, ensure_ascii=False, indent=4)