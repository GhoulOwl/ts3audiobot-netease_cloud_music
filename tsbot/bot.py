import ts3
import requests
import json
import io
from pydub import AudioSegment
from pydub.playback import play
from threading import Thread, Lock
import time

# Teamspeak3服务器配置
TS3_SERVER = 'ping 120.24.179.202'
TS3_PORT = 10011
TS3_USERNAME = 'serveradmin'
TS3_PASSWORD = 'wqFjBx0i'
TS3_VIRTUAL_SERVER_ID = 1
TS3_CHANNEL_ID = 1
TS3_BOT_NICKNAME = 'MusicBot'

# NeteaseCloudMusicApi配置
NETEASE_API_URL = 'https://wy.liumouy.com:8443'

# 全局变量
current_song = None
current_song_id = None
playlist = []
is_playing = False
stop_signal = False
command_lock = Lock()  # 线程锁，用于保护共享资源

def get_song_info(song_name):
    try:
        response = requests.get(f"{NETEASE_API_URL}/search", params={'keywords': song_name})
        response.raise_for_status()
        data = response.json()
        return data['result']['songs'][0]['id']
    except requests.RequestException as e:
        print(f"Error fetching song info: {e}")
        return None

def get_song_url(song_id):
    try:
        response = requests.get(f"{NETEASE_API_URL}/song/url", params={'id': song_id})
        response.raise_for_status()
        data = response.json()
        return data['data'][0]['url']
    except requests.RequestException as e:
        print(f"Error fetching song url: {e}")
        return None

def play_song(song_url):
    global is_playing, stop_signal
    try:
        with command_lock:
            if stop_signal:
                print("Playback stopped by user.")
                return
            response = requests.get(song_url)
            audio = AudioSegment.from_file(io.BytesIO(response.content))
            is_playing = True
            play(audio)
            is_playing = False
    except Exception as e:
        print(f"Error playing song: {e}")

def play_next_song():
    global current_song, current_song_id, is_playing
    with command_lock:
        if playlist:
            current_song = playlist.pop(0)
            current_song_id = get_song_info(current_song)
            if current_song_id:
                song_url = get_song_url(current_song_id)
                if song_url:
                    play_song(song_url)
                else:
                    print("Failed to fetch song URL.")
            else:
                print("Failed to fetch song ID.")
        else:
            print("Playlist is empty.")

def handle_command(command, ts3conn):
    global is_playing, stop_signal, current_song, playlist
    with command_lock:
        if command.startswith('!播放 '):
            song_name = command.split('!播放 ', 1)[1]
            playlist.append(song_name)
            if not is_playing:
                play_next_song()
                ts3conn.sendtextmessage(targetmode=2, target=TS3_CHANNEL_ID, msg=f"正在播放: {song_name}")
        elif command == '!暂停':
            stop_signal = True
            is_playing = False
            ts3conn.sendtextmessage(targetmode=2, target=TS3_CHANNEL_ID, msg="播放已暂停")
        elif command == '!停止':
            stop_signal = True
            playlist = []
            is_playing = False
            ts3conn.sendtextmessage(targetmode=2, target=TS3_CHANNEL_ID, msg="播放已停止，歌单已清空")
        elif command == '!每日':
            try:
                response = requests.get(f"{NETEASE_API_URL}/recommend/songs")
                response.raise_for_status()
                data = response.json()
                for song in data['recommend']:
                    playlist.append(song['name'])
                if not is_playing:
                    play_next_song()
                    ts3conn.sendtextmessage(targetmode=2, target=TS3_CHANNEL_ID, msg="今日推荐歌曲已加入播放队列")
            except requests.RequestException as e:
                print(f"Error getting daily recommendations: {e}")
        elif command == '!上一曲':
            if len(playlist) > 1:
                playlist.insert(0, playlist.pop())
                play_next_song()
                ts3conn.sendtextmessage(targetmode=2, target=TS3_CHANNEL_ID, msg="切换至上一曲")
        elif command == '!下一曲':
            play_next_song()
            ts3conn.sendtextmessage(targetmode=2, target=TS3_CHANNEL_ID, msg="切换至下一曲")

try:
    with ts3.query.TS3BaseConnection(f"telnet://{TS3_SERVER}:{TS3_PORT}") as ts3conn:
        ts3conn.login(client_login_name=TS3_USERNAME, client_login_password=TS3_PASSWORD)
        ts3conn.use(sid=TS3_VIRTUAL_SERVER_ID)
        ts3conn.clientupdate(client_nickname=TS3_BOT_NICKNAME)

        def monitor_channel_messages():
            while True:
                event = ts3conn.recv_event()
                if event.event == "notifytextmessage":
                    msg = event.parsed["msg"]
                    handle_command(msg, ts3conn)

        thread = Thread(target=monitor_channel_messages)
        thread.start()

        while True:
            with command_lock:
                if is_playing and stop_signal:
                    is_playing = False
                    stop_signal = False
                elif not is_playing and playlist:
                    play_next_song()
            time.sleep(1)
except ts3.query.TS3QueryError as e:
    print(f"Error connecting to Teamspeak3 server: {e}")