# ts3audiobot-netease_cloud_music

```
docker run -d --name ts3audiobot -v $(pwd)/test/rights.toml:/tsbot/rights.toml -v $(pwd)/test/YunSettings.ini:/tsbot/plugins/YunSettings.ini -v $(pwd)/test/bot.toml:/tsbot/bots/default/bot.toml -p 48913:58913 ts3audiobot-netease_cloud_music:latest
```
