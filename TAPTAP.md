# 《狐狐勇者》TapTap 横屏 H5 试玩

用 Python 3 在仓库根目录打包。

```sh
python3 tools/package_taptap.py
```

输出为 `dist/huhuhero-taptap.zip`。包内入口为 `huhuhero/index.html`，游戏脚本与贴图随包提供。打包命令会检查所需文件、重新打开 ZIP 校验，并输出 SHA-256。

## 试玩打好的包

```sh
python3 -m zipfile -e dist/huhuhero-taptap.zip dist/preview
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist/preview
```

在浏览器打开 `http://127.0.0.1:8000/huhuhero/`。在桌面浏览器的触屏设备模拟模式下重新加载页面，即可测试手机版。也可以在地址末尾加上 `?touch=1` 用鼠标检查触控界面。

- **战斗**　向右进入战区，读怪物头上的英文。靠近武器看释义，点「砍」拾取匹配的武器，面向对应怪物再点「砍」。
- **屏幕方向**　横屏时单词和触控键更大。竖屏也可以开始试玩。从横屏转回竖屏会暂停，重新选择继续即可。
- **暂停**　点右上角的暂停键，或把游戏切到后台。回到页面后点「继续游戏」。暂停保留当前页面里的进度，刷新会重新开局。
- **桌面**　A / D 移动，空格跳跃，J 捡武器或攻击，K 翻滚，Q 喝药。

## 在 TapTap 客户端自测

作者决定试发后，可在自己的 TapTap 开发者中心确认该应用支持 H5 包，选择 H5 和横屏，上传 ZIP 并取得自测二维码。建议先在真机核对旋转后的按钮位置、边走边跳、首场拾取与斩杀，以及锁屏后继续战斗。具体流程见 [TapTap 包体管理与自测](https://developer.taptap.cn/v3/cli/skills/taptap-package-management/)。

本仓库含网页导出产物。移动入口位于 `index.html`、`mobile.js` 和 `mobile.css`，使用当前导出提供的 `window.__game` 和 `window.__scene` 管理缩放和暂停。后续重新导出游戏时，请同步入口的脚本文件名，并复测上述操作。
