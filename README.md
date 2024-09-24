# TypoGuardian GitHub 🛡️

![GitHub stars](https://img.shields.io/github/stars/Hyunddu/typoguardian?style=social)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)

> Detect risky packages using TypoGuardian in the dependency packages of GitHub Python-based projects.

## 🚀 기능 설명

### 1. git_url.py
- GitHub에 등록된 Python 기반 프로젝트 중 스타 수 기준 상위 1000개의 repo URL을 가져옵니다.
- 필요 사항:
  - GitHub 토큰
- 출력: `top_repositories_1000.json`

### 2. git_pkglist.py
- `setup.py`, `pyproject.toml`, `requirements.txt`에 포함된 패키지 리스트를 추출합니다.
- 필요 사항:
  - GitHub 토큰
  - `top_repositories_1000.json` 파일
- 출력: `git_package_list.json`

### 3. extract_value.py
- TypoGuardian에 입력하기 위해 value 값만 추출하고 중복을 제거합니다.
- 출력: `values_only.json`

### 4. git_pkg.py
- TypoGuardian의 결과와 기존 패키지 리스트를 결합합니다.
- 필요 사항:
  - `mal.json`
  - `results.json` (TypoGuardian을 통해 얻음)
  - `git_package_list.json`
- 주요 기능:
  1. `results.json`에서 score가 6.0 이상인 패키지가 포함된 repo_url 식별
  2. pypi_url이 존재하지 않는 패키지가 포함된 repo_url 식별
  3. malware 리스트에 포함된 패키지가 `git_package_list.json`에도 포함된 경우 식별
  4. malware 리스트에 포함되어 있고 `results.json`에도 같은 패키지가 있는 경우 식별

### 5. output.py
- TypoGuardian에서 pypi_url이 없을 경우 발생하는 에러를 해결하기 위한 코드

## 🔗 의존성

이 프로젝트는 [TypoGuardian](https://github.com/Hyunddu/typoguardian)을 사용합니다.

## 🛠️ 설치 및 사용법

(여기에 설치 방법과 사용 예시를 추가하세요)

## 🤝 기여하기

버그를 발견하셨거나 새로운 기능을 제안하고 싶으시다면 이슈를 열어주세요. 풀 리퀘스트도 환영합니다!

## 📞 문의하기

질문이나 피드백이 있으시면 [이슈](https://github.com/Hyunddu/typoguardian_github/issues)를 통해 연락해주세요.

