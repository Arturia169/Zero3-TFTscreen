"""
Telegram Bot 创建和配置指南

1. 打开 Telegram，搜索 @BotFather
2. 发送 /newbot
3. 按提示设置 Bot 名称和用户名
4. 获得 Bot Token（类似：123456789:ABCdefGHIjklMNOpqrsTUVwxyz）
5. 将 Token 保存到 telegram_config.json：

{
  "bot_token": "你的Bot Token",
  "channels": [
    "@channel_username1",
    "@channel_username2"
  ]
}

注意：
- 频道用户名需要加 @ 前缀
- Bot 只能读取公开频道
- 需要先将 Bot 添加为频道管理员（可选，用于获取更多信息）
"""
