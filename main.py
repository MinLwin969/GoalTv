import json
import os
from datetime import datetime, timezone, timedelta
import requests

def is_active_time():
    # မြန်မာစံတော်ချိန် (MMT = UTC +6:30) ဖြင့် စစ်ဆေးခြင်း
    utc_now = datetime.now(timezone.utc)
    mmt_now = utc_now + timedelta(hours=6, minutes=30)
    current_hour = mmt_now.hour
    
    # ညနေ ၄ နာရီ (16) မှ မနက် ၅ နာရီ (5) အတွင်း
    if current_hour >= 16 or current_hour < 5:
        return True
    return False

def main():
    # အချိန်သတ်မှတ်ချက် စစ်ဆေးရန် (မြန်မာစံတော်ချိန် ညနေ ၄ မှ မနက် ၅ အတွင်းသာ)
    if not is_active_time():
        print("Outside active time (4 PM to 5 AM MMT). Skipping execution.")
        return

    main_url = "https://restless-smoke-4e11.mominulislamm3u8.workers.dev/categories/live-events.txt"
    
    try:
        response = requests.get(main_url, timeout=15)
        response.raise_for_status()
        events = response.json()
    except Exception as e:
        print(f"Error fetching main events: {e}")
        return

    live_matches = []

    for event in events:
        if event.get("status") == "live":
            event_info = event.get("eventInfo", {})
            channel_url = event.get("channelUrl")
            
            links = []
            if channel_url:
                try:
                    ch_res = requests.get(channel_url, timeout=10)
                    ch_data = ch_res.json()
                    stream_urls = ch_data.get("streamUrls", [])
                    
                    for stream in stream_urls:
                        raw_link = stream.get("link", "")
                        
                        # .mpd လင့်ခ်များကိုသာ စစ်ထုတ်ယူမည်
                        if ".mpd" in raw_link:
                            # နောက်က user-agent / extra parameters များကို ဖြတ်ထုတ်ခြင်း (| သင်္ကေတနောက်ပိုင်းဖယ်ရန်)
                            if "|" in raw_link:
                                clean_mpd = raw_link.split("|")[0]
                            else:
                            # query parameters တွေပါရင် ရှင်းထုတ်ရန် (သို့မဟုတ် လိုအပ်သလိုထိန်းရန်)
                                clean_mpd = raw_link.split("?")[0] if "?" in raw_link else raw_link
                                # ဒါပေမယ့် mpd မှာ drm query တွေပါနိုင်ို့ ?| ပုံစံကိုသာ အဓိക ဖြတ်ပါတယ်
                            
                            # တကယ်လို့ query parameter အချို့ (ဥပမာ drmScheme) ပါရင် ချန်လှပ်ချင်ပါက:
                            # ဥပမာ - https://.../cenc.mpd?|drmScheme=clearkey&drmLicense=KID:KEY ပုံစံဖြစ်ပါက
                            base_mpd = raw_link.split("?|")[0] if "?|" in raw_link else raw_link
                            api_key = stream.get("api", "")
                            
                            final_url = base_mpd
                            if api_key:
                                # api ထဲက kid:key ကို ရယူပြီး ပေါင်းစပ်ပုံစံဖော်မည်
                                final_url = f"{base_mpd}?|drmScheme=clearkey&drmLicense={api_key}"
                            
                            links.append({
                                "url": final_url,
                                "lang": "en",
                                "referer": ""
                            })
                except Exception as e:
                    print(f"Error fetching channel data from {channel_url}: {e}")

            # Match အချက်အလက်များ ထည့်သွင်းခြင်း
            match_data = {
                "enmatchName": f"{event_info.get('teamA')} VS {event_info.get('teamB')}",
                "LeagueName": event_info.get('eventType', ''),
                "Leaguelogo": event_info.get('eventLogo', ''),
                "homeLogo": event_info.get('teamAFlag', ''),
                "awayLogo": event_info.get('teamBFlag', ''),
                "matchTime": int(datetime.strptime(event_info.get('startTime', '2026/01/01 00:00:00 +0000').split(" +")[0], "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()) if event_info.get('startTime') else 0,
                "matchDate": event_info.get('startTime', ''),
                "enhomeName": event_info.get('teamA', ''),
                "enawayName": event_info.get('teamB', ''),
                "links": links
            }
            live_matches.append(match_data)

    output_data = {"livematch": live_matches}

    # output.json ဖိုင်သို့ သိမ်းဆည်းမည်
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print("Successfully generated output.json")

if __name__ == "__main__":
    main()
