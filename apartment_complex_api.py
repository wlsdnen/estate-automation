"""
법정동 코드로 아파트 단지 목록을 조회하는 API 래퍼
"""

from typing import Dict, List

import requests

DEFAULT_SERVICE_KEY = "HM//9e1e677T4gTHNhoZjQpeIL0MvpaKqIsm+Tphr7GdqYpjvBt95sxFNkWG5BigL258GGwUULXRXPF56QJbDA=="
DEFAULT_BJD_CODE = "1174010600"


def fetch_apartment_complexes_by_legal_code(
    service_key: str, bjd_code: str, num_of_rows: int = 100
) -> List[Dict]:
    """
    법정동 코드로 아파트 단지 목록을 조회합니다.

    Args:
        service_key (str): 공공데이터포털 서비스키
        bjd_code (str): 법정동 코드
        num_of_rows (int): 한 번에 조회할 최대 단지 수

    Returns:
        List[Dict]: [{kaptCode, kaptName, bjdCode, addr}, ...]
    """
    url = "http://apis.data.go.kr/1613000/AptListService3/getLegaldongAptList3"
    params = {
        "serviceKey": service_key,
        "bjdCode": bjd_code,
        "numOfRows": num_of_rows,
        "pageNo": 1,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get("response", {}).get("body", {}).get("items", [])
        result = []
        for item in items:
            result.append(
                {
                    "kaptCode": item.get("kaptCode"),
                    "kaptName": item.get("kaptName"),
                    "bjdCode": item.get("bjdCode"),
                    "addr": f"{item.get('as1', '')} {item.get('as2', '')} {item.get('as3', '')}".strip(),
                }
            )
        return result
    except Exception as e:
        print(f"[ERROR] 아파트 단지 목록 조회 실패: {e}")
        return []


def main():
    """
    예시 실행: 기본 서비스키와 법정동 코드로 단지 목록 조회
    """
    complexes = fetch_apartment_complexes_by_legal_code(
        DEFAULT_SERVICE_KEY, DEFAULT_BJD_CODE
    )
    for complex_info in complexes:
        print(
            f"[{complex_info['kaptCode']}] {complex_info['kaptName']} - {complex_info['addr']}"
        )


if __name__ == "__main__":
    main()
