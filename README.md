# Davinci Resolve Matching Subtitles

![](./screenshots/screenshot.jpg)

## Motivation

Davinci 18 可以识别字幕，尽管听准确的，但是还是有错误的地方，如果已经有字幕了，那么希望直接使用已有字幕做打轴。目前还没有这个功能。

## 安装

1. 安装 Python >= 3.6
2. 安装 Python 包

```shell
pip install thefuzz
pip install srt
```

或者创建 `davinci` 虚拟环境，再安装上面的包，可能更好一点。

3. 将 `Matching Subtitles.py` 拷贝到 `"%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility"`
4. 默认该目录为 `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility`

## 使用

1. 首先使用 Davinci 创建字幕，最大长度 1
2. 然后 `Workspace` > `Script` > `Matching Subtitles`
3. 将字幕输入文本框中
4. 点击 Match
5. 完成后，项目资源中会创建一个匹配好的字幕，文件名随机的 `.srt` 文件
6. 手动创建一个字幕轨，托入即可

## References

- https://github.com/tmoroney/auto-subs
