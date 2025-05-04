import requests
from datetime import datetime
import json

# ====== LINE設定 ======
access_token = os.environ.get("ACCESS_TOKEN")
user_id = os.environ.get("USER_ID")

# 気象庁 山形県（庄内）の天気予報データ
JMA_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/060000.json"

# データ取得
def get_jma_weather():
    try:
        response = requests.get(JMA_URL)
        if response.status_code != 200:
            print("天気取得失敗:", response.status_code)
            return None
        return response.json()
    except Exception as e:
        print("例外:", e)
        return None

# 天気文の自然な整形
def format_weather_text(raw_text):
    # 例：「くもり　夜　雨　所により　雷　を伴う」→「くもり。夜は雨で、所により雷を伴います。」
    text = raw_text.replace("　", " ")
    text = text.replace("夜", "夜は")
    text = text.replace("所により", "所により")
    text = text.replace("を伴う", "を伴います")
    if not text.endswith("。"):
        text += "。"
    return text.strip()

# メッセージ作成
def create_jma_message(weather_json):
    try:
        area_index = 2  # 庄内地方

        # 日付
        report_datetime = weather_json[0]['reportDatetime'][:10]
        date_str = datetime.strptime(report_datetime, "%Y-%m-%d").strftime("%Y年%m月%d日")

        area_name = weather_json[0]['timeSeries'][0]['areas'][area_index]['area']['name']
        raw_weather = weather_json[0]['timeSeries'][0]['areas'][area_index]['weathers'][0]
        today_weather = format_weather_text(raw_weather)

        # 降水確率（今日 6〜24時）
        pop_data = weather_json[0]['timeSeries'][1]
        pops = pop_data['areas'][area_index]['pops']
        times = pop_data['timeDefines']

        today_rain = []
        for i in range(len(pops)):
            hour = times[i][11:16]
            if i < 4:
                today_rain.append(f"{hour}：{pops[i]}%")

        # 明日の朝（6:00〜12:00）
        raw_tomorrow = weather_json[0]['timeSeries'][0]['areas'][area_index]['weathers'][1]
        tomorrow_weather = format_weather_text(raw_tomorrow)

        tomorrow_rain = []
        for i in range(len(pops)):
            hour = times[i][11:16]
            if i == 4 or i == 5:  # 明日の6:00、12:00
                if pops[i] != "":
                    tomorrow_rain.append(f"{hour}：{pops[i]}%")

        # 風情報（風向・風速）
        winds = weather_json[0]['timeSeries'][0]['areas'][area_index].get('winds', ["情報なし"])
        wind_text = winds[0]

        # メッセージ
        message = (
            f"【{date_str}・{area_name}の天気予報】\n"
            f"今日の天気：{today_weather}\n"
            f"風：{wind_text}\n"
            f"今日の降水確率：\n" + "\n".join(today_rain) + "\n\n"
            f"明日の朝の天気：{tomorrow_weather}\n"
        )
        if tomorrow_rain:
            message += "明日の朝の降水確率：\n" + "\n".join(tomorrow_rain)
        return message
    except Exception as e:
        return f"データ処理エラー: {e}"

# LINE通知
def send_line_message(messageText):
    headers = {
        "Authorization": f'Bearer {access_token}',
        "Content-Type": "application/json"
    }
    data = {
        "to": user_id,
        "messages": [{"type": "text", "text": messageText}]
    }
    url = 'https://api.line.me/v2/bot/message/push'
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("送信完了：", messageText)
    else:
        print(f"エラー:{response.status_code},{response.text}")

# 実行処理
if __name__ == "__main__":
    weather_json = get_jma_weather()
    if weather_json:
        message = create_jma_message(weather_json)
        send_line_message(message)
    else:
        send_line_message("天気データの取得に失敗しました。")
