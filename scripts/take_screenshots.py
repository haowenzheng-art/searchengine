"""自动截图脚本 - 用 Playwright 跑完整前端流程并截图.

前置:
- 后端 API 在 http://localhost:8001
- 前端 dev server 在 http://localhost:5175
- 数据库干净或已有 screenshot@example.com 账号

输出: docs/screenshots/ 目录下的 10 张截图
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
from playwright.sync_api import Page, sync_playwright

BASE_URL = "http://localhost:5175"
API_URL = "http://localhost:8001"
OUT_DIR = Path(__file__).parent.parent / "docs" / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EMAIL = "screenshot@example.com"
PASSWORD = "Passw0rd!"


def ensure_user() -> None:
    """先注册一个账号供截图使用."""
    try:
        r = httpx.post(
            f"{API_URL}/api/v1/auth/register",
            json={"email": EMAIL, "password": PASSWORD},
            timeout=10,
        )
        print(f"register: {r.status_code}")
    except Exception as e:
        print(f"register failed (maybe exists): {e}")


def get_first_workflow_id() -> int | None:
    try:
        r = httpx.post(
            f"{API_URL}/api/v1/auth/login",
            data={"username": EMAIL, "password": PASSWORD},
            timeout=10,
        )
        token = r.json()["access_token"]
        list_r = httpx.get(
            f"{API_URL}/api/v1/workflows",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        data = list_r.json()
        if data["items"]:
            return data["items"][0]["id"]
        create_r = httpx.post(
            f"{API_URL}/api/v1/workflows",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "招聘筛选流程", "notes": "互联网行业招聘流程分析"},
            timeout=10,
        )
        return create_r.json()["workflow_id"]
    except Exception as e:
        print(f"get workflow id failed: {e}")
        return None


def screenshot_login(page) -> None:
    page.goto(f"{BASE_URL}/login")
    page.wait_for_selector("button[type='submit']")
    page.screenshot(path=OUT_DIR / "01-login.png", full_page=True)
    print("saved 01-login.png")


def screenshot_register(page) -> None:
    page.goto(f"{BASE_URL}/register")
    page.wait_for_selector("button[type='submit']")
    page.screenshot(path=OUT_DIR / "02-register.png", full_page=True)
    print("saved 02-register.png")


def do_login(page) -> None:
    """直接调用后端登录 API，再把 token 注入 localStorage，绕过 Vite proxy 对 form-data 的转发问题."""
    r = httpx.post(
        f"{API_URL}/api/v1/auth/login",
        data={"username": EMAIL, "password": PASSWORD},
        timeout=10,
    )
    r.raise_for_status()
    tokens = r.json()
    me_r = httpx.get(
        f"{API_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=10,
    )
    me_r.raise_for_status()
    user = me_r.json()

    # 与 Zustand persist store (name='wda-auth') 的序列化格式一致
    store_payload = {
        "state": {
            "user": user,
            "accessToken": tokens["access_token"],
            "refreshToken": tokens["refresh_token"],
        },
        "version": 0,
    }
    page.goto(f"{BASE_URL}/login")
    page.wait_for_selector("input#email")
    page.evaluate(f"localStorage.setItem('wda-auth', JSON.stringify({store_payload}))")
    page.goto(f"{BASE_URL}/dashboard")
    page.locator("h1", has_text="工作流").wait_for(timeout=30000)
    time.sleep(1)


def screenshot_dashboard(page) -> None:
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_selector("h1")
    time.sleep(1)
    page.screenshot(path=OUT_DIR / "03-dashboard.png", full_page=True)
    print("saved 03-dashboard.png")


def screenshot_new_workflow(page) -> None:
    page.goto(f"{BASE_URL}/workflows/new")
    page.wait_for_selector("h1")
    time.sleep(0.5)
    page.screenshot(path=OUT_DIR / "04-new-workflow.png", full_page=True)
    print("saved 04-new-workflow.png")


def screenshot_workflow_detail(page: Page, workflow_id: int) -> None:
    # 时间线 tab
    page.goto(f"{BASE_URL}/workflows/{workflow_id}")
    page.wait_for_selector("h1")
    time.sleep(2)
    page.screenshot(path=OUT_DIR / "05-detail-timeline.png", full_page=True)
    print("saved 05-detail-timeline.png")

    # 展开第一个 tool_call
    buttons = page.locator("button", has_text="迭代 #").all()
    if buttons:
        buttons[0].click()
        time.sleep(0.5)
        page.screenshot(path=OUT_DIR / "06-timeline-expanded.png", full_page=True)
        print("saved 06-timeline-expanded.png")

    # 证据链 tab
    evidence_tab = page.locator("button", has_text="证据链").first
    if evidence_tab.count() > 0:
        evidence_tab.click()
        time.sleep(1)
        page.screenshot(path=OUT_DIR / "07-evidence.png", full_page=True)
        print("saved 07-evidence.png")

    # 报告 tab（只有完成后才有）
    report_tab = page.locator("button", has_text="报告").first
    if report_tab.count() > 0:
        report_tab.click()
        time.sleep(0.5)
        page.screenshot(path=OUT_DIR / "08-report.png", full_page=True)
        print("saved 08-report.png")


def screenshot_usage(page) -> None:
    page.goto(f"{BASE_URL}/usage")
    page.wait_for_selector("h1")
    time.sleep(0.5)
    page.screenshot(path=OUT_DIR / "09-usage.png", full_page=True)
    print("saved 09-usage.png")


def screenshot_navbar(page) -> None:
    page.goto(f"{BASE_URL}/dashboard")
    # 点击头像打开下拉
    avatar = page.locator("button[variant='ghost']").first
    if avatar.count() > 0:
        avatar.click()
        time.sleep(0.5)
    page.screenshot(path=OUT_DIR / "10-navbar.png", full_page=False)
    print("saved 10-navbar.png")


def main() -> None:
    print(f"Output dir: {OUT_DIR}")
    ensure_user()
    workflow_id = get_first_workflow_id()
    print(f"workflow_id: {workflow_id}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        screenshot_login(page)
        screenshot_register(page)
        do_login(page)
        screenshot_dashboard(page)
        screenshot_new_workflow(page)
        if workflow_id:
            screenshot_workflow_detail(page, workflow_id)
        screenshot_usage(page)
        screenshot_navbar(page)

        browser.close()
    print("done")


if __name__ == "__main__":
    main()
