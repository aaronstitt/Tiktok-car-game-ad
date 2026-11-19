from playwright.sync_api import sync_playwright
import pathlib
url = pathlib.Path("Bronco_Pause_Game.html").resolve().as_uri()
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox","--use-gl=swiftshader","--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width":420,"height":820}, device_scale_factor=2)
    errs=[]
    pg.on("console", lambda m: errs.append(m.type+": "+m.text) if m.type in ("error","warning") else None)
    pg.on("pageerror", lambda e: errs.append("PAGEERROR: "+str(e)))
    pg.goto(url); pg.wait_for_timeout(1500)
    pg.screenshot(path="review/g1_playing.png")
    # force a guaranteed win by tapping at the align instant via JS hook:
    pg.evaluate("playStart = performance.now() - %f" % (0.60*3200))  # set t≈ALIGN
    pg.wait_for_timeout(60)
    pg.mouse.click(210,400)   # tap to freeze -> should win
    pg.wait_for_timeout(700)
    pg.screenshot(path="review/g2_youwin.png")
    pg.wait_for_timeout(1300)  # form appears at 1700ms
    pg.screenshot(path="review/g3_form.png")
    # fill the form
    pg.click(".prize[data-prize='Cooler']")
    pg.fill("#fName","Test Buyer"); pg.fill("#fPhone","801-555-0123")
    pg.select_option("#fWhen","In the next week")
    pg.screenshot(path="review/g4_form_filled.png")
    print("CONSOLE ISSUES:", errs if errs else "none")
    b.close()
print("done")
