import asyncio
import logging
import os
import pickle
import random
import time
from typing import Set, Tuple

import aiohttp
import redis
from celery import shared_task
from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from yarl import URL

from instagram_automation.models import FollowerSnapshot, InstagramUser

logger = logging.getLogger("instagram_automation")



CHROME_DRIVER_PATH = '/app/drivers/chromedriver'
COOKIE_FILE_PATH = '/app/cookies/instagram_cookies.pkl'
DEBUG_DIR = '/app/debug'
COOKIE_DIR = '/app/cookies'

os.makedirs(COOKIE_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)

def _create_debug_files(driver: webdriver.Chrome, file_name: str) -> None:
    debug_screenshot_path = os.path.join(DEBUG_DIR, f'{file_name}.png')
    debug_html_path = os.path.join(DEBUG_DIR, f'{file_name}.html')

    driver.save_screenshot(debug_screenshot_path)
    with open(debug_html_path, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    
    logger.info(f"Screenshot saved to: {debug_screenshot_path}")
    logger.info(f"Page HTML saved to: {debug_html_path}")



def _extract_session_data(driver: webdriver.Chrome) -> dict:
    """Extract session data once to share between concurrent operations"""
    js_script = """
        return (async () => {
            try {
                const cache = await caches.open('logging-params-v3');
                const keys = await cache.keys();
                const loggingRequest = keys.find(req => req.url.includes('/data/logging_params/'));
                if (!loggingRequest) return null;

                const response = await cache.match(loggingRequest);
                const data = await response.json();
                return data.appId;
            } catch (e) {
                console.error('Error accessing cache:', e);
                return null;
            }
        })();
        """
    app_id = driver.execute_script(js_script)
    
    if not app_id:
        raise ValueError("Error: Failed to get appId.")
    
    all_cookies = driver.get_cookies()
    required_cookie_names = [
        'datr', 'ig_did', 'ps_l', 'ps_n', 'mid', 'wd', 'dpr', 
        'csrftoken', 'rur', 'sessionid', 'ds_user_id'
    ]
    
    cookies_dict = {cookie['name']: cookie['value'] for cookie in all_cookies if cookie['name'] in required_cookie_names}
    
    if 'sessionid' not in cookies_dict or 'ds_user_id' not in cookies_dict:
        raise ValueError("Error: Missing essential session cookies.")
    
    return {
        'app_id': app_id,
        'cookies': cookies_dict,
        'user_id': cookies_dict['ds_user_id'],
        'csrf_token': cookies_dict['csrftoken']
    }


async def _scrape_follower_list_async(*,
    session: aiohttp.ClientSession,
    session_data: dict,
    list_type: str,
    username: str
) -> Set[str]:
    
    api_path = "followers" if list_type == "Followers" else "following"
    api_url = f"https://www.instagram.com/api/v1/friendships/{session_data['user_id']}/{api_path}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'x-ig-app-id': str(session_data['app_id']),
        'X-CSRFToken': session_data['csrf_token'],
        'Referer': f'https://www.instagram.com/{username}/{api_path}/',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    }
    
    all_user_list = []
    max_id = None
    retry_count = 0
    max_retries = 3
    
    logger.info(f"Starting async fetch of {api_path} for {username}...")
    
    while True:
        params = {"count": 25}
        if max_id: 
            params["max_id"] = max_id
        
        try:
            async with session.get(api_url, headers=headers, params=params) as response:
                
                if response.status != 200:
                    logger.error(f"API request failed with status {response.status}")
                    
                    if response.status == 429:
                        logger.warning("Rate limited - waiting before retry...")
                        await asyncio.sleep(random.uniform(5, 10))
                        continue
                    
                    elif response.status in [500, 502, 503, 504]:
                        if retry_count < max_retries:
                            retry_count += 1
                            logger.warning(f"Server error {response.status}, retry {retry_count}/{max_retries}")
                            await asyncio.sleep(random.uniform(2, 5))
                            continue
                        else:
                            logger.error(f"Max retries exceeded for server error {response.status}")
                            response.raise_for_status()
                    
                    else:
                        response.raise_for_status()
                    
                retry_count = 0
                
                data = await response.json()
                page_user_list = data.get("users", [])
                all_user_list.extend(page_user_list)
                
                logger.info(f"[{list_type}] Fetched {len(page_user_list)} users. Total: {len(all_user_list)}")
                
                if data.get("next_max_id"):
                    max_id = data["next_max_id"]
                    await asyncio.sleep(random.uniform(1, 2))
                else:
                    logger.info(f"[{list_type}] Reached end of list. Total: {len(all_user_list)}")
                    break
                    
        except aiohttp.ClientError as e:
            if retry_count < max_retries:
                retry_count += 1
                logger.warning(f"Network error: {e}, retry {retry_count}/{max_retries}")
                await asyncio.sleep(random.uniform(2, 5))
                continue
            else:
                logger.error(f"Max retries exceeded for network error: {e}")
                raise
        
        except asyncio.TimeoutError:
            if retry_count < max_retries:
                retry_count += 1
                logger.warning(f"Request timeout, retry {retry_count}/{max_retries}")
                await asyncio.sleep(random.uniform(2, 5))
                continue
            else:
                logger.error("Max retries exceeded for timeout")
                raise
        
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}")
            raise
    
    follower_usernames = [user['username'] for user in all_user_list]
    return set(follower_usernames)



async def _perform_concurrent_scraping(*, session_data: dict, username: str) -> Tuple[Set[str], Set[str]]:
    cookie_jar = aiohttp.CookieJar()
    for name, value in session_data['cookies'].items():
        cookie_jar.update_cookies({name: value}, response_url=URL("https://www.instagram.com"))
    
    connector = aiohttp.TCPConnector(
        limit=2,
        limit_per_host=2,
        ssl=True
    )
    
    async with aiohttp.ClientSession(
        cookie_jar=cookie_jar,
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=60)
    ) as session:
        
        followers_task = _scrape_follower_list_async(
            session=session,
            session_data=session_data,
            list_type="Followers",
            username=username
        )
        
        following_task = _scrape_follower_list_async(
            session=session,
            session_data=session_data,
            list_type="Following",
            username=username
        )
        
        followers_set, following_set = await asyncio.gather(
            followers_task, 
            following_task,
            return_exceptions=True
        )
        
        if isinstance(followers_set, Exception) or isinstance(followers_set, BaseException):
            logger.error(f"Followers fetch failed: {followers_set}")
            raise followers_set
        if isinstance(following_set, Exception) or isinstance(following_set, BaseException):
            logger.error(f"Following fetch failed: {following_set}")
            raise following_set
            
        return followers_set, following_set



def _perform_follower_scrape(*, driver: webdriver.Chrome, username: str, password: str, request_id: str) -> None:
    
    try:
        logger.info("Establishing browser context...")
        driver.get(f"https://www.instagram.com/{username}/")
        time.sleep(random.uniform(2, 4))
        
        session_data = _extract_session_data(driver)
        logger.info("Session data extracted successfully")
        
        driver.get(f"https://www.instagram.com/{username}/followers/")
        time.sleep(random.uniform(1, 2))
        
        driver.get(f"https://www.instagram.com/{username}/following/")
        time.sleep(random.uniform(1, 2))
        
        logger.info("Starting concurrent API scraping...")
        followers_set, following_set = asyncio.run(
            _perform_concurrent_scraping(
                session_data=session_data,
                username=username
            )
        )
        
        logger.info("Concurrent scraping complete. Saving to database...")
        
    except Exception as e:
        logger.error(f"Unexpected error while scraping follower/following: {str(e)}")
        raise
    
    profile_user, _ = InstagramUser.objects.get_or_create(
        username=username,
        defaults={"instagram_pk": f"pk_{username}"} #Placeholder pk
    )
    snapshot = FollowerSnapshot.objects.create(profile=profile_user)
    
    all_users_set = followers_set.union(following_set)
    user_map = {}
    for uname in all_users_set:
        user_obj, _ = InstagramUser.objects.get_or_create(
            username=uname,
            defaults={"instagram_pk": f"pk_{uname}"}
        )
        
        user_map[uname] = user_obj
        
    snapshot.followers.add(*[user_map[u] for u in followers_set])
    snapshot.following.add(*[user_map[u] for u in following_set])
    
    logger.info(f"Snapshot created with {len(followers_set)} followers and {len(following_set)} following.")
    


def _perform_ig_login(*, driver: webdriver.Chrome, username: str, password: str, request_id: str) -> None:
    try:
        logger.info("Attempting to log in with cookies...")
        driver.get("https://www.instagram.com/")
        time.sleep(random.uniform(2, 4))
        
        with open(COOKIE_FILE_PATH, 'rb') as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        
        driver.refresh()
        time.sleep(random.uniform(3, 5))

        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, f"a[href*='/{username}/']")))
        logger.info("Successfully logged in using cookies.")
        
    except Exception as e:
        logger.warning(f"Cookie login failed: {e}. Performing manual login.")
        
        try:
        
            driver.get("https://www.instagram.com/accounts/login/")
            wait = WebDriverWait(driver, 20)
            
            username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            time.sleep(random.uniform(1, 3))
            username_field.send_keys(username)
            
            password_field = driver.find_element(By.NAME, "password")
            time.sleep(random.uniform(1, 2))
            password_field.send_keys(password)
            
            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            time.sleep(random.uniform(1, 3))
            login_button.click()
            
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"a[href*='/{username}/']")))
            logger.info("Manual login successful! Saving cookies...")
            
            with open(COOKIE_FILE_PATH, 'wb') as file:
                pickle.dump(driver.get_cookies(), file)
            logger.info(f"Cookies saved to {COOKIE_FILE_PATH}")
            
        except TimeoutException:
            logger.error("!!! Login failed after submitting credentials. Saving debug info. !!!")
            _create_debug_files(driver, f"{request_id}_failure")
            raise


@shared_task(bind=True)
def scrape_followers_and_following(self, username: str, password: str) -> None:
    redis_client = redis.from_url(settings.CELERY_BROKER_URL)
    lock_key = f"scan_lock_for_{username}"
    
    is_lock_acquired = redis_client.set(lock_key, "running", ex=3600, nx=True)
    
    if not is_lock_acquired:
        message = f"A scan is already in progress for {username}. Aborting this task."
        logger.warning(message)
        return
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    
    service = Service(executable_path=CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:

        _perform_ig_login(
            driver=driver,
            username=username,
            password=password,
            request_id=self.request.id
        )
                
        _perform_follower_scrape(
            driver=driver,
            username=username,
            password=password,
            request_id=self.request.id
        )

    finally:
        logger.info("Releasing lock.")
        redis_client.delete(lock_key)
        if driver:
            logger.info("Closing driver")
            driver.quit()

    

@shared_task(bind=True)
def perform_instagram_login(self, username, password):
    print(f"Starting Instagram login task for user: {username}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    
    service = Service(executable_path=CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    _perform_ig_login(
        driver=driver,
        username=username,
        password=password,
        request_id=self.request.id
    )
            
    
    logger.info("Taking a screenshot to prove it worked...")
    driver.get(f"https://www.instagram.com/{username}/")
    time.sleep(5)
    debug_success_screenshot_path = os.path.join(DEBUG_DIR, f'{self.request.id}_success.png')
    driver.save_screenshot(debug_success_screenshot_path)

    driver.quit()
    return f"Login process for {username} completed. Screenshot saved."