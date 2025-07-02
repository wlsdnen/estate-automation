import re

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def parse_article_data(data: dict) -> dict:
    detail = data.get("articleDetail", {})
    addition = data.get("articleAddition", {})
    facility = data.get("articleFacility", {})
    space = data.get("articleSpace", {})
    price = data.get("articlePrice", {})
    land = data.get("landPrice", {})

    trade_type = addition.get("tradeTypeName", "")
    property_type = addition.get("realEstateTypeName", "")
    complex_name = addition.get("articleName", "")
    building_usage = detail.get("lawUsage") or detail.get("principalUse")

    supply_area = space.get("supplySpace")
    exclusive_area = space.get("exclusiveSpace")
    area_label = addition.get("areaName")

    dong = (
        land.get("dongNm", "")
        or detail.get("originBuildingName", "")
        or detail.get("buildingName", "")
    )
    ho = land.get("hoFloor", "")
    floor_info = addition.get("floorInfo", "")
    floor = floor_info.split("/")[0] if "/" in floor_info else floor_info

    direction_base_name = facility.get("directionBaseTypeName", "")
    direction_name = facility.get("directionTypeName", "")
    direction_base = direction_base_name.split()[0] if direction_base_name else None
    direction = direction_name.replace("향", "") if direction_name else None

    num_rooms = detail.get("roomCount")
    num_bathrooms = detail.get("bathroomCount")
    entrance_type = facility.get("entranceTypeName")

    move_in = {
        "type": detail.get("moveInTypeName"),
        "date": detail.get("moveInPossibleYmd"),
        "negotiable": detail.get("moveInDiscussionPossibleYN", None),
    }

    parking_total = detail.get("parkingCount") or detail.get("aptParkingCount")
    parking_per_household = detail.get("parkingPerHouseholdCount") or detail.get(
        "aptParkingCountPerHousehold"
    )

    # === 🧠 거래유형별 가격 조건 처리 ===
    price_info = {}
    loan_amount = price.get("financePrice", 0)
    loan_type = None  # 원본 데이터에 명시적 필드가 없으므로 None 처리

    if trade_type == "매매":
        price_info = {
            "sale_price": price.get("dealPrice", ""),
            "loan_amount": loan_amount,
            "loan_type": loan_type,
        }
    elif trade_type == "전세":
        price_info = {
            "jeonse_price": price.get("warrantPrice", 0),
            "loan_amount": loan_amount,
            "loan_type": loan_type,
        }
    elif trade_type == "월세":
        price_info = {
            "deposit": price.get("warrantPrice", 0),
            "rent_price": price.get("rentPrice", 0),
            "loan_amount": loan_amount,
            "loan_type": loan_type,
        }
    elif trade_type == "단기임대":
        description = detail.get("detailDescription", "")
        term_month = None
        term_condition = None

        match = re.search(r"(\d+)\s*개월", description)
        if match:
            term_month = int(match.group(1))

        if "이내 협의" in description:
            term_condition = "이내 협의가능"
        elif "이상 협의" in description:
            term_condition = "이상 협의가능"
        elif "협의" in description:
            term_condition = "협의없음"
        else:
            term_condition = "협의없음"

        price_info = {
            "deposit": price.get("warrantPrice", 0),
            "rent_price": price.get("rentPrice", 0),
            "contract_period_month": term_month,
            "contract_period_condition": term_condition,
            "negotiable": move_in.get("negotiable"),
            "loan_amount": loan_amount,
            "loan_type": loan_type,
        }

    result = {
        "trade_type": trade_type,
        "property_type": property_type,
        "complex_name": complex_name,
        "building_usage": building_usage,
        "supply_area": supply_area,
        "supply_area_type": area_label,
        "exclusive_area": exclusive_area,
        "address": {"dong": dong, "ho": ho, "floor": floor},
        "direction": {"based_on": direction_base, "aspect": direction},
        "num_rooms": num_rooms,
        "num_bathrooms": num_bathrooms,
        "entrance_type": entrance_type,
        "move_in": move_in,
        "parking": {
            "total_spaces": parking_total,
            "per_household": parking_per_household,
        },
        "price_info": price_info,
    }

    return result


def get_redirected_article_url(article_no):
    # 크롬 옵션 설정
    options = Options()
    options.add_argument("--headless")  # 창을 띄우지 않음
    options.add_argument("--disable-gpu")

    # 크롬 드라이버 실행
    driver = webdriver.Chrome(options=options)

    # 매물번호 입력
    url = f"https://new.land.naver.com?articleNo={article_no}"

    # 접속
    driver.get(url)

    # 리디렉션된 실제 URL 가져오기
    redirected_url = driver.current_url

    # 드라이버 종료
    driver.quit()

    return redirected_url


def fetch_article_data(article_no, url):
    property_type = ""
    if "complexes" in url:
        property_type = "complexes"
    elif "houses" in url:
        property_type = "houses"
    elif "rooms" in url:
        property_type = "rooms"
    elif "offices" in url:
        property_type = "offices"
    else:
        property_type = "unknown"

    cookies = {
        "PROP_TEST_ID": "636f6f17810a1104aede79e7b62182125b536db034973812dcaf370fd25ec5dc",
        "PROP_TEST_KEY": "1751375135301.e4544f1d3b6b265d777984b64a751b7c8545242c794e2888bd31a591d6c66195",
        "REALESTATE": "Tue%20Jul%2001%202025%2022%3A05%3A35%20GMT%2B0900%20(Korean%20Standard%20Time)",
    }

    headers = {
        "Accept": "*/*",
        "Sec-Fetch-Site": "same-origin",
        # 'Cookie': 'PROP_TEST_ID=a8a05c9a9ff92144fb75599869aa0d3468644345f9d15c777fdaa78b837c3929; PROP_TEST_KEY=1751108735745.1909855a43eb5ed723d99e8ff0750a41225d68ef8de56a5b9214dedc467abaef; REALESTATE=Sat%20Jun%2028%202025%2020%3A05%3A35%20GMT%2B0900%20(Korean%20Standard%20Time)',
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NTExMDg3MzUsImV4cCI6MTc1MTExOTUzNX0.rlSc7IwmE9Xx-CcX41lzG2dwWwsGuGIhgOKZPDcl4DU",
        "Sec-Fetch-Dest": "empty",
        "Referer": f"https://new.land.naver.com/{property_type}?ms=0,0,0&a=APT:ABYG:JGC:PRE&e=RETAIL&articleNo={article_no}",
        "Referer": url,
        "Sec-Fetch-Mode": "cors",
        "Accept-Language": "ko-KR,ko;q=0.9",
        # 'Accept-Encoding': 'gzip, deflate, br',
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15",
        "Priority": "u=3, i",
    }

    params = {
        # "complexNo": "",
    }

    response = requests.get(
        f"https://new.land.naver.com/api/articles/{article_no}",
        params=params,
        cookies=cookies,
        headers=headers,
    )

    data = response.json()

    return data
