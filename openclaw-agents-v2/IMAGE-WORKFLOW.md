# CPIS 飞书图片工作流

## 飞书权限

飞书应用必须开通并发布：

- `docs:document.media:upload`
- `docx:document:write_only`

## 图片传递

1. `cpis-info-collector` 采集无需登录即可读取的 HTTP/HTTPS 商品主图 URL。
2. `cpis-product-analyst` 原样透传 `image_url`。
3. `cpis-knowledge-curator` 使用 `feishu_doc` 的 `upload_image` 直接上传远程图片。
4. 每张图片最多尝试一次。失败后报告 `partial`，保留原始图片链接。
5. 禁止 base64、`data:` URI、空图片块和全量 `list_blocks` 扫描。

需要使用本地测试图片时，只能放在：

```text
~/.openclaw/media/cpis/<run_id>/
```

## 云端更新

```bash
cd ~/projects/Competitive-Product-Intelligence-System
git pull --ff-only
bash openclaw-agents-v2/install-rules.sh
bash openclaw-agents-v2/verify-rules.sh
```

验证输出必须包含：

```text
PASS cpis-info-collector
PASS cpis-product-analyst
PASS cpis-knowledge-curator
PASS CPIS image handoff and upload rules
```
