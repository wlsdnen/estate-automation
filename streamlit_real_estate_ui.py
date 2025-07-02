import datetime
import re
import sqlite3

import requests
import streamlit as st
from apartment_complex_api import fetch_apartment_complexes_by_legal_code
from naver_real_estate_parser import (
    fetch_article_data,
    get_redirected_article_url,
    parse_article_data,
)

SERVICE_KEY = "HM//9e1e677T4gTHNhoZjQpeIL0MvpaKqIsm+Tphr7GdqYpjvBt95sxFNkWG5BigL258GGwUULXRXPF56QJbDA=="


@st.cache_resource
def get_conn():
    return sqlite3.connect("database/address.db", check_same_thread=False)


conn = get_conn()


def map_api_to_form_fields(parsed_data: dict) -> dict:
    move_in_type = parsed_data["move_in"].get("type", "")
    move_in_date = parsed_data["move_in"].get("date", "")
    move_in_negotiate = parsed_data["move_in"].get("negotiable", False)

    if move_in_type == "즉시입주" or "즉시" in str(move_in_type):
        move_in_type_radio = "즉시 입주"
        move_in_date_value = ""
    else:
        move_in_type_radio = "날짜 선택"
        move_in_date_value = move_in_date if move_in_date else ""

    price_info = parsed_data.get("price_info", {})
    form_data = {
        "property_type": parsed_data.get("property_type", ""),
        "complex_name": parsed_data.get("complex_name", ""),
        "building_usage": parsed_data.get("building_usage", ""),
        "direction_base": parsed_data.get("direction", {}).get("based_on", ""),
        "direction": parsed_data.get("direction", {}).get("aspect", ""),
        "floor": str(parsed_data.get("address", {}).get("floor", "")),
        "address_dong": str(parsed_data.get("address", {}).get("dong", "")),
        "address_ho": str(parsed_data.get("address", {}).get("ho", "")),
        "num_rooms": str(parsed_data.get("num_rooms", "")),
        "num_bathrooms": str(parsed_data.get("num_bathrooms", "")),
        "entrance_type": parsed_data.get("entrance_type", ""),
        "supply_area": str(parsed_data.get("supply_area", "")),
        "supply_area_type": parsed_data.get("supply_area_type", ""),
        "exclusive_area": str(parsed_data.get("exclusive_area", "")),
        "deal_type": parsed_data.get("trade_type", ""),
        "move_in_type": move_in_type_radio,
        "move_in_date_value": move_in_date_value,
        "move_in_negotiate": move_in_negotiate,
        "parking_total_spaces": str(
            parsed_data.get("parking", {}).get("total_spaces", "")
        ),
        "parking_per_household": str(
            parsed_data.get("parking", {}).get("per_household", "")
        ),
    }

    deal_type = parsed_data.get("trade_type", "")
    if deal_type == "매매":
        form_data.update(
            {
                "sale_price": str(price_info.get("sale_price", "")),
                "loan_amount": str(price_info.get("loan_amount", "")),
                "loan_info": price_info.get("loan_type", ""),
            }
        )
    elif deal_type == "전세":
        form_data.update(
            {
                "jeonse_price": str(price_info.get("jeonse_price", "")),
                "loan_amount": str(price_info.get("loan_amount", "")),
                "loan_info": price_info.get("loan_type", ""),
            }
        )
    elif deal_type == "월세":
        form_data.update(
            {
                "deposit": str(price_info.get("deposit", "")),
                "rent_price": str(price_info.get("rent_price", "")),
                "loan_amount": str(price_info.get("loan_amount", "")),
                "loan_info": price_info.get("loan_type", ""),
            }
        )
    elif deal_type == "단기":
        form_data.update(
            {
                "deposit": str(price_info.get("deposit", "")),
                "rent_price": str(price_info.get("rent_price", "")),
                "contract_period_month": price_info.get("contract_period_month", ""),
                "contract_period_condition": (
                    "협의없음"
                    if move_in_negotiate is None
                    else ("이내 협의가능" if move_in_negotiate else "협의없음")
                ),
                "loan_amount": str(price_info.get("loan_amount", "")),
                "loan_info": price_info.get("loan_type", ""),
            }
        )

    return form_data


def get_beopjeongdong_code_ui(conn):
    st.markdown("### 지번 주소 입력")
    # 시도, 시군구, 읍면동, 리를 한 줄에 배치
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sido = st.selectbox(
            "시도",
            [
                r[0]
                for r in conn.execute(
                    "SELECT DISTINCT 시도명 FROM legal_dong WHERE 시도명 IS NOT NULL ORDER BY 시도명"
                )
            ],
        )
    with col2:
        sigungu = st.selectbox(
            "시군구",
            [
                r[0]
                for r in conn.execute(
                    "SELECT DISTINCT 시군구명 FROM legal_dong WHERE 시도명=? AND 시군구명 IS NOT NULL ORDER BY 시군구명",
                    (sido,),
                )
            ],
        )
    with col3:
        eupmyeon = st.selectbox(
            "읍면동",
            [
                r[0]
                for r in conn.execute(
                    "SELECT DISTINCT 읍면동명 FROM legal_dong WHERE 시도명=? AND 시군구명=? AND 읍면동명 IS NOT NULL ORDER BY 읍면동명",
                    (sido, sigungu),
                )
            ],
        )
    with col4:
        ri_query = "SELECT DISTINCT 리명 FROM legal_dong WHERE 시도명=? AND 시군구명=? AND 읍면동명=? AND 리명 IS NOT NULL ORDER BY 리명"
        ri_result = [r[0] for r in conn.execute(ri_query, (sido, sigungu, eupmyeon))]
        ri = st.selectbox("리", ri_result if ri_result else ["(해당 없음)"])
    # 본번, 부번도 한 줄에 배치
    col_bun, col_ji = st.columns(2)
    with col_bun:
        bun = st.text_input("본번", "")
    with col_ji:
        ji = st.text_input("부번", "")

    if ri != "(해당 없음)":
        query = "SELECT 법정동코드 FROM legal_dong WHERE 시도명=? AND 시군구명=? AND 읍면동명=? AND 리명=? ORDER BY 생성일자 DESC LIMIT 1"
        params = (sido, sigungu, eupmyeon, ri)
    else:
        query = "SELECT 법정동코드 FROM legal_dong WHERE 시도명=? AND 시군구명=? AND 읍면동명=? AND 리명 IS NULL ORDER BY 생성일자 DESC LIMIT 1"
        params = (sido, sigungu, eupmyeon)

    row = conn.execute(query, params).fetchone()
    code = str(row[0]).zfill(10) if row else None
    bunji = f"{bun}" + (f"-{ji}" if ji else "")
    full_addr = (
        f"{sido} {sigungu} {eupmyeon} {ri if ri != '(해당 없음)' else ''} {bunji}"
    )
    return code, full_addr.strip(), sido, sigungu, bun, ji


def get_br_title_info(service_key, sigungu_cd, bjdong_cd, bun, ji):
    url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
    params = {
        "serviceKey": service_key,
        "sigunguCd": sigungu_cd,
        "bjdongCd": bjdong_cd,
        "platGbCd": "0",
        "bun": bun.zfill(4),
        "ji": ji.zfill(4) if ji else "0000",
        "numOfRows": 1,
        "pageNo": 1,
        "_type": "json",
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        item = data["response"]["body"]["items"]["item"][0]
        return {
            "건물명": item.get("bldNm", ""),
            "건축물용도": item.get("mainPurpsCdNm", ""),
            "연면적": item.get("totArea", ""),
            "사용승인일": item.get("useAprDay", ""),
            "구조": item.get("strctCdNm", ""),
        }
    except:
        return {}


st.title("매물 자동 정보 생성기")

bjd_code, full_address, sido, sigungu, bun, ji = get_beopjeongdong_code_ui(conn)

# 네이버 매물번호 → 정보 조회
article_no = st.text_input("네이버 매물번호 (선택)", placeholder="예: 2531022483")
naver_info = {}
br_title_info = {}
show_br_title_info = False

# 조회 결과를 입력 폼에 자동 반영할 변수 준비
naver_parsed = {}
br_title_parsed = {}

# '조회' 버튼을 가운데 정렬, 넓게
center_col = st.columns([1, 2, 1])
with center_col[1]:
    if st.button("조회", key="naver_info_btn", use_container_width=True):
        if article_no:
            try:
                redirected_article_url = get_redirected_article_url(article_no)
                article_data = fetch_article_data(article_no, redirected_article_url)
                naver_info = parse_article_data(article_data)
                naver_parsed = map_api_to_form_fields(naver_info)
                naver_parsed = naver_parsed.copy() if naver_info else {}
            except Exception as e:
                naver_parsed = {}
        # 표제부 정보 조회
        if bjd_code:
            sigungu_cd = bjd_code[:5]
            bjdong_cd = bjd_code[5:]
            br_title_info = get_br_title_info(
                SERVICE_KEY, sigungu_cd, bjdong_cd, bun, ji
            )
            br_title_parsed = br_title_info.copy() if br_title_info else {}
        else:
            br_title_parsed = {}

# --- 구분선 ---
st.divider()

# 기본 매물 정보 제목 (폰트 약간 크게)
st.markdown("### 기본 매물 정보", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# 입력 폼의 기본값을 네이버/표제부 정보에서 가져오도록 처리
if "naver_parsed" not in st.session_state:
    st.session_state["naver_parsed"] = {}
if "br_title_parsed" not in st.session_state:
    st.session_state["br_title_parsed"] = {}

# 조회 버튼 클릭 시 session_state에 값 저장
if naver_parsed:
    st.session_state["naver_parsed"] = naver_parsed
if br_title_parsed:
    st.session_state["br_title_parsed"] = br_title_parsed

naver_parsed = st.session_state.get("naver_parsed", {})
br_title_parsed = st.session_state.get("br_title_parsed", {})

# 건축물 용도 판단
main_purpose = br_title_parsed.get("건축물용도", "") if br_title_parsed else ""
is_apartment = "공동주택" in main_purpose

# 단지 선택 (공동주택만)
danji_name = ""
if is_apartment and bjd_code:
    apt_list = fetch_apartment_complexes_by_legal_code(SERVICE_KEY, bjd_code)
    if apt_list:
        danji_options = [f"{apt['kaptName']} ({apt['addr']})" for apt in apt_list]
        selected_danji_idx = st.selectbox(
            "단지 목록",
            options=list(range(len(danji_options))),
            format_func=lambda i: danji_options[i],
        )
        danji_name = apt_list[selected_danji_idx]["kaptName"]
    else:
        st.warning("공동주택이지만 단지 목록이 없습니다.")
elif main_purpose and not is_apartment:
    st.info("공동주택이 아닌 건축물입니다. 단지 선택 없이 진행됩니다.")

# 고정 셀렉트 박스
property_types = [
    "아파트",
    "주상복합",
    "재건축",
    "아파트 분양권",
    "오피스텔 분양권",
    "주상복합 분양권",
    "오피스텔",
    "원룸-방",
    "사무실",
    "주택-빌라/연립",
    "주택-빌라/연립(단지)",
    "주택-단독/다가구",
    "주택-전원/농가주택",
    "주택-상가주택",
    "주택-한옥주택",
    "상가점포",
    "토지/임야",
    "공장-공장/창고",
    "공장-지식산업센터",
    "재개발",
    "건물-빌딩/건물",
    "건물-상가건물",
    "건물-숙박/콘도",
    "건물-기타",
]
purposes = [
    "단독주택",
    "공동주택",
    "제1종 근린생활시설",
    "제2종 근린생활시설",
    "문화 및 집회시설",
    "종교시설",
    "판매시설",
    "운수시설",
    "의료시설",
    "교육연구시설",
    "노유자(幼者: 노인 및 어린이)시설",
    "수련시설",
    "운동시설",
    "업무시설",
    "숙박시설",
    "위락(위안)시설",
    "공장",
    "창고시설",
    "위험물 저장 및 처리 시설",
    "자동차 관련 시설",
    "동물 및 식물 관련 시설",
    "자원순환 관련 시설",
    "교정 및 군사 시설",
    "방송통신시설",
    "발전시설",
    "묘지 관련 시설",
    "관광 휴게시설",
    "장례시설",
    "야영장 시설",
    "미등기건물",
    "그 밖에 토지의 정착물",
]
directions = ["동", "서", "남", "북", "북동", "남동", "북서", "남서"]
room_positions = ["거실", "안방"]

# 입력 폼 (기본 매물 정보)
col_type = st.columns(2)
with col_type[0]:
    purpose_value = br_title_parsed.get(
        "건축물용도", naver_parsed.get("building_usage", "")
    )
    purpose = st.selectbox(
        "건축물 용도",
        purposes,
        index=purposes.index(purpose_value) if purpose_value in purposes else 0,
    )
with col_type[1]:
    property_type = st.selectbox(
        "매물 종류",
        property_types,
        index=(0),
    )

# 방향(위치), 방향
pos_value = naver_parsed.get("direction_base", "")
dir_value = naver_parsed.get("direction", "")

col_dir1, col_dir2 = st.columns(2)
with col_dir1:
    pos = st.selectbox(
        "방향(위치)",
        room_positions,
        index=room_positions.index(pos_value) if pos_value in room_positions else 0,
    )
with col_dir2:
    dir_ = st.selectbox(
        "방향",
        directions,
        index=directions.index(dir_value) if dir_value in directions else 0,
    )

# 층, 방수, 욕실수
col_a, col_b, col_c = st.columns(3)
with col_a:
    floor = st.text_input("층", naver_parsed.get("floor", ""))
with col_b:
    room = st.text_input("방수", naver_parsed.get("num_rooms", ""))
with col_c:
    bath = st.text_input("욕실수", naver_parsed.get("num_bathrooms", ""))

# 공급면적/전용면적
area_col1, area_col2 = st.columns(2)
with area_col1:
    supply_area = st.text_input("공급면적 (㎡)", naver_parsed.get("supply_area", ""))
with area_col2:
    exclusive_area = st.text_input(
        "전용면적 (㎡)", naver_parsed.get("exclusive_area", "")
    )

# --- 구분선 ---
st.divider()

# 거래 조건 입력란 바로 위에 변수 초기화
# 거래 조건 입력 제목 (폰트 약간 크게)
st.markdown("### 거래 조건", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

deposit = ""
rent = ""
management = ""

# 거래 조건 입력
deal_type = st.radio(
    "거래 종류",
    ["매매", "전세", "월세", "단기"],
    index=["매매", "전세", "월세", "단기"].index(naver_parsed.get("deal_type", "매매")),
)


# 거래 조건별 자동 세팅
sale_price = loan_amount = loan_type = deposit = rent = ""
term_months = term_condition = ""

if deal_type == "매매":
    sale_price = st.text_input(
        "매매가 (만원)", naver_parsed.get("sale_price", ""), key="매매_매매가"
    )
    loan_amount = st.text_input(
        "융자금 (만원)", naver_parsed.get("loan_amount", ""), key="매매_융자금"
    )
    loan_info_options = [
        "미표기",
        "융자금 없음",
        "시세대비 30% 미만",
        "시세대비 30% 이상",
    ]
    loan_info_value = naver_parsed.get("loan_info") or "미표기"
    if loan_info_value not in loan_info_options:
        loan_info_value = "미표기"
    loan_type = st.radio(
        "융자금 정보",
        loan_info_options,
        index=loan_info_options.index(loan_info_value),
        key="매매_융자정보",
    )
elif deal_type == "전세":
    deposit = st.text_input(
        "전세가 (만원)", naver_parsed.get("charter_price", ""), key="전세_보증금"
    )
    loan_amount = st.text_input(
        "융자금 (만원)", naver_parsed.get("loan_amount", ""), key="전세_융자금"
    )
    loan_info_options = [
        "미표기",
        "융자금 없음",
        "시세대비 30% 미만",
        "시세대비 30% 이상",
    ]
    loan_info_value = naver_parsed.get("loan_info") or "미표기"
    if loan_info_value not in loan_info_options:
        loan_info_value = "미표기"
    loan_type = st.radio(
        "융자금 정보",
        loan_info_options,
        index=loan_info_options.index(loan_info_value),
        key="전세_융자정보",
    )

elif deal_type == "월세":
    deposit = st.text_input(
        "보증금 (만원)", naver_parsed.get("deposit", ""), key="월세_보증금"
    )
    rent = st.text_input(
        "월세 (만원)", naver_parsed.get("rent_price", ""), key="월세_월세"
    )
    loan_amount = st.text_input(
        "융자금 (만원)", naver_parsed.get("loan_amount", ""), key="월세_융자금"
    )
    loan_info_options = [
        "미표기",
        "융자금 없음",
        "시세대비 30% 미만",
        "시세대비 30% 이상",
    ]
    loan_info_value = naver_parsed.get("loan_info") or "미표기"
    if loan_info_value not in loan_info_options:
        loan_info_value = "미표기"
    loan_type = st.radio(
        "융자금 정보",
        loan_info_options,
        index=loan_info_options.index(loan_info_value),
        key="월세_융자정보",
    )

elif deal_type == "단기":
    deposit = st.text_input(
        "보증금 (만원)", naver_parsed.get("deposit", ""), key="단기_보증금"
    )
    rent = st.text_input(
        "월세 (만원)", naver_parsed.get("rent_price", ""), key="단기_월세"
    )
    term_months = st.selectbox(
        "계약 기간 (개월)",
        list(range(1, 24)),
        index=int(naver_parsed.get("contract_period_month", 1)) - 1,
        key="단기_개월수",
    )
    term_condition = st.radio(
        "기간 조건",
        ["협의없음", "이내 협의가능", "이상 협의가능"],
        index=["협의없음", "이내 협의가능", "이상 협의가능"].index(
            naver_parsed.get("contract_period_condition", "협의없음")
        ),
        key="단기_조건",
    )
    loan_amount = st.text_input(
        "융자금 (만원)", naver_parsed.get("loan_amount", ""), key="단기_융자금"
    )
    loan_info_options = [
        "미표기",
        "융자금 없음",
        "시세대비 30% 미만",
        "시세대비 30% 이상",
    ]
    loan_info_value = naver_parsed.get("loan_info") or "미표기"
    if loan_info_value not in loan_info_options:
        loan_info_value = "미표기"
    loan_type = st.radio(
        "융자금 정보",
        loan_info_options,
        index=loan_info_options.index(loan_info_value),
        key="단기_융자정보",
    )

# --- 구분선 ---
st.divider()

# 입주 가능일 입력 제목 (폰트 약간 크게)
st.markdown("### 입주 가능일 선택", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# 입주가능일 파싱: '2026년 6월 1일 협의가능' → 날짜, 협의가능
move_in_type_raw = naver_parsed.get("move_in_type", "")
move_in_date_value = naver_parsed.get("move_in_date_value", "")
move_in_negotiate = naver_parsed.get("move_in_negotiate", False)

# 기본값 판단
move_in_radio_default = 0 if move_in_type_raw in ["즉시입주", "즉시 입주"] else 1

if move_in_radio_default == 1 and move_in_date_value:
    try:
        y, m, d = map(int, move_in_date_value.split("-"))
        default_date = datetime.date(y, m, d)
    except:
        default_date = None
else:
    default_date = None

move_in_type = st.radio(
    "입주 가능 방식", ["즉시 입주", "날짜 선택"], index=move_in_radio_default
)

move_in_date = None
if move_in_type == "날짜 선택":
    move_in_date = st.date_input(
        "입주 가능일",
        value=default_date if default_date else None,
        format="YYYY-MM-DD",
    )

move_in_negotiate = st.checkbox("협의 가능", value=move_in_negotiate)

# 최종 문자열로 가공
if move_in_type == "즉시 입주":
    move_in = "즉시입주"
elif move_in_type == "날짜 선택" and move_in_date:
    move_in = move_in_date.strftime("%Y-%m-%d")
    if move_in_negotiate:
        move_in += " 협의가능"
else:
    move_in = ""

# --- 구분선 ---
st.divider()

# 매물 설명 제목 (폰트 약간 크게)
st.markdown("### 기타 정보", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

feature = st.text_input("매물 특징", "")
detail = st.text_area("상세 설명", "")

# --- 구분선 ---
st.divider()


def format_summary(
    address,
    property_type,
    danji_name,
    purpose,
    floor,
    room,
    bath,
    supply_area,
    exclusive_area,
    pos,
    dir_,
    deal_type,
    sale_price,
    deposit,
    rent,
    loan_amount,
    loan_type,
    term_months,
    term_condition,
    move_in,
    feature,
    detail,
):
    lines = []
    # 1. 주소 및 기본 정보
    if address:
        lines.append(f"주소: {address}")
    if danji_name:
        lines.append(f"단지명: {danji_name}")
    if property_type:
        lines.append(f"매물 종류: {property_type}")
    if purpose:
        lines.append(f"건축물 용도: {purpose}")
    if floor:
        lines.append(f"해당 층: {floor}")
    if room:
        lines.append(f"방 수: {room}")
    if bath:
        lines.append(f"욕실 수: {bath}")
    if supply_area:
        lines.append(f"공급면적: {supply_area}㎡")
    if exclusive_area:
        lines.append(f"전용면적: {exclusive_area}㎡")
    if pos or dir_:
        pos_dir = []
        if pos:
            pos_dir.append(f"위치: {pos}")
        if dir_:
            pos_dir.append(f"방향: {dir_}")
        lines.append(", ".join(pos_dir))
    # 2. 거래 조건
    lines.append(f"거래 종류: {deal_type}")
    if deal_type == "매매":
        if sale_price:
            lines.append(f"매매가: {sale_price}만원")
        if loan_amount:
            lines.append(f"융자금: {loan_amount}만원")
        if loan_type:
            lines.append(f"융자금 정보: {loan_type}")
    elif deal_type == "전세":
        if deposit:
            lines.append(f"전세가: {deposit}만원")
        if loan_amount:
            lines.append(f"융자금: {loan_amount}만원")
        if loan_type:
            lines.append(f"융자금 정보: {loan_type}")
    elif deal_type == "월세":
        if deposit:
            lines.append(f"보증금: {deposit}만원")
        if rent:
            lines.append(f"월세: {rent}만원")
        if loan_amount:
            lines.append(f"융자금: {loan_amount}만원")
        if loan_type:
            lines.append(f"융자금 정보: {loan_type}")
    elif deal_type == "단기":
        if deposit:
            lines.append(f"보증금: {deposit}만원")
        if rent:
            lines.append(f"월세: {rent}만원")
        if term_months:
            lines.append(f"계약 기간: {term_months}개월")
        if term_condition:
            lines.append(f"기간 조건: {term_condition}")
        if loan_amount:
            lines.append(f"융자금: {loan_amount}만원")
        if loan_type:
            lines.append(f"융자금 정보: {loan_type}")
    # 3. 입주 가능일
    if move_in:
        lines.append(f"입주 가능일: {move_in}")
    # 4. 매물 특징 및 상세 설명
    if feature:
        lines.append(f"매물 특징: {feature}")
    if detail:
        lines.append(f"상세 설명: {detail}")
    return "\n".join(lines)


# 요약 생성 버튼 가운데, 넓게
center_col2 = st.columns([1, 2, 1])
with center_col2[1]:
    if st.button("요약 생성", use_container_width=True):
        if bjd_code:
            # 입력값 수집
            summary = format_summary(
                address=full_address,
                property_type=property_type,
                danji_name=danji_name,
                purpose=purpose,
                floor=floor,
                room=room,
                bath=bath,
                supply_area=supply_area,
                exclusive_area=exclusive_area,
                pos=pos,
                dir_=dir_,
                deal_type=deal_type,
                sale_price=sale_price,
                deposit=deposit,
                rent=rent,
                loan_amount=loan_amount,
                loan_type=loan_type,
                term_months=term_months,
                term_condition=term_condition,
                move_in=move_in,
                feature=feature,
                detail=detail,
            )
            st.text_area("요약 내용", summary, height=400)
        else:
            st.warning("법정동 코드가 없습니다. 주소를 다시 확인해 주세요.")
