import os
import re
import time
import pandas as pd
from playwright.sync_api import sync_playwright

USER_DATA_DIR = "./playwright_session"
EXCEL_OUTPUT_FILE = "sundaygrids_detailed_report.xlsx"

TARGET_PROJECTS = ["Ara 40", "Venera 130", "Soho 195"]


def parse_drawer_metrics(text, period_label):
    """Extracts structured metrics and assigns correct date ranges."""
    def grab(pattern):
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else "N/A"

    capacity = grab(r"Capacity Reserved\s*([\d,.]+\s*W)")
    energy = grab(r"Energy Produced\s*([\d,.]+\s*kWh)")
    estimated_credits = grab(r"Estimated Credits(?:\s*BETA)?\s*(₹[\d,.\s\-–]+)")
    
    credits_earned = grab(r"Credits Earned[^\n]*[\r\n]+\s*(₹[\d,.]+)")
    if credits_earned == "N/A":
        match = re.search(r"Credits Earned.*?([₹$][\d,.]+)", text, re.DOTALL | re.IGNORECASE)
        if match:
            credits_earned = match.group(1).strip()

    current_year = pd.Timestamp.now().year
    if period_label == "Today":
        date_range = pd.Timestamp.now().strftime("%b %d, %Y")
    elif period_label == "This Month":
        date_range = f"Nov 1, {current_year} - today"
    elif period_label.startswith("Month - "):
        month_name = period_label.replace("Month - ", "")
        month_map = {
            "Jan": f"Jan 1 - Jan 31, {current_year}", "Feb": f"Feb 1 - Feb 28, {current_year}",
            "Mar": f"Mar 1 - Mar 31, {current_year}", "Apr": f"Apr 1 - Apr 30, {current_year}",
            "May": f"May 1 - May 31, {current_year}", "Jun": f"Jun 1 - Jun 30, {current_year}",
            "Jul": f"Jul 1 - Jul 31, {current_year}", "Aug": f"Aug 1 - Aug 31, {current_year}",
            "Sep": f"Sep 1 - Sep 30, {current_year}", "Oct": f"Oct 1 - Oct 31, {current_year}",
            "Nov": f"Nov 1 - Nov 30, {current_year}", "Dec": f"Dec 1 - Dec 31, {current_year}"
        }
        date_range = month_map.get(month_name, f"{month_name}, {current_year}")
    else:
        date_range = grab(r"([A-Za-z]+\s+\d+,\s+\d+\s*[-–]\s*[^\n]+|[A-Za-z]+\s+\d+\s*[-–]\s*[^\n]+)")

    return {
        "Date Range": date_range,
        "Capacity Reserved": capacity,
        "Energy Produced": energy,
        "Estimated Credits": estimated_credits,
        "Credits Earned": credits_earned,
    }


def get_full_drawer_text(page):
    drawer = page.locator("div:has-text('Project Generation'):has-text('Your Archive')").last
    if drawer.count() > 0:
        return drawer.inner_text()
    return page.inner_text("body")


def run_sundaygrids_scraper():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",
            headless=False,
            slow_mo=100,
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.new_page()
        print("Navigating to SundayGrids dashboard...")
        page.goto("https://app.sundaygrids.com/")

        if "login" in page.url or "signin" in page.url or page.locator("input[type='tel']").count() > 0:
            print("\n--- MANUAL LOGIN REQUIRED ---")
            input("Please log into your SundayGrids account, then press Enter here in your terminal...")

        print("Successfully logged in! Waiting for dashboard to settle...")
        page.wait_for_load_state("networkidle")
        time.sleep(3)

        consolidated_summary = []
        history_records = []
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

        for proj_name in TARGET_PROJECTS:
            print(f"\n--- Processing Project: {proj_name} ---")

            proj_title = page.get_by_text(proj_name, exact=True).first
            if proj_title.count() == 0:
                print(f"Could not find {proj_name} on dashboard.")
                continue

            proj_title.scroll_into_view_if_needed()
            proj_title.click()
            time.sleep(2.5)

            try:
                page.locator("text='Your Archive'").last.wait_for(state="visible", timeout=5000)
            except Exception:
                print(f"Warning: Side drawer archive section took longer to load for {proj_name}")

            drawer = page.locator("div:has-text('Project Generation'):has-text('Your Archive')").last
            
            # 1. ALL TIME (Sheet 1)
            all_time_btn = drawer.get_by_text("All Time", exact=True).first
            if all_time_btn.count() > 0:
                all_time_btn.click()
                time.sleep(1.2)

            all_time_metrics = parse_drawer_metrics(get_full_drawer_text(page), "All Time")
            earned_val = all_time_metrics["Credits Earned"]
            if earned_val == "N/A":
                earned_val = all_time_metrics["Estimated Credits"]

            consolidated_summary.append({
                "Timestamp": timestamp,
                "Project Name": proj_name,
                "Date Range": all_time_metrics["Date Range"],
                "Capacity Reserved": all_time_metrics["Capacity Reserved"],
                "Total Energy Produced": all_time_metrics["Energy Produced"],
                "Estimated Credits": all_time_metrics["Estimated Credits"],
                "Total Credits Earned": earned_val,
            })
            print(f"  ✔ All Time captured -> Credits: {earned_val}")

            # 2. TODAY & THIS MONTH (Sheet 2)
            for period_label in ["Today", "This Month"]:
                tab_btn = drawer.get_by_text(period_label, exact=True).first
                if tab_btn.count() > 0:
                    tab_btn.click()
                    time.sleep(1.2)
                    m = parse_drawer_metrics(get_full_drawer_text(page), period_label)
                    history_records.append({
                        "Timestamp": timestamp,
                        "Project Name": proj_name,
                        "Period": period_label,
                        "Date Range": m["Date Range"],
                        "Capacity Reserved": m["Capacity Reserved"],
                        "Energy Produced": m["Energy Produced"],
                        "Estimated Credits": m["Estimated Credits"],
                        "Credits Earned": m["Credits Earned"],
                    })
                    print(f"  ✔ Captured '{period_label}' metrics -> Energy: {m['Energy Produced']} | Earned: {m['Credits Earned']}")

            # 3. MONTH BY YEAR
            try:
                dropdown_arrow = drawer.locator("button:has(svg)").filter(has_not_text=re.compile(r".")).last
                if dropdown_arrow.count() > 0:
                    dropdown_arrow.click()
                    time.sleep(1.0)

                month_by_year_btn = drawer.get_by_text("Month by Year", exact=True).first
                if month_by_year_btn.count() > 0:
                    month_by_year_btn.click()
                    time.sleep(1.5)

                    month_pills = drawer.locator("button").filter(has_text=re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$"))
                    count = month_pills.count()
                    print(f"  -> Found {count} month buttons under 'Month by Year'.")

                    for idx in range(count):
                        try:
                            pill = month_pills.nth(idx)
                            if not pill.is_visible():
                                continue

                            pill.scroll_into_view_if_needed()
                            month_name = pill.inner_text().strip()
                            pill.click()
                            time.sleep(1.2)

                            period_key = f"Month - {month_name}"
                            m = parse_drawer_metrics(get_full_drawer_text(page), period_key)
                            history_records.append({
                                "Timestamp": timestamp,
                                "Project Name": proj_name,
                                "Period": period_key,
                                "Date Range": m["Date Range"],
                                "Capacity Reserved": m["Capacity Reserved"],
                                "Energy Produced": m["Energy Produced"],
                                "Estimated Credits": m["Estimated Credits"],
                                "Credits Earned": m["Credits Earned"],
                            })
                            print(f"    ✔ Captured Month: {month_name} -> Energy: {m['Energy Produced']} | Earned: {m['Credits Earned']}")
                        except Exception as ex:
                            print(f"    Could not process month index {idx}: {ex}")
                else:
                    print("  -> 'Month by Year' button not found.")
            except Exception as e:
                print(f"  -> Skipped 'Month by Year': {e}")

            # --- BULLETPROOF CLOSE DRAWER & BACKDROP CLEARING ---
            print(f"Closing side panel for {proj_name}...")
            try:
                close_btn = drawer.locator("button:has(svg), [aria-label='Close'], button.rounded-full").last
                if close_btn.count() > 0:
                    close_btn.click()
                else:
                    page.keyboard.press("Escape")
            except:
                page.keyboard.press("Escape")

            try:
                backdrop = page.locator(".backdrop-blur-sm, [class*='modal-backdrop']")
                if backdrop.count() > 0 and backdrop.is_visible():
                    page.mouse.click(10, 200)
            except:
                pass

            time.sleep(2.0)

        # Write both structured sheets to Excel
        with pd.ExcelWriter(EXCEL_OUTPUT_FILE, engine="openpyxl") as writer:
            pd.DataFrame(consolidated_summary).to_excel(
                writer, sheet_name="Consolidated Totals", index=False
            )
            pd.DataFrame(history_records).to_excel(
                writer, sheet_name="History & Current Month", index=False
            )

        print(f"\n🎉 Saved comprehensive report with {len(history_records)} history rows into {EXCEL_OUTPUT_FILE}!")
        context.close()


if __name__ == "__main__":
    run_sundaygrids_scraper()
