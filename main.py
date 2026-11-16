import json
from datetime import datetime, timezone, timedelta
import requests

def is_active_time():
    # မြန်မာစံတော်ချိန် (UTC +6:30) ဖြင့် လက်ရှိအချိန်ကို စစ်ဆေးခြင်း
    mmt_now = datetime.now(timezone(timedelta(hours=6, minutes=30)))
    current_hour = mmt_now.hour
    
    # ညနေ ၄ နာရီ (16) မှ မနက် ၅ နာရီ (5) အတွင်း
    if current_hour >= 16 or current_hour < 5:
        return True
    return False

def get_mmt_datetime(start_time_str):
    if not start_time_str:
        return 0, ""
    try:
        # ဥပမာ - "2026/11/16 13:00:00 +0000"
        clean_time_str = start_time_str.split(" +")[0]
        dt_utc = datetime.strptime(clean_time_str, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)
        
        # မြန်မာစံတော်ချိန် (UTC +6:30) သို့ ပြောင်းရန်
        dt_mmt = dt_utc.astimezone(timezone(timedelta(hours=6, minutes=30)))
        timestamp = int(dt_mmt.timestamp())
        
        now_mmt = datetime.now(timezone(timedelta(hours=6, minutes=30)))
        time_formatted = dt_mmt.strftime("%I:%M %p")
        
        if dt_mmt.date() == now_mmt.date():
            date_formatted = f"Today {time_formatted}"
        elif dt_mmt.date() == (now_mmt + timedelta(days=1)).date():
            date_formatted = f"Tomorrow {time_formatted}"
        else:
            date_formatted = dt_mmt.strftime("%b %d, %Y %I:%M %p")
            
        return timestamp, date_formatted
    except Exception as e:
        print(f"Time parsing error: {e}")
        return 0, start_time_str

def main():
    # သတ်မှတ်ထားသော အချိန်ပြင်ပ (မြန်မာစံတော်ချိန် ညနေ ၄ မှ မနက် ၅ အတွင်းမဟုတ်ပါက) ကျော်သွားမည်
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
        event_info = event.get("eventInfo", {})
        event_name = event_info.get("eventName", "")
        
        # Football သီးသန့်သာ စစ်ထုတ်မည်
        if event_name != "Football":
            continue
            
        status = event.get("status", "")
        channel_url = event.get("channelUrl")
        
        links = []
        
        # status က "live" ဖြစ်ပြီး channelUrl ရှိမှသာ stream links များကို ဝင်ဆွဲမည်
        if status == "live" and channel_url:
            try:
                ch_res = requests.get(channel_url, timeout=10)
                ch_data = ch_res.json()
                stream_urls = ch_data.get("streamUrls", [])
                
                for stream in stream_urls:
                    raw_link = stream.get("link", "")
                    
                    # .mpd လင့်ခ်များကိုသာ စစ်ထုတ်ယူမည်
                    if ".mpd" in raw_link:
                        # user-agent များနှင့် အခြားမလိုသည်များကို ရှင်းထုတ်ခြင်း
                        if "?|" in raw_link:
                            base_mpd = raw_link.split("?|")[0]
                        elif "|" in raw_link:
                            base_mpd = raw_link.split("|")[0]
                        else:
                            base_mpd = raw_link
                            
                        api_key = stream.get("api", "")
                        
                        # API ထဲက kid:key ရှိပါက drm ပုံစံဖြင့် ပေါင်းစပ်ပေးမည်
                        final_url = base_mpd
                        if api_key:
                            final_url = f"{base_mpd}?|drmScheme=clearkey&drmLicense={api_key}"
                            
                        links.append({
                            "url": final_url,
                            "lang": "en",
                            "referer": ""
                        })
            except Exception as e:
                print(f"Error fetching channel data from {channel_url}: {e}")

        start_time_raw = event_info.get('startTime', '')
        match_time, match_date = get_mmt_datetime(start_time_raw)

        match_data = {
            "enmatchName": f"{event_info.get('teamA')} VS {event_info.get('teamB')}",
            "LeagueName": event_info.get('eventType', ''),
            "Leaguelogo": event_info.get('eventLogo', ''),
            "homeLogo": event_info.get('teamAFlag', ''),
            "awayLogo": event_info.get('teamBFlag', ''),
            "matchTime": match_time,
            "matchDate": match_date,
            "enhomeName": event_info.get('teamA', ''),
            "enawayName": event_info.get('teamB', ''),
            "links": links
        }
        live_matches.append(match_data)

    output_data = {"livematch": live_matches}

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print("Successfully generated output.json!")

if __name__ == "__main__":
    main()
