# LarpManager - https://larpmanager.com
# Copyright (C) 2025 Scanagatta Mauro
#
# This file is part of LarpManager and is dual-licensed:
#
# 1. Under the terms of the GNU Affero General Public License (AGPL) version 3,
#    as published by the Free Software Foundation. You may use, modify, and
#    distribute this file under those terms.
#
# 2. Under a commercial license, allowing use in closed-source or proprietary
#    environments without the obligations of the AGPL.
#
# If you have obtained this file under the AGPL, and you make it available over
# a network, you must also make the complete source code available under the same license.
#
# For more information or to purchase a commercial license, contact:
# commercial@larpmanager.com
#
# SPDX-License-Identifier: AGPL-3.0-or-later OR Proprietary


from playwright.sync_api import expect, sync_playwright

from larpmanager.tests.utils import go_to, handle_error, login_orga, login_user, logout, page_start


def test_exe_assoc_role(live_server):
    with sync_playwright() as p:
        browser, context, page = page_start(p)
        try:
            exe_assoc_role(live_server, page)

        except Exception as e:
            handle_error(page, e, "exe_assoc")

        finally:
            context.close()
            browser.close()


def exe_assoc_role(live_server, page):
    login_user(page, live_server)

    go_to(page, live_server, "/manage/")
    expect(page.locator("#header")).to_contain_text("Access denied")

    login_orga(page, live_server)

    go_to(page, live_server, "/manage/roles")
    page.get_by_role("link", name="New").click()
    page.locator("#id_name").click()
    page.locator("#id_name").fill("test role")
    page.locator("#id_name").press("Tab")
    page.get_by_role("searchbox").fill("us")
    page.get_by_role("option", name="User Test -").click()
    page.locator("#id_Organization_2").check()
    page.locator("#id_Accounting_0").check()
    page.get_by_role("button", name="Confirm", exact=True).click()
    expect(page.locator('[id="\\32 "]')).to_contain_text("Organization (Configuration), Accounting (Accounting)")

    logout(page, live_server)
    login_user(page, live_server)

    go_to(page, live_server, "/manage/accounting/")
    expect(page.locator("#banner")).to_contain_text("Accounting - Organization")

    logout(page, live_server)
    login_orga(page, live_server)

    go_to(page, live_server, "/manage/roles")
    page.get_by_role("row", name=" test role User Test").get_by_role("link").click()
    page.get_by_role("link", name="Delete").click()
    page.wait_for_timeout(2000)
    page.get_by_role("button", name="Confirmation delete").click()

    logout(page, live_server)
    login_user(page, live_server)

    go_to(page, live_server, "/manage/")
    expect(page.locator("#header")).to_contain_text("Access denied")
