import requests
# import xmltodict

SERVICE_KEY = "HM//9e1e677T4gTHNhoZjQpeIL0MvpaKqIsm+Tphr7GdqYpjvBt95sxFNkWG5BigL258GGwUULXRXPF56QJbDA=="
BJD_CODE = "1174010600"

def get_apartment_list_by_bjd_code(service_key: str, bjd_code: str, num_of_rows: int = 100) -> list[dict]:
    """
    법정동 코드로 아파트 단지 목록을 조회합니다. JSON 응답 기반, 실 구조 반영.

    Returns:
        list[dict]: [{kaptCode, kaptName, kaptAddr}, ...]
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

        # 방어적으로 필터링
        result = []
        for item in items:
            result.append({
                "kaptCode": item.get("kaptCode"),
                "kaptName": item.get("kaptName"),
                "bjdCode": item.get("bjdCode"),
                "addr": f"{item.get('as1', '')} {item.get('as2', '')} {item.get('as3', '')}"
            })

        return result

    except Exception as e:
        print(f"[ERROR] 아파트 목록 조회 실패: {e}")
        return []


apts = get_apartment_list_by_bjd_code(SERVICE_KEY, BJD_CODE)
for apt in apts:
    print(f"[{apt['kaptCode']}] {apt['kaptName']} - {apt['addr']}")