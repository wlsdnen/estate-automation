from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
import time


def login_homesdid(user_id: str, user_pw: str, headless: bool = True):
    # 1. 크롬 옵션 설정
    options = Options()
    if headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1280,960')
    options.add_argument("--disable-blink-features=AutomationControlled")

    # ✅ HTTP 사이트 대응 옵션 추가
    options.add_argument('--allow-insecure-localhost')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--unsafely-treat-insecure-origin-as-secure=http://homesdid.co.kr')

    # Mac OS 특화 옵션 (시스템 팝업 최소화)
    options.add_argument("--disable-blink-features=AutomationControlled")

    try:
        # 2. 브라우저 실행
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)  # 최대 대기 시간

        # 3. 로그인 페이지 접속
        login_url = 'http://homesdid.co.kr/mmc/member/login.asp'
        driver.get(login_url)

        # 4. 아이디/비밀번호 입력
        driver.find_element(By.ID, 'userid').send_keys(user_id)
        driver.find_element(By.ID, 'userpw').send_keys(user_pw)

        # 5. 로그인 버튼 클릭 (자바스크립트 함수 실행)
        driver.execute_script("memberLogin();")
        time.sleep(2)  # 로그인 처리 대기

        # 6. 로그인 성공 확인
        current_url = driver.current_url
        if "login.asp" in current_url:
            print("❌ 로그인 실패: 아이디 또는 비밀번호를 확인하세요.")
            driver.quit()
            return False

        print("✅ 로그인 성공:", current_url)

        # 7. 세션 유지 상태에서 driver 객체 반환 (선택)
        return driver  # 후속 작업 가능

    except (NoSuchElementException, TimeoutException) as e:
        print("❌ 요소 탐색 실패:", str(e))
    except WebDriverException as e:
        print("❌ 드라이버 실행 실패:", str(e))
    except Exception as e:
        print("❌ 예외 발생:", str(e))


# ✅ 실행
if __name__ == "__main__":
    login_homesdid(user_id='c4481000', user_pw='c267123410', headless=False)
