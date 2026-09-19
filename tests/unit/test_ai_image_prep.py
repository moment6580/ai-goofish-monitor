import base64
import os
from datetime import datetime

import pytest
from PIL import Image

from src import ai_handler


@pytest.fixture()
def images(tmp_path):
    paths = []
    for index in range(8):
        path = tmp_path / f"img-{index}.png"
        # 大尺寸 + 随机噪点，确保压缩后体积明显减小
        image = Image.new("RGB", (2000, 1500))
        pixels = image.load()
        for x in range(0, 2000, 10):
            for y in range(0, 1500, 10):
                pixels[x, y] = ((x * 7 + index) % 256, (y * 11) % 256, (x + y) % 256)
        image.save(path, format="PNG")
        paths.append(str(path))
    return paths


def test_prepare_image_data_urls_caps_image_count(images, monkeypatch):
    monkeypatch.setattr(ai_handler, "DEFAULT_AI_MAX_IMAGES", 3)

    urls = ai_handler.prepare_image_data_urls(images)

    assert len(urls) == 3
    assert all(url.startswith("data:image/jpeg;base64,") for url in urls)


def test_prepare_image_data_urls_compresses(images, monkeypatch):
    monkeypatch.setattr(ai_handler, "DEFAULT_AI_MAX_IMAGES", 1)
    monkeypatch.setattr(ai_handler, "AI_IMAGE_MAX_SIDE", 512)
    monkeypatch.setattr(ai_handler, "AI_IMAGE_JPEG_QUALITY", 70)

    url = ai_handler.prepare_image_data_urls([images[0]])[0]
    raw = base64.b64decode(url.split(",", 1)[1])

    assert len(raw) < os.path.getsize(images[0])

    # 产物应为可解码的 JPEG，且最长边被缩放到 512
    from io import BytesIO

    decoded = Image.open(BytesIO(raw))
    assert decoded.format == "JPEG"
    assert max(decoded.size) == 512


def test_prepare_image_data_urls_handles_empty_and_missing(tmp_path):
    assert ai_handler.prepare_image_data_urls([]) == []
    assert ai_handler.prepare_image_data_urls(None) == []
    # 不存在的文件不应抛异常，只是被跳过
    assert ai_handler.prepare_image_data_urls([str(tmp_path / "nope.png")]) == []


def test_prepare_image_data_urls_falls_back_to_raw_when_compress_fails(images, monkeypatch):
    monkeypatch.setattr(ai_handler, "DEFAULT_AI_MAX_IMAGES", 1)
    monkeypatch.setattr(ai_handler, "_compress_image_to_base64", lambda _path: None)

    urls = ai_handler.prepare_image_data_urls([images[0]])

    assert len(urls) == 1
    assert urls[0].startswith("data:image/jpeg;base64,")
    # 回退路径应为原图字节
    raw = base64.b64decode(urls[0].split(",", 1)[1])
    assert len(raw) == os.path.getsize(images[0])


def test_ai_log_filename_includes_microseconds_and_product():
    """连续生成的日志文件名必须唯一（此前秒级命名会互相覆盖）。"""
    names = [ai_handler._build_ai_log_filename("item/123") for _ in range(50)]

    assert len(set(names)) == len(names)
    # 目录清理按前 15 字符解析时间戳，需保持兼容
    assert datetime.strptime(names[0][:15], "%Y%m%d_%H%M%S")
    assert all(name.endswith("_item_123.log") for name in names)


def test_ai_log_filename_sanitizes_and_handles_empty():
    assert ai_handler._build_ai_log_filename("") .endswith("_unknown.log")
    unsafe = ai_handler._build_ai_log_filename("../../etc/passwd")
    assert "/" not in unsafe
    assert ".." not in unsafe
