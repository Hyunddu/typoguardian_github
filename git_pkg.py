import json


def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        print(f"JSON 파일 파싱 오류: {e}")
        return None


results_data = load_json_file('results.json')
git_package_list = load_json_file('git_package_list.json')
mal_data = load_json_file('mal.json')

if results_data is None or git_package_list is None or mal_data is None:
    print("JSON 파일을 로드하는 중 오류가 발생.")
    exit()

typo_results = results_data.get('typoResult', [])

output_data = {}

for result in typo_results:
    package_name = result['name']
    pypi_url = result.get('pypi_url', "")
    if pypi_url == "no pypi url":
        for git_url, packages in git_package_list.items():
            if package_name in packages:
                if git_url not in output_data:
                    output_data[git_url] = {}
                if package_name not in output_data[git_url] or output_data[git_url][package_name]['score'] < result['score']:
                    result['danger'] += " - 삭제 혹은 오타 패키지 존재"
                    output_data[git_url][package_name] = {
                        "name": result['name'],
                        "pypi_url": result['pypi_url'],
                        "score": result['score'],
                        "score_breakdown": result['score_breakdown'],
                        "danger": result['danger'],
                        "result": result['result']
                    }
    elif result.get('score', 0) >= 6.0:
        for git_url, packages in git_package_list.items():
            if package_name in packages:
                if git_url not in output_data:
                    output_data[git_url] = {}
                if package_name not in output_data[git_url] or output_data[git_url][package_name]['score'] < result['score']:
                    output_data[git_url][package_name] = {
                        "name": result['name'],
                        "pypi_url": result['pypi_url'],
                        "score": result['score'],
                        "score_breakdown": result['score_breakdown'],
                        "danger": result['danger'],
                        "result": result['result']
                    }

for mal_pkg in mal_data:
    is_in_results = False
    for result in typo_results:
        if result['name'] == mal_pkg:
            is_in_results = True
            for git_url, packages in git_package_list.items():
                if mal_pkg in packages:
                    if git_url not in output_data:
                        output_data[git_url] = {}
                    if mal_pkg not in output_data[git_url] or output_data[git_url][mal_pkg]['score'] < 10:
                        modified_result = result.copy()
                        modified_result['score'] = 10
                        modified_result['danger'] = "malware"
                        output_data[git_url][mal_pkg] = modified_result
            break

    if not is_in_results:
        for git_url, packages in git_package_list.items():
            if mal_pkg in packages:
                if git_url not in output_data:
                    output_data[git_url] = {}
                if mal_pkg not in output_data[git_url] or output_data[git_url][mal_pkg]['score'] < 10:
                    output_data[git_url][mal_pkg] = {
                        "name": mal_pkg,
                        "score": 10,
                        "danger": "malware"
                    }

sorted_output_data = {}

for git_url in output_data:
    sorted_output_data[git_url] = sorted(output_data[git_url].values(), key=lambda x: x['score'], reverse=True)

sorted_urls = sorted(sorted_output_data.items(), key=lambda x: x[1][0]['score'], reverse=True)
final_output_data = dict(sorted_urls)

with open('github_results.json', 'w', encoding='utf-8') as output_file:
    json.dump(final_output_data, output_file, ensure_ascii=False, indent=4)
print("github_results.json 저장되었습니다.")
